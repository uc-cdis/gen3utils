from gen3utils.validate import blocks_validation, versions_validation, manifest_version


def test_manifest_version():
    versions_block = {
        "indexd": "quay.io/cdis/indexd:1.0.0",
        "arborist": "quay.io/cdis/arborist:master",
        "fence": "quay.io/cdis/fence:feat_mybranch",
    }

    indexd_version = manifest_version(versions_block, "indexd")
    assert indexd_version == "1.0.0"

    arborist_version = manifest_version(versions_block, "arborist")
    assert arborist_version == "master"

    fence_version = manifest_version(versions_block, "fence")
    assert fence_version == "feat_mybranch"


def test_versions_validation_needs(validation_config):
    """
    Test validation of "versions" section of manifest for validation
    configuration that uses "needs" keyword
    """
    versions_block = {
        "fence": "quay.io/cdis/fence:3.0.0",
        "arborist": "quay.io/cdis/arborist:2.2.0",
    }
    ok = versions_validation(versions_block, validation_config["versions"])
    assert ok, "fence 3.0.0 + arborist 2.2.0 should pass validation"

    versions_block = {
        "fence": "quay.io/cdis/fence:3.0.0",
        "arborist": "quay.io/cdis/arborist:1.0.0",
    }
    ok = versions_validation(versions_block, validation_config["versions"])
    assert not ok, "fence 3.0.0 + arborist 1.0.0 should not pass validation"
