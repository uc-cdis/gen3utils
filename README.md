# gen3utils

Utils for Gen3 commons management

## manifest.json validation

Validate one or more `manifest.json` files:
```
pip install gen3utils
gen3utils validate_manifest cdis-manifest/*/manifest.json
```

The validation settings can be updated by modifying [this file](gen3utils/validation_config.yaml).

## :construction: etlMapping.yaml validation :construction:

> This feature is still in development!

Validate an `etlMapping.yaml` file against the dictionary URL specified in a `manifest.json` file:
```
pip install gen3utils
gen3utils validate_etl_mapping etlMapping.yaml manifest.json
```

## Dev test

```
python setup.py install
python -m pytest
```
