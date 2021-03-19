# gen3utils

Utils for Gen3 commons management

## Install with pip
pip install gen3utils

## manifest.json validation

Validate one or more `manifest.json` files:
```
gen3utils validate-manifest cdis-manifest/*/manifest.json
```

The validation settings can be updated by modifying [this file](gen3utils/manifest/validation_config.yaml).

## etlMapping.yaml validation

Validate an `etlMapping.yaml` file against the dictionary URL specified in a `manifest.json` file:
```
gen3utils validate-etl-mapping etlMapping.yaml manifest.json
```

## Portal Configuration (gitops.json) validation

Validate a `gitops.json` file against the dictionary URL specified in a `manifest.json` file and an etlMapping.yaml file. Adds a comment to a pull request listing all the errors encountered when validating against etlMapping.yaml
```
gen3utils validate-portal-config etlMapping.yaml manifest.json gitops.json <username>/<repository> <pull request number>
```
To run without making a pull request comment
```
gen3utils validate-portal-config etlMapping.yaml manifest.json gitops.json
```


## Comment on a PR with any deployment changes when updating manifest services

The command requires the name of the repository, the pull request number and **a `GITHUB_TOKEN` environment variable** containing a token with read and write access to the repository. It also comments a warning if a service is pinned on a branch.
```
pip install gen3utils
gen3utils post-deployment-changes <username>/<repository> <pull request number>
```

## Log parser for CTDS log pipeline

```
pip install gen3utils
gen3utils s3log --help
gen3utils s3log [OPTIONS] BUCKET PREFIX SCRIPT
```

Run `SCRIPT` in Gen3 logs under S3 `BUCKET:PREFIX`. The `SCRIPT` should be importable defining a method like this:
```
def handle_row(obj, line):
    if 1 + 1 == 2:
        return line
```

For example, to process logs in bucket `my-commons-logs` at prefix `my-logs` with a `gen3utils/script.py` file:
```
pip install gen3utils
gen3utils s3log my-commons-logs my-logs gen3utils.script
```

## Running tests locally

```
poetry install -vv
poetry run pytest -vv ./tests
```
