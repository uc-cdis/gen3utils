from gen3utils.validate import (
    validate_manifest_block,
    versions_validation,
    manifest_version,
)


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
        "fence": "quay.io/cdis/fence:4.6.1",
        "arborist": "quay.io/cdis/arborist:2.3.0",
    }
    ok = versions_validation(versions_block, validation_config["versions"])
    assert ok, "fence 4.6.1 + arborist 2.3.0 should pass validation"

    versions_block = {
        "fence": "quay.io/cdis/fence:4.6.1",
        "arborist": "quay.io/cdis/arborist:1.0.0",
    }
    ok = versions_validation(versions_block, validation_config["versions"])
    assert not ok, "fence 4.6.1 + arborist 1.0.0 should not pass validation"

    versions_block = {
        "fence": "quay.io/cdis/fence:4.4.4",
        "arborist": "quay.io/cdis/arborist:2.2.0",
    }
    ok = versions_validation(versions_block, validation_config["versions"])
    assert ok, "fence 4.4.4 + arborist 2.2.0 should pass validation"

    versions_block = {
        "fence": "quay.io/cdis/fence:4.4.4",
        "arborist": "quay.io/cdis/arborist:1.0.0",
    }
    ok = versions_validation(versions_block, validation_config["versions"])
    assert not ok, "fence 4.4.4 + arborist 1.0.0 should not pass validation"

    versions_block = {
        "sower": "quay.io/cdis/sower:0.3.0",
        "guppy": "quay.io/cdis/guppy:0.3.0",
    }
    ok = versions_validation(versions_block, validation_config["versions"])
    assert ok, "sower + guppy should pass validation"

    versions_block = {"sower": "quay.io/cdis/sower:0.3.0"}
    ok = versions_validation(versions_block, validation_config["versions"])
    assert not ok, "sower without guppy should not pass validation"


def test_validate_manifest_block(validation_config):
    """
    Test validation of sevice having block requirements in manifest for validation
    """
    block_requirement = {
        "versions": {"arborist": "quay.io/cdis/arborist:2.2.0"},
        "arborist": {"deployment_version": "2"},
    }
    ok = validate_manifest_block(block_requirement, validation_config["block"])
    assert (
        ok
    ), "arborist 2.2.0 with deployment_version in arborist blcok should pass validation"

    block_requirement = {"versions": {"arborist": "quay.io/cdis/arborist:2.2.0"}}
    ok = validate_manifest_block(block_requirement, validation_config["block"])
    assert (
        not ok
    ), "arborist 2.2.0 without deployment_version in arborist blcok should not pass validation"

    block_requirement = {
        "versions": {"hatchery": "quay.io/cdis/hatchery:0.1.0"},
        "hatchery": {
            "sidecar": {
                "cpu-limit": "1.0",
                "memory-limit": "256Mi",
                "image": "quay.io/cdis/gen3fuse-sidecar:chore_sidecar",
                "env": {"NAMESPACE": "default", "HOSTNAME": "whatever"},
                "args": [],
                "command": ["/bin/bash", "/sidecarDockerrun.sh"],
                "lifecycle-pre-stop": [
                    "su",
                    "-c",
                    "echo test",
                    "-s",
                    "/bin/sh",
                    "root",
                ],
            }
        },
    }
    ok = validate_manifest_block(block_requirement, validation_config["block"])
    assert ok, "hatchery with sidecar in hatchery blcok should pass validation"

    block_requirement = {"versions": {"hatchery": "quay.io/cdis/hatchery:0.1.0"}}
    ok = validate_manifest_block(block_requirement, validation_config["block"])
    assert (
        not ok
    ), "hatchery without sidecar in hatchery blcok should not pass validation"

    block_requirement = {
        "versions": {"guppy": "quay.io/cdis/guppy:0.3.0"},
        "guppy": {
            "indices": [{"index": "test", "type": "case"}],
            "auth_filter_field": "auth_resource_path",
        },
    }
    ok = validate_manifest_block(block_requirement, validation_config["block"])
    assert ok, "guppy with guppy block should pass validation"

    block_requirement = {"versions": {"guppy": "quay.io/cdis/guppy:0.3.0"}}
    ok = validate_manifest_block(block_requirement, validation_config["block"])
    assert not ok, "guppy without guppy block should pass validation"
