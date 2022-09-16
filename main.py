#!/usr/bin/env python3
import json
import os

import requests
import semver
import sys

from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport


def needenv(name):
    """Check if required environment variables exist"""
    var = os.getenv(name)
    if var is None or var == "":
        sys.exit(f"The environment variable {name} is required.")
    return var


def read_spec(oas):
    """Return JSON string containing spec contents"""
    my_file = open(oas, "r", encoding="utf-8")
    my_file = my_file.read()
    return json.loads(my_file)


def get_spec_version(spec):
    """Return the version field of the OAS"""
    return spec["info"]["version"]


def get_api_name(spec):
    """Return the title / name field of the OAS"""
    return spec["info"]["title"]


def get_api_description(spec):
    """Return the description field of the OAS"""
    return spec["info"]["description"]


def already_exists(name, owner_id, c):
    """Check if an API already exists"""
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
            "name": name,
            "ownerId": int(owner_id)
        }
    }
    res = c.execute(search_for_api, variable_values=json.dumps(params))
    nodes = res["apis"]["nodes"]
    if len(nodes) == 0:
        return None
    if len(nodes) == 1:
        return nodes.pop()["id"]

    print("Error: more than one API found. That should not happen")
    sys.exit(1)


def get_current_api_version(id, c):
    """
    Queries the GraphQL PAPI for active API versions and calls
    get_current_version() to return the API version set as "current" only
    """
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
    """
    Set a specific version of an API as "current"
    """
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
    """
    Takes a list of API versions and returns only the one set as "current"
    """
    name = next(v["name"] for v in versions if v["current"] is True)
    version_id = next(v["id"] for v in versions if v["current"] is True)
    return (name, version_id)


def create_new_listing(my_file, c=None):
    """
    Creates a new API listing on the RapidAPI (Enterprise) Hub
    This has to be based on the REST PAPI until the GraphQL PAPI parses
    metadata
    """
    # create_api_listing = gql(
    #     """
    #     mutation createApisFromSpecs($creations: [ApiCreateFromSpecInput!]!)
    #       {
    #       createApisFromSpecs(creations: $creations) {
    #         apiId
    #       }
    #     }
    #     """
    # )
    headers = {
        "x-rapidapi-key": os.getenv("INPUT_X_RAPIDAPI_KEY"),
        "x-rapidapi-host": os.getenv("INPUT_X_RAPIDAPI_REST_HOST")
    }

    # Weird syntax to work around GitHub Actions issue #924
    url = os.getenv("INPUT_REST_URL")
    if url == "" or url is None:
        url = "https://platform.p.rapidapi.com/"

    url = f"{url}v1/apis/rapidapi-file"
    files = {'file': open(my_file, 'rb')}

    response = requests.request("POST", url, files=files, headers=headers)
    return response.json()["apiId"]

    # params = {
    #     "creations": [
    #         {
    #             "spec": oas,
    #             "specType": "OPENAPI",
    #             "category": "Utility APIs",
    #             "name": name,
    #             "description": description
    #         }
    #     ]
    # }
    # res = c.execute(create_api_listing, variable_values=params,
    #                 upload_files=True)
    # return res["createApisFromSpecs"][0]["apiId"]


def create_api_version(version_name, api_id, c):
    """
    Creates and returns a new API version for a given API
    """
    create_api_version_mutation = gql(
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
    res = c.execute(create_api_version_mutation, variable_values=params)
    return res["createApiVersions"][0]["id"]


def update_api_version(spec_path, api_id, api_version_id, c=None):
    """
    Upload a spec into the newly created API version
    This has to be based on the REST PAPI until the GraphQL PAPI parses
    metadata
    """
    # update_api_version = gql(
    #     """
    #     mutation updateApisFromSpecs($updates: [ApiUpdateFromSpecInput!]!) {
    #         updateApisFromSpecs(updates: $updates) {
    #             apiId
    #         }
    #     }
    #     """
    # )
    # with open(spec_path, "rb") as oas:
    #     params = {
    #         "updates": [
    #             {
    #                 "spec": oas,
    #                 "specType": "OPENAPI",
    #                 "apiVersionId": api_version_id
    #             }
    #         ]
    #     }
    #     res = c.execute(update_api_version, variable_values=params,
    #                     upload_files=True)
    #     return res["updateApisFromSpecs"][0]["apiId"]

    headers = {
        "x-rapidapi-key": needenv("INPUT_X_RAPIDAPI_KEY"),
        "x-rapidapi-host": needenv("INPUT_X_RAPIDAPI_REST_HOST")
    }
    # Weird syntax to work around GitHub Actions issue #924
    url = os.getenv("INPUT_REST_URL")
    if url == "":
        url = "https://platform.p.rapidapi.com/"

    url = f"{url}v1/apis/rapidapi-file/" + \
          f"{api_id}/versions/{api_version_id}"
    files = {'file': open(spec_path, 'rb')}

    requests.request("PUT", url, files=files, headers=headers)


def create_or_update():
    """
    Create a new listing, or update an existing listing on RapidAPI Hub
    """

    # Verifying environment variables
    x_rapidapi_key = needenv("INPUT_X_RAPIDAPI_KEY")

    # Weird syntax to work around GitHub Actions issue #924
    x_rapidapi_identity_key = os.getenv("INPUT_X_RAPIDAPI_KEY")
    if x_rapidapi_identity_key == "":
        x_rapidapi_identity_key = x_rapidapi_key

    x_rapidapi_graphql_host = needenv("INPUT_X_RAPIDAPI_GRAPHQL_HOST")
    # won't explicitly use this, only in the context of creating APIs and API
    #  versions, but want to check whether it exists before we create things
    _x_rapidapi_rest_host = needenv("INPUT_X_RAPIDAPI_REST_HOST")  # noqa: F841
    rapidapi_owner_id = needenv("INPUT_OWNER_ID")
    spec_path = needenv("INPUT_SPEC_PATH")

    # Create header dictionary for the GraphQL PAPI based on input from GitHub
    headers = {
        "x-rapidapi-key": x_rapidapi_key,
        "x-rapidapi-host": x_rapidapi_graphql_host,
        "x-rapidapi-identity-key": x_rapidapi_identity_key
    }

    # setting up connection to GraphQL PAPI
    # Weird syntax to work around GitHub Actions issue #924
    graphql_url = os.getenv("INPUT_GRAPHQL_URL")
    if graphql_url == "" or graphql_url is None:
        graphql_url = "https://graphql-platform.p.rapidapi.com/"

    transport = AIOHTTPTransport(url=graphql_url, headers=headers)
    client = Client(transport=transport, fetch_schema_from_transport=False)

    # Start reading spec
    spec = read_spec(spec_path)
    spec_version = get_spec_version(spec)
    api_name = get_api_name(spec)
    print(f"API name: {api_name}")
    print(f"Spec version: {spec_version}")

    api_id = already_exists(api_name, rapidapi_owner_id, client)
    if api_id is None:
        print("This is a new API, creating a new listing...")
        new_id = create_new_listing(spec_path, client)
        print(f"New API created with id: {new_id}")
        print("Grabbing id of newly created version")
        current_version = get_current_api_version(new_id, client)

        print(f"::set-output name=api_id::{new_id}")
        print(f"::set-output name=api_version_name::{current_version[0]}")
        print(f"::set-output name=api_version_id::{current_version[1]}")
    else:
        print(f"API already exists with id: {api_id}")
        current_version = get_current_api_version(api_id, client)
        parsed_spec_version = semver.VersionInfo.parse(spec_version)
        parsed_current_version = semver.VersionInfo.parse(current_version[0])
        print(f"parsed spec version: {parsed_spec_version}")
        print(f"current version: {parsed_current_version}")
        spec_is_newer = parsed_spec_version > parsed_current_version
        print("Uploaded spec is newer:", spec_is_newer)

        if spec_is_newer:
            print(f"Creating new api version for api {api_id}")
            api_version_id = create_api_version(parsed_spec_version,
                                                api_id, client)
            print(f"New api version id: {api_version_id}")
            update_api_version(spec_path, api_id, api_version_id, client)
            print("Setting new version as current")
            set_created_version_as_active(api_version_id, client)
            print(f"::set-output name=api_id::{api_id}")
            print(f"::set-output name=api_version_name::{parsed_spec_version}")
            print(f"::set-output name=api_version_id::{api_version_id}")
        else:
            print("Uploaded spec is not newer than the current version.")
            sys.exit(1)


if __name__ == '__main__':
    create_or_update()
