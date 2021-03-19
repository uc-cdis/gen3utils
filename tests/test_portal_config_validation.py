import pytest
from gen3utils.errors import FieldError
from gen3utils.gitops.gitops_validator import (
    check_field_value,
    check_required_fields,
    map_all_ES_index_props,
    val_gitops,
    validate_against_dictionary,
    validate_against_etl,
    validate_explorerConfig,
    validate_studyViewerConfig,
    validate_gitops_syntax,
)

data_dict = "https://s3.amazonaws.com/dictionary-artifacts/covid19-datadictionary/3.8.1/schema.json"
etlmapping = "tests/data/etlMapping_gitops.yaml"


def test_check_required_fields():
    checks = ["check1", "check2"]
    ok = True
    ok = check_required_fields("path", checks, {}, ok)
    assert not ok

    ok = True
    ok = check_required_fields("path", checks, {"check1": "1", "check2": ""}, ok)
    assert not ok

    ok = True
    ok = check_required_fields("path", checks, {"check1": "1", "check2": "2"}, ok)
    assert ok


def test_check_field_value():
    checks = ["check1", "check4"]
    accepted_vals = ["check1", "check2", "check3"]
    errors = []
    check_field_value("path", checks, accepted_vals, errors)
    assert errors == [FieldError("Field check4 in path not found in ETLmapping")]

    checks = ["check1", "check2"]
    accepted_vals = ["check1", "check2", "check3"]
    errors = ["error"]
    check_field_value("path", checks, accepted_vals, errors)
    assert errors == ["error"]


def test_validate_explorerConfig(gitops_json, etl_prop_type_map):

    errors = validate_explorerConfig(gitops_json, etl_prop_type_map, [])
    assert errors == [
        FieldError(
            "Field investigator_affiliation in explorerConfig.filters.tabs.fields not found in ETLmapping"
        ),
        FieldError(
            "Field investigator_affiliation in explorerConfig.table.fields not found in ETLmapping"
        ),
    ]

    gitops_json["explorerConfig"][0]["table"]["enabled"] = False
    errors = validate_explorerConfig(gitops_json, etl_prop_type_map, [])
    assert errors == [
        FieldError(
            "Field investigator_affiliation in explorerConfig.filters.tabs.fields not found in ETLmapping"
        )
    ]


def test_map_all_ES_index_props(gitops_etl_mapping, etl_prop_type_map):
    mapping = map_all_ES_index_props(gitops_etl_mapping.get("mappings"))
    assert etl_prop_type_map == mapping


def test_validate_against_dictionary(gitops_json):
    ok = validate_against_dictionary(gitops_json, data_dict)
    assert ok

    gitops_json["graphql"]["boardCounts"][0]["graphql"] = "_notanode_count"
    ok = validate_against_dictionary(gitops_json, data_dict)
    assert not ok


def test_validate_against_etl(gitops_json):
    errors = validate_against_etl(gitops_json, "tests/data/etlMapping_gitops.yaml")
    assert errors == [
        FieldError(
            "Field investigator_affiliation in explorerConfig.filters.tabs.fields not found in ETLmapping"
        ),
        FieldError(
            "Field investigator_affiliation in explorerConfig.table.fields not found in ETLmapping"
        ),
    ]


def test_validate_studyViewerConfig(gitops_json, etl_prop_type_map):
    study_viewer = gitops_json["studyViewerConfig"]
    errors = []
    validate_studyViewerConfig(study_viewer, etl_prop_type_map, errors)
    assert errors == []

    # valid datatype but invalid fields
    study_viewer[0]["dataType"] = "dataset"
    errors = []
    validate_studyViewerConfig(study_viewer, etl_prop_type_map, errors)
    assert errors == [
        FieldError(
            "Field project_id in studyViewerConfig.blockFields.listItemConfig not found in ETLmapping"
        ),
        FieldError(
            "Field study_doi in studyViewerConfig.tableFields.singleItemConfig not found in ETLmapping"
        ),
    ]

    # invalid datatype
    study_viewer[0]["dataType"] = "error"
    errors = []
    validate_studyViewerConfig(study_viewer, etl_prop_type_map, errors)
    assert errors == [
        FieldError("Field error in studyViewerConfig.dataType not found in ETLmapping"),
        FieldError("rowAccessor code not found in index with type error"),
        FieldError(
            "Field project_id in studyViewerConfig.blockFields.listItemConfig not found in ETLmapping"
        ),
        FieldError(
            "Field study_doi in studyViewerConfig.tableFields.singleItemConfig not found in ETLmapping"
        ),
    ]


def test_val_gitops():
    # syntax error
    with pytest.raises(AssertionError):
        val_gitops(data_dict, etlmapping, "tests/data/gitops_syntax_error.json")

    # etl mapping errors
    errors, ok = val_gitops(data_dict, etlmapping, "tests/data/gitops_test.json")
    assert errors == [
        FieldError(
            "Field investigator_affiliation in explorerConfig.filters.tabs.fields not found in ETLmapping"
        ),
        FieldError(
            "Field investigator_affiliation in explorerConfig.table.fields not found in ETLmapping"
        ),
    ]
    assert ok

    # dictionary error
    _, ok = val_gitops(data_dict, etlmapping, "tests/data/gitops_dict_error.json")
    assert not ok


def test_validate_syntax(gitops_json_syntax_error):
    ok = validate_gitops_syntax(gitops_json_syntax_error)
    assert not ok
