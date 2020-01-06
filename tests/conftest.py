import os
import pytest
import yaml


CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture(scope="session")
def manifest_validation_config():
    requirements_file = os.path.join(
        CURRENT_DIR, "../gen3utils/manifest/validation_config.yaml"
    )
    with open(requirements_file, "r") as f:
        requirements = yaml.safe_load(f.read())
    return requirements


@pytest.fixture(scope="session")
def etl_mapping_validation_dict():
    return "https://s3.amazonaws.com/dictionary-artifacts/datadictionary/develop/schema.json"


@pytest.fixture(scope="session")
def etl_mapping_validation_mapping():
    with open("tests/exampleEtlMapping.yaml", "r") as f:
        return yaml.safe_load(f.read()).get("mappings")
