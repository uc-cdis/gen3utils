import os
import pytest
import requests
from unittest.mock import MagicMock
import yaml
import json

import mock


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
    return "https://s3.amazonaws.com/my-bucket/test-tb-dictionary/1.0/schema.json"


@pytest.fixture(scope="session")
def etl_mapping_validation_manifest():
    with open("tests/data/manifest.json") as f:
        return json.load(f)


@pytest.fixture(scope="function")
def gitops_json():
    with open("tests/data/gitops_test.json", "r") as f:
        data = json.loads(f.read())
    return data


@pytest.fixture(scope="function")
def gitops_json_syntax_error():
    with open("tests/data/gitops_syntax_error.json", "r") as f:
        data = json.loads(f.read())
    return data


@pytest.fixture(scope="function")
def etl_prop_type_map():
    type_map = {
        "subject": set(
            [
                "project_id",
                "project_url",
                "project_name",
                "vital_status",
                "gender",
                "age",
                "image_location",
                "code",
                "study_doi",
                "location",
                "continent",
                "imaging_studies.study_modality",
            ]
        ),
        "dataset": set(["code", "name", "program_name"]),
    }
    return type_map


@pytest.fixture(scope="function")
def gitops_etl_mapping():
    with open("tests/data/etlMapping_gitops.yaml", "r") as f:
        data = yaml.safe_load(f.read())
    return data


@pytest.fixture(autouse=True)
def mock_dictionary_requests():
    def _mock_request(url, **kwargs):
        mocked_response = MagicMock(requests.Response)
        mocked_response.status_code = 200
        data = {}
        if (
            url
            == "https://s3.amazonaws.com/my-bucket/test-tb-dictionary/1.0/schema.json"
        ):
            with open("tests/data/schema_tb.json", "r") as f:
                data = f.read()
        elif (
            url
            == "https://s3.amazonaws.com/my-bucket/test-covid-dictionary/2.0/schema.json"
        ):
            with open("tests/data/schema_covid.json", "r") as f:
                data = f.read()
        mocked_response.text = data
        return mocked_response

    mock.patch(
        "dictionaryutils.requests.get", MagicMock(side_effect=_mock_request)
    ).start()
