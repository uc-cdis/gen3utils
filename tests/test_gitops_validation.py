import pytest
import copy
from gen3utils.errors import FieldError, FieldSyntaxError
from gen3utils.gitops.gitops_validator import (
    check_field_value,
    check_required_fields,
    map_all_ES_index_props,
    val_gitops,
    validate_against_dictionary,
    validate_against_etl,
    validate_explorerConfig,
    validate_studyViewerConfig,
)

data_dict = "https://s3.amazonaws.com/dictionary-artifacts/covid19-datadictionary/3.8.1/schema.json"


def test_check_required_fields():
    checks = ["check1", "check2"]
    error = check_required_fields("path", checks, {})
    assert error == FieldSyntaxError("path.check1")

    error = check_required_fields("path", checks, {"check1": "1", "check2": ""})
    assert error == FieldSyntaxError("path.check2")

    error = check_required_fields("path", checks, {"check1": "1", "check2": "2"})
    assert error == None


def test_check_field_value():
    checks = ["check1", "check4"]
    accepted_vals = ["check1", "check2", "check3"]
    errors = check_field_value("path", checks, accepted_vals, [])
    assert errors == [FieldError("Invalid field check4 in path")]

    checks = ["check1", "check2"]
    accepted_vals = ["check1", "check2", "check3"]
    errors = check_field_value("path", checks, accepted_vals, ["error"])
    assert errors == ["error"]


def test_validate_explorerConfig(gitops_json, etl_prop_type_map):

    errors = validate_explorerConfig(gitops_json, etl_prop_type_map, [])
    assert errors == [
        FieldError(
            "Invalid field investigator_affiliation in explorerConfig.filters.tabs.fields"
        ),
        FieldError(
            "Invalid field investigator_affiliation in explorerConfig.table.fields"
        ),
    ]

    gitops_json["explorerConfig"][0]["table"]["enabled"] = False
    errors = validate_explorerConfig(gitops_json, etl_prop_type_map, [])
    assert errors == [
        FieldError(
            "Invalid field investigator_affiliation in explorerConfig.filters.tabs.fields"
        )
    ]


def test_map_all_ES_index_props(gitops_etl_mapping, etl_prop_type_map):
    mapping = map_all_ES_index_props(gitops_etl_mapping.get("mappings"))
    print("mapingsss")
    for k, v in mapping.items():
        print(k, v)
    print("tests")
    for k, v in etl_prop_type_map.items():
        print(k, v)
    assert etl_prop_type_map == mapping


def test_validate_against_dictionary(gitops_json):
    ok = validate_against_dictionary(gitops_json, data_dict)
    assert ok == True

    gitops_json["graphql"]["boardCounts"][0]["graphql"] = "_notanode_count"
    ok = validate_against_dictionary(gitops_json, data_dict)
    assert ok == False


def test_validate_against_etl(gitops_json):
    errors = validate_against_etl(gitops_json, "tests/data/etlMapping_gitops.yaml")
    assert errors == [
        FieldError(
            "Invalid field investigator_affiliation in explorerConfig.filters.tabs.fields"
        ),
        FieldError(
            "Invalid field investigator_affiliation in explorerConfig.table.fields"
        ),
    ]


def test_validate_studyViewerConfig(gitops_json, etl_prop_type_map):
    study_viewer = gitops_json["studyViewerConfig"]
    errors = validate_studyViewerConfig(study_viewer, etl_prop_type_map, [])
    assert errors == []

    # valid datatype but invalid fields
    study_viewer[0]["dataType"] = "dataset"
    errors = validate_studyViewerConfig(study_viewer, etl_prop_type_map, [])
    assert errors == [
        FieldError(
            "Invalid field project_id in studyViewerConfig.blockFields.(list/single)ItemConfig"
        ),
        FieldError(
            "Invalid field study_doi in studyViewerConfig.tableFields.(list/single)ItemConfig"
        ),
    ]

    # invalid datatype
    study_viewer[0]["dataType"] = "error"
    errors = validate_studyViewerConfig(study_viewer, etl_prop_type_map, [])
    assert errors == [
        FieldError("Invalid field error in studyViewerConfig.dataType"),
        FieldError(
            "Invalid field project_id in studyViewerConfig.blockFields.(list/single)ItemConfig"
        ),
        FieldError(
            "Invalid field study_doi in studyViewerConfig.tableFields.(list/single)ItemConfig"
        ),
    ]


def test_val_gitops(gitops_etl_mapping):

    # etl mapping errors
    errors = val_gitops(data_dict, gitops_etl_mapping, "tests/data/gitops_test.json")
    assert errors == [
        FieldError(
            "Invalid field investigator_affiliation in explorerConfig.filters.tabs.fields"
        ),
        FieldError(
            "Invalid field investigator_affiliation in explorerConfig.table.fields"
        ),
    ]

    # syntax error
    with pytest.raises(AssertionError):
        val_gitops(data_dict, gitops_etl_mapping, "tests/data/gitops_syntax_error.json")

    # dictionary error
    with pytest.raises(AssertionError):
        val_gitops(data_dict, gitops_etl_mapping, "tests/data/gitops_dict_error.json")


def test_validate_syntax(gitops_json_syntax_error):
    with pytest.raises(AssertionError):
        validate_gitops_syntax(gitops_json_syntax_error)
