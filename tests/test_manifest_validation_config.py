def test_min_max(manifest_validation_config):
    message = "For now, we do not handle versions validation with either min or max but not both - either fix the config or update the validation code to handle it: {}"
    for requirement in manifest_validation_config.get("versions"):
        for key, details in requirement.items():
            if key != "needs":
                assert ("min" in details and "max" in details) or (
                    "min" not in details and "max" not in details
                ), message.format(requirement)
            else:
                for need_details in details.values():
                    assert ("min" in need_details and "max" in need_details) or (
                        "min" not in need_details and "max" not in need_details
                    ), message.format(requirement)


def test_description(manifest_validation_config):
    for requirement in manifest_validation_config.get("versions"):
        assert requirement.get(
            "desc"
        ), 'Missing description of requirement for "{}"'.format(requirement)
