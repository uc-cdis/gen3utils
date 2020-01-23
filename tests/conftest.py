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
    return "https://s3.amazonaws.com/dictionary-artifacts/tb-datadictionary/1.1.5/schema.json"


@pytest.fixture(scope="session")
def etl_mapping_validation_mapping():
    return "tests/data/etlMapping.yaml"


@pytest.fixture(scope="session")
def etl_mapping_validation_mapping_failed():
    return "tests/data/etlMapping_constraints_error.yaml"


@pytest.fixture(scope="session")
def etl_mapping_validation_format_failed():
    return "tests/data/etlMapping_format_error.yaml"
