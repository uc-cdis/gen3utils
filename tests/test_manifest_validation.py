from gen3utils.manifest.manifest_validator import (
    validate_manifest_block,
    versions_validation,
    manifest_version,
    version_is_branch,
)


def test_manifest_version():
    versions_block = {
        "indexd": "quay.io/cdis/indexd:1.0.0",
        "arborist": "quay.io/cdis/arborist:master",
        "fence": "quay.io/cdis/fence:feat_mybranch",
    }

    indexd_version = manifest_version(versions_block, "indexd")
    assert str(indexd_version) == "1.0.0"

    arborist_version = manifest_version(versions_block, "arborist")
    assert str(arborist_version) == "master"

    fence_version = manifest_version(versions_block, "fence")
    assert str(fence_version) == "feat_mybranch"


def test_service_is_on_branch():
    assert version_is_branch("master")
    assert version_is_branch("feat_new-thing")
    assert not version_is_branch("1.2.14.8")


def test_versions_validation_needs(manifest_validation_config):
    """
    Test validation of "versions" section of manifest for validation
    configuration that uses "needs" keyword
    """
    versions_block = {
        "fence": "quay.io/cdis/fence:4.6.1",
        "arborist": "quay.io/cdis/arborist:2.3.0",
    }
    ok = versions_validation(versions_block, manifest_validation_config["versions"])
    assert ok, "fence 4.6.1 + arborist 2.3.0 should pass validation"

    versions_block = {
        "fence": "quay.io/cdis/fence:4.6.1",
        "arborist": "quay.io/cdis/arborist:1.0.0",
    }
    ok = versions_validation(versions_block, manifest_validation_config["versions"])
    assert not ok, "fence 4.6.1 + arborist 1.0.0 should not pass validation"

    versions_block = {"fence": "quay.io/cdis/fence:4.6.1"}
    ok = versions_validation(versions_block, manifest_validation_config["versions"])
    assert not ok, "fence 4.6.1 + no arborist should not pass validation"

    versions_block = {
        "fence": "quay.io/cdis/fence:4.4.4",
        "arborist": "quay.io/cdis/arborist:2.2.0",
    }
    ok = versions_validation(versions_block, manifest_validation_config["versions"])
    assert ok, "fence 4.4.4 + arborist 2.2.0 should pass validation"

    versions_block = {
        "fence": "quay.io/cdis/fence:4.4.4",
        "arborist": "quay.io/cdis/arborist:1.0.0",
    }
    ok = versions_validation(versions_block, manifest_validation_config["versions"])
    assert not ok, "fence 4.4.4 + arborist 1.0.0 should not pass validation"

    # test for chainning service dependencies
    versions_block = {
        "sower": "quay.io/cdis/sower:0.3.0",
        "guppy": "quay.io/cdis/guppy:0.3.0",
        "aws-es-proxy": "abutaha/aws-es-proxy:0.8",
    }
    ok = versions_validation(versions_block, manifest_validation_config["versions"])
    assert ok, "sower + guppy + aws-es-proxy should pass validation"

    versions_block = {
        "sower": "quay.io/cdis/sower:0.3.0",
        "guppy": "quay.io/cdis/guppy:0.3.0",
    }
    ok = versions_validation(versions_block, manifest_validation_config["versions"])
    assert not ok, "sower + guppy should not pass validation"

    versions_block = {"sower": "quay.io/cdis/sower:0.3.0"}
    ok = versions_validation(versions_block, manifest_validation_config["versions"])
    assert not ok, "sower without guppy should not pass validation"


def test_versions_comparison(manifest_validation_config):
    """
    Makes sure version "10.0.0" is considered higher than version "2.0.0"
    """
    versions_block = {
        "fence": "quay.io/cdis/fence:3.0.0",
        "arborist": "quay.io/cdis/arborist:3.0.0",
    }
    ok = versions_validation(versions_block, manifest_validation_config["versions"])
    assert ok, "fence 3.0.0 + arborist 3.0.0 should pass validation: 3.0.0 > 2.0.0"

    versions_block = {
        "fence": "quay.io/cdis/fence:3.0.0",
        "arborist": "quay.io/cdis/arborist:10.0.0",
    }
    ok = versions_validation(versions_block, manifest_validation_config["versions"])
    assert ok, "fence 3.0.0 + arborist 10.0.0 should pass validation: 10.0.0 > 2.0.0"


def test_validate_manifest_block(manifest_validation_config):
    """
    Test validation of sevice having block requirements in manifest for validation
    """
    block_requirement = {
        "versions": {"arborist": "quay.io/cdis/arborist:2.2.0"},
        "arborist": {"deployment_version": "2"},
    }
    ok = validate_manifest_block(block_requirement, manifest_validation_config["block"])
    assert (
        ok
    ), "arborist 2.2.0 with deployment_version in arborist block should pass validation"

    block_requirement = {"versions": {"arborist": "quay.io/cdis/arborist:2.2.0"}}
    ok = validate_manifest_block(block_requirement, manifest_validation_config["block"])
    assert (
        not ok
    ), "arborist 2.2.0 without deployment_version in arborist block should not pass validation"

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
    ok = validate_manifest_block(block_requirement, manifest_validation_config["block"])
    assert ok, "hatchery with sidecar in hatchery block should pass validation"

    block_requirement = {
        "versions": {"hatchery": "quay.io/cdis/hatchery:0.1.0"},
        "hatchery": {},
    }
    ok = validate_manifest_block(block_requirement, manifest_validation_config["block"])
    assert (
        not ok
    ), "hatchery without sidecar in hatchery block should not pass validation"

    block_requirement = {
        "versions": {"guppy": "quay.io/cdis/guppy:0.3.0"},
        "guppy": {
            "indices": [{"index": "test", "type": "case"}],
            "auth_filter_field": "auth_resource_path",
        },
    }
    ok = validate_manifest_block(block_requirement, manifest_validation_config["block"])
    assert ok, "guppy with guppy block should pass validation"

    block_requirement = {"versions": {"guppy": "quay.io/cdis/guppy:0.3.0"}}
    ok = validate_manifest_block(block_requirement, manifest_validation_config["block"])
    assert not ok, "guppy without guppy block should pass validation"
