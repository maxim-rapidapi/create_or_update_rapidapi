# Create or update an API on RapidAPI Hub

[![Action Template](https://img.shields.io/badge/Create%20or%20update%20an%20API%20on%20RapidAPI%20Hub-blue.svg?colorA=24292e&colorB=0366d6&style=flat&longCache=true&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAOCAYAAAAfSC3RAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAM6wAADOsB5dZE0gAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAERSURBVCiRhZG/SsMxFEZPfsVJ61jbxaF0cRQRcRJ9hlYn30IHN/+9iquDCOIsblIrOjqKgy5aKoJQj4O3EEtbPwhJbr6Te28CmdSKeqzeqr0YbfVIrTBKakvtOl5dtTkK+v4HfA9PEyBFCY9AGVgCBLaBp1jPAyfAJ/AAdIEG0dNAiyP7+K1qIfMdonZic6+WJoBJvQlvuwDqcXadUuqPA1NKAlexbRTAIMvMOCjTbMwl1LtI/6KWJ5Q6rT6Ht1MA58AX8Apcqqt5r2qhrgAXQC3CZ6i1+KMd9TRu3MvA3aH/fFPnBodb6oe6HM8+lYHrGdRXW8M9bMZtPXUji69lmf5Cmamq7quNLFZXD9Rq7v0Bpc1o/tp0fisAAAAASUVORK5CYII=)](https://github.com/rapidapi/create-or-update-rapidapi)
[![Actions Status](https://github.com/maxim-rapidapi/create_or_update_rapidapi/workflows/Lint/badge.svg)](https://github.com/maxim-rapidapi/create_or_update_rapidapi/actions)
[![Actions Status](https://github.com/maxim-rapidapi/create_or_update_rapidapi/workflows/Integration%20Test/badge.svg)](https://github.com/maxim-rapidapi/create_or_update_rapidapi/actions)

This is a preview release of a GitHub action designed to make it easy to onboard
new APIs onto RapidAPI Hub or Enterprise Hub, or create new versions of existing
APIs. It uses the RapidAPI Platform API to upload an OpenAPI spec file and
returns the ID of the new API, as well as the name and ID of the newly created
API version.

This action is based on Jacob Tomlinson's excellent [template
repository](https://github.com/jacobtomlinson/python-container-action) for
Python based GitHub actions.

## Usage

The action needs an OpenAPI v3.0 spec file in JSON format to exist in the repo. The
name of this file (or path to it, if it is in a subdirectory), needs to be fed to
the action by setting the `spec_path` environment variable. 

### Requirements 
If you are a RapidAPI Enterprise Hub user, you need both the REST Platform API
as well as the preview of the GraphQL Platform API enabled in your Hub. You will
need credentials (the `x-rapidapi-key` and `x-rapidapi-host` headers) of a user
or team that is enabled to use both of these APIs, as well as their owner ID.

### Example workflow

```yaml
name: My API Workflow
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@master
    - name: Upload OAS to RapidAPI Hub for processing
      uses: maxim-rapidapi/create_or_update_rapidapi@v1
      with:
        spec_path: openapi.json
        owner_id: 12345678
        x_rapidapi_host: graphql-platform.yourhub.rapidapi.com
        x_rapidapi_key: a-very-long-api-key
        x_rapidapi_rest_host: platform.yourhub.rapidapi.com
```

### Inputs

| Input                                             | Description                                        | Required |
|------------------------------------------------------|-----------------------------------------------|-----------|
| `spec_path`  | Path to the OpenAPI spec file in JSON format | True |
| `owner_id`  | The ID of the owning entity of an API on the Hub. This can be either a user ID or a team ID. | True |
| `x_rapidapi_key`  | API key for the user / the team that will own this API on the Hub | True |
| `x_rapidapi_graphql_host`  | GraphQL platform API host for the user / the team that will own this API on the Hub (e.g. `graphql-platform.yourhub.rapidapi.com`) | True |
| `x_rapidapi_rest_host`  | REST platform API host for the user / the team that will own this API on the Hub (e.g. `platform.yourhub.rapidapi.com`) | True |
| `x_rapidapi_identity_key`  | API identity key for the user / the team that will own this API on the Hub | False |
| `graphql_url` | The URL to the GraphQL Platform API, defaults to `https://graphql-platform.p.rapidapi.com/` (mind the slash!) | False |
| `rest_url` | The URL to the REST Platform API, defaults to `https://platformapi.p.rapidapi.com/` (mind the slash!) | False |

### Outputs

| Output                                             | Description                                        |
|------------------------------------------------------|-----------------------------------------------|
| `api_id`  | The ID of the newly created or updated API on the RapidAPI Hub |
| `api_version_name`  | The name (e.g. v0.2.0) of the newly created API version on the RapidAPI Hub |
| `api_version_id`  | The ID of the newly created API version on the RapidAPI Hub |

### Using the optional input

This is how to use the optional input.

```yaml
name: My API Workflow
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@master
    - name: Upload OAS to RapidAPI Hub for processing
      uses: maxim-rapidapi/create_or_update_rapidapi@v1
      with:
        spec_path: openapi.json
        owner_id: 12345678
        x_rapidapi_host: graphql-platform.yourhub.rapidapi.com
        x_rapidapi_key: a-very-secure-api-key
        x_rapidapi_identity_key: another-very-secure-api-key
        x_rapidapi_rest_host: platform.yourhub.rapidapi.com
        x_rapidapi_rest_url: https://restpapi.p.rapidapi.com/
        x_rapidapi_graphql_url: https://graphql-papi.p.rapidapi.com/
```

### Using outputs

The outputs of this action (`api_id` and `api_version_id`) can be used as input
to subsequent actions:

```yaml
steps:
- uses: actions/checkout@master
- name: Upload OAS to RapidAPI Hub for processing
  id: rapidapi-upload
  uses: maxim-rapidapi/creat_or_update_rapidapi@v1
  with:
    spec_path: openapi.json
    [...]

- name: Check outputs
    run: |
    echo "New API ID - ${{ steps.rapidapi-upload.outputs.api_id }}"
    echo "New API Version ID - ${{ steps.rapidapi-upload.outputs.api_version_id }}"
```

### Limitations
Eventually, this action will only call the GraphQL Platform API. For the time
being, it needs to call both, which is why you need to provide both the
`x_rapidapi_rest_host` and `x_rapidapi_host` variables.

Using the `on-behalf-of` header is currently not supported. This only impacts
the API calls for the creation of new APIs and new API versions.
