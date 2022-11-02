from gen3utils.etl.etl_validator import validate_mapping

from tests.utils import print_errors


def test_pass_validation(
    etl_mapping_validation_dict,
    etl_mapping_validation_manifest,
):
    errors = validate_mapping(
        etl_mapping_validation_dict,
        "tests/data/etlMapping.yaml",
        etl_mapping_validation_manifest,
    )
    print_errors(errors)
    assert len(errors) == 0


def test_duplicated_fail_validation(
    etl_mapping_validation_dict,
    etl_mapping_validation_manifest,
):
    errors = validate_mapping(
        etl_mapping_validation_dict,
        "tests/data/etlMapping_duplicate_field_error.yaml",
        etl_mapping_validation_manifest,
    )
    print_errors(errors)
    assert len(errors) == 4
    str_errors = [str(e) for e in errors]
    assert (
        "Properties error: 'project_id' in index 'subject' is duplicated" in str_errors
    )
    assert (
        "Properties error: 'study_objective' in index 'subject' is duplicated"
        in str_errors
    )
    assert "Properties error: 'data_format' in index 'file' is duplicated" in str_errors
    assert "Properties error: 'project_id' in index 'file' is duplicated" in str_errors


def test_fail_validation(
    etl_mapping_validation_dict,
    etl_mapping_validation_manifest,
):
    errors = validate_mapping(
        etl_mapping_validation_dict,
        "tests/data/etlMapping_constraints_error.yaml",
        etl_mapping_validation_manifest,
    )
    print_errors(errors)
    assert len(errors) == 5


def test_fail_format(
    etl_mapping_validation_dict,
    etl_mapping_validation_manifest,
):
    errors = validate_mapping(
        etl_mapping_validation_dict,
        "tests/data/etlMapping_format_error.yaml",
        etl_mapping_validation_manifest,
    )
    print_errors(errors)
    assert len(errors) == 2


def test_pass_validation_collector(
    etl_mapping_validation_dict,
    etl_mapping_validation_manifest,
):
    """
    In "tests/data/etlMapping_collector.yaml" the mapping type is "collector"
    on category "data_file". It contains:
    - "object_id" prop: in all "data_file" nodes;
    - "assay_instrument_model" prop: in "submitted_methylation" node (which is
    a "data_file" node), but not in other "data_file" nodes.
    We should be able to include the "assay_instrument_model" prop in the
    collector index even if it's not available in all "data_file" nodes.
    """
    errors = validate_mapping(
        etl_mapping_validation_dict,
        "tests/data/etlMapping_collector.yaml",
        etl_mapping_validation_manifest,
    )
    print_errors(errors)
    assert len(errors) == 0


def test_fail_validation_collector_unknown_prop(
    etl_mapping_validation_dict,
    etl_mapping_validation_manifest,
):
    """
    Same as above except the "prop_doesnt_exist" prop does not exist in
    ANY node of category "data_file", so we should not be able to include
    it in the collector index.
    """
    errors = validate_mapping(
        etl_mapping_validation_dict,
        "tests/data/etlMapping_collector_unknown_prop.yaml",
        etl_mapping_validation_manifest,
    )
    print_errors(errors)
    assert len(errors) == 1
