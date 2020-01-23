import yaml

from gen3utils.etl.etl_validator import validate_mapping


def test_pass_validation(etl_mapping_validation_dict, etl_mapping_validation_mapping):
    errors = validate_mapping(
        etl_mapping_validation_dict, etl_mapping_validation_mapping
    )
    assert len(errors) == 0


def test_fail_validation(
    etl_mapping_validation_dict, etl_mapping_validation_mapping_failed
):
    errors = validate_mapping(
        etl_mapping_validation_dict, etl_mapping_validation_mapping_failed
    )
    assert len(errors) == 5


def test_fail_format(etl_mapping_validation_dict, etl_mapping_validation_format_failed):
    errors = validate_mapping(
        etl_mapping_validation_dict, etl_mapping_validation_format_failed
    )
    assert len(errors) == 2
