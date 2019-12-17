# gen3utils

Utils for Gen3 commons management

## manifest.json validation

Validate one or more `manifest.json` files using the CLI:
```
pip install gen3utils
gen3utils validate cdis-manifest/*/manifest.json
```

The validation settings can be updated by modifying [this file](gen3utils/validation_config.yaml).


## dev-test

```
python setup.py install
python -m pytest
```
