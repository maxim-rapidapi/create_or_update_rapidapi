import json
import os
import semver
import sys

from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport


def read_spec(oas):
    f = open(oas, "r")
    f = f.read()
    return json.loads(f)


def get_spec_version(spec):
    return spec["info"]["version"]


def get_api_name(spec):
    return spec["info"]["title"]


def get_api_description(spec):
    return spec["info"]["description"]


def already_exists(name, c):
    search_for_api = gql(
        """
        query api($where: ApiWhereInput) {
          apis(where: $where) {
            nodes {
              id
              name
            }
          }
        }
        """
    )
    params = {
        "where": {
            "name": name
        }
    }
    res = c.execute(search_for_api, variable_values=json.dumps(params))
    nodes = res["apis"]["nodes"]
    if len(nodes) == 0:
        return None
    elif len(nodes) == 1:
        return nodes.pop()["id"]
    else:
        print("Error: more than one API found by this name. That should not happen")
        sys.exit(1)


def get_current_api_version(id, c):
    get_api_version_query = gql(
        """
        query apiVersions($where: ApiVersionWhereInput) {
          apiVersions(where: $where) {
            nodes {
              id
              name
              current
            }
          }
        }
        """
    )
    params = {
        "where": {
            "apiId": id,
            "versionStatus": "ACTIVE"
        }
    }
    res = c.execute(get_api_version_query, variable_values=json.dumps(params))
    return get_current_version(res["apiVersions"]["nodes"])


def set_created_version_as_active(api_version_id, c):
    set_active_query = gql(
        """
        mutation updateApiVersions($apiVersions: [ApiVersionUpdateInput!]!) {
          updateApiVersions(apiVersions: $apiVersions) {
            id
            name
            current
          }
        }
        """
    )
    params = {
        "apiVersions": [{
            "apiVersionId": api_version_id,
            "current": True,
            "versionStatus": "active"
        }]
    }
    res = c.execute(set_active_query, variable_values=params)
    return res["updateApiVersions"][0]["current"]


def get_current_version(versions):
    return next(v["name"] for v in versions if v["current"] is True)


def create_new_listing(my_file, name, description, c):
    create_api_listing = gql(
        """
        mutation createApisFromSpecs($creations: [ApiCreateFromSpecInput!]!) {
          createApisFromSpecs(creations: $creations) {
            apiId
          }
        }
        """
    )
    with open(my_file, "rb") as oas:
        params = {
            "creations": [
                {
                    "spec": oas,
                    "specType": "OPENAPI",
                    "category": "Utility APIs",
                    "name": name,
                    "description": description
                }
            ]
        }
        res = c.execute(create_api_listing, variable_values=params,
                        upload_files=True)
        return res["createApisFromSpecs"][0]["apiId"]


def create_api_version(version_name, api_id, c):
    create_api_version = gql(
        """
    mutation createApiVersions($apiVersions: [ApiVersionCreateInput!]!) {
        createApiVersions(apiVersions: $apiVersions) {
            id
        }
    }
    """
    )
    params = {
        "apiVersions": {
            "api": api_id,
            "name": str(version_name),
        }
    }
    res = c.execute(create_api_version, variable_values=params)
    return res["createApiVersions"][0]["id"]


def update_api_version(spec_path, api_version_id, c):
    update_api_version = gql(
        """
        mutation updateApisFromSpecs($updates: [ApiUpdateFromSpecInput!]!) {
            updateApisFromSpecs(updates: $updates) {
                apiId
            }
        }
        """
    )
    with open(spec_path, "rb") as oas:
        params = {
            "updates": [
                {
                    "spec": oas,
                    "specType": "OPENAPI",
                    "apiVersionId": api_version_id
                }
            ]
        }
        res = c.execute(update_api_version, variable_values=params,
                        upload_files=True)
        return res["updateApisFromSpecs"][0]["apiId"]


def create_or_update():
    """
    Create a new listing, or update an existing listing on RapidAPI Hub
    """

    # Create header dictionary based on input from GitHub
    headers = {
        "x-rapidapi-key": os.getenv("INPUT_X_RAPIDAPI_KEY"),
        "x-rapidapi-host": os.getenv("INPUT_X_RAPIDAPI_HOST")
    }
    x_rapidapi_identity_key = os.getenv("INPUT_X_RAPIDAPI_IDENTITY_KEY")
    if x_rapidapi_identity_key:
        headers["x-rapidapi-identity-key"] = x_rapidapi_identity_key

    # setting up connection to GraphQL PAPI
    graphql_url = os.getenv("INPUT_GRAPHQL_URL",
                            default="https://graphql-platform.p.rapidapi.com/")
    transport = AIOHTTPTransport(url=graphql_url, headers=headers)
    client = Client(transport=transport, fetch_schema_from_transport=False)

    # Start reading spec
    spec_path = os.environ["INPUT_SPEC_PATH"]
    f = read_spec(spec_path)
    spec_version = get_spec_version(f)
    api_name = get_api_name(f)
    api_description = get_api_description(f)
    print(f"API name: {api_name}")
    print(f"Spec version: {spec_version}")

    api_id = already_exists(api_name, client)
    if api_id is None:
        print("This is a new API, creating a new listing...")
        new_id = create_new_listing(spec_path, api_name,
                                    api_description, client)
        print(f"New API created with id: {new_id}")
        print(f"Grabbing id of newly created version")
        current_version = get_current_api_version(new_id, client)

        print(f"::set-output name=api_id::{new_id}")
        print(f"::set-output name=api_version_id::{current_version}")
    else:
        print(f"API already exists with id: {api_id}")
        current_version = get_current_api_version(api_id, client)
        parsed_spec_version = semver.VersionInfo.parse(spec_version)
        parsed_current_version = semver.VersionInfo.parse(current_version)
        print(f"parsed spec version: {parsed_spec_version}")
        print(f"current version: {parsed_current_version}")
        spec_is_newer = parsed_spec_version > parsed_current_version
        print("Uploaded spec is newer:", spec_is_newer)

        if spec_is_newer:
            print(f"Creating new api version for api {api_id}")
            api_version_id = create_api_version(parsed_spec_version,
                                                api_id, client)
            print(f"New api version id: {api_version_id}")
            update_api_version(spec_path, api_version_id, client)
            print(f"Setting new version as current")
            set_created_version_as_active(api_version_id, client)
            print(f"::set-output name=api_id::{api_id}")
            print(f"::set-output name=api_version_id::{api_version_id}")
        else:
            print("Uploaded spec is not newer than the current version.")
            sys.exit(1)


if __name__ == '__main__':
    create_or_update()
