import os
import pytest
import yaml


CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture(scope="session")
def validation_config():
    requirements_file = os.path.join(
        CURRENT_DIR, "../gen3utils/manifest/validation_config.yaml"
    )
    with open(requirements_file, "r") as f:
        requirements = yaml.safe_load(f.read())
    return requirements
