import os

from gen3utils.deployment_changes.generate_comment import (
    get_versions_dict,
    compare_versions_blocks,
    check_services_on_branch,
    get_repo_name,
    get_downgraded_services,
)


def get_test_versions():
    old_versions = {
        "arborist": "quay.io/cdis/arborist:2.0.0",
        "audit-service": "quay.io/cdis/audit-service:2.0.0",
        "fence": "quay.io/cdis/fence:2.0.0",
        "indexd": "quay.io/cdis/indexd:2.0.0",
        "peregrine": "quay.io/cdis/peregrine:2.0.0",
        "sheepdog": "quay.io/cdis/sheepdog:master",  # old and new on branch
        "guppy": "quay.io/cdis/pidgin:2.0.0",  # deleted service
        "ambassador": "quay.io/cdis/hello-branch",
    }
    new_versions = {
        "arborist": "quay.io/cdis/arborist:3.0.0",  # new > old
        "audit-service": "707767160287.dkr.ecr.us-east-1.amazonaws.com/gen3/audit-service:2.1.0",  # new > old + ECR image
        "fence": "quay.io/cdis/fence:1.0.0",  # new < old
        "indexd": "quay.io/cdis/indexd:2.0.0",  # new == old
        "peregrine": "quay.io/cdis/peregrine:feat_something",  # new on branch
        "sheepdog": "quay.io/cdis/sheepdog:master",  # old and new on branch
        "pidgin": "quay.io/cdis/pidgin:2.0.0",  # new service
        "ambassador": "quay.io/cdis/hello-branch",  # branch to ignore
    }
    return old_versions, new_versions


def test_compare_versions(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake_token")
    old_versions, new_versions = get_test_versions()

    compared = compare_versions_blocks(old_versions, new_versions, True)
    print("Compared versions:", compared)

    assert "arborist" in compared
    assert compared["arborist"]["old"] == "2.0.0"
    assert compared["arborist"]["new"] == "3.0.0"
    assert "audit-service" in compared
    assert compared["audit-service"]["old"] == "2.0.0"
    assert compared["audit-service"]["new"] == "2.1.0"
    assert "fence" in compared
    assert compared["fence"]["old"] == "2.0.0"
    assert compared["fence"]["new"] == "1.0.0"
    assert "peregrine" in compared
    assert compared["peregrine"]["old"] == "2.0.0"
    assert compared["peregrine"]["new"] == "feat_something"

    # Same version and new/deleted services should not be compared
    assert "indexd" not in compared
    assert "sheepdog" not in compared
    assert "guppy" not in compared
    assert "pidgin" not in compared
    assert "ambassador" not in compared


def test_services_on_branch():
    _, new_versions = get_test_versions()
    services_on_branch = check_services_on_branch(new_versions)
    print("Services on branch:", services_on_branch)
    assert services_on_branch == ["peregrine", "sheepdog"]


def test_downgraded_services():
    compared_versions = {
        "upgraded-semver": {"old": "1.0", "new": "2.0.0"},
        "downgraded-semver": {"old": "3", "new": "2.0.0"},
        "upgraded-monthly": {"old": "2022.02", "new": "2022.03"},
        "downgraded-monthly": {"old": "2022.02", "new": "2021.03"},
        "upgraded-mixed": {"old": "2020.03", "new": "3.3.1"},
        "downgraded-mixed": {"old": "3.3.1", "new": "2020.03"},
    }
    downgraded_services = get_downgraded_services(compared_versions)
    expected = ["downgraded-semver", "downgraded-monthly"]
    assert sorted(downgraded_services) == sorted(expected)


def test_get_versions_dict():
    manifest_contents = {
        "notes": ["some note"],
        "versions": {
            "audit-service": "707767160287.dkr.ecr.us-east-1.amazonaws.com/gen3/audit-service:2023.02",
            "ambassador": "quay.io/datawire/ambassador:1.4.2",
        },
        "global": {
            "hostname": "data.commons.example",
            "useryaml_s3path": "s3://cdis-gen3-users/covid19/user.yaml",
        },
        "ssjdispatcher": {
            "job_images": {
                "indexing": "707767160287.dkr.ecr.us-east-1.amazonaws.com/gen3/indexs3client:2023.02"
            }
        },
        "jupyterhub": {
            "enabled": "yes",
            "containers": [
                {
                    "name": "Bioinfo",
                    "cpu": 1,
                    "memory": "1024M",
                    "image": "quay.io/a/b:1.9.0",
                },
                {
                    "name": "Demo",
                    "cpu": 1,
                    "memory": "1024M",
                    "image": "707767160287.dkr.ecr.us-east-1.amazonaws.com/gen3/c/d:1d33030cef16",
                },
            ],
        },
        "sower": [
            {
                "name": "my-pelican-export",
                "action": "my-export",
                "container": {
                    "name": "job-task",
                    "image": "707767160287.dkr.ecr.us-east-1.amazonaws.com/gen3/pelican-export:2023.02",
                },
            },
            {
                "name": "my-manifest-indexing",
                "action": "my-index-object-manifest",
                "container": {
                    "name": "manifest-indexing-job",
                    "image": "707767160287.dkr.ecr.us-east-1.amazonaws.com/gen3/manifest-indexing:2023.02",
                },
            },
        ],
    }
    assert get_versions_dict(manifest_contents) == {
        "audit-service": "707767160287.dkr.ecr.us-east-1.amazonaws.com/gen3/audit-service:2023.02",
        "ambassador": "quay.io/datawire/ambassador:1.4.2",
        "ssjdispatcher.job_images.indexing": "707767160287.dkr.ecr.us-east-1.amazonaws.com/gen3/indexs3client:2023.02",
        "jupyterhub.containers.image.Bioinfo": "quay.io/a/b:1.9.0",
        "jupyterhub.containers.image.Demo": "707767160287.dkr.ecr.us-east-1.amazonaws.com/gen3/c/d:1d33030cef16",
        "sower.container.image.pelican-export": "707767160287.dkr.ecr.us-east-1.amazonaws.com/gen3/pelican-export:2023.02",
        "sower.container.image.manifest-indexing": "707767160287.dkr.ecr.us-east-1.amazonaws.com/gen3/manifest-indexing:2023.02",
    }


def test_get_repo_name():
    # repo without special handling
    assert get_repo_name("fence") == "uc-cdis/fence"
    assert get_repo_name("ssjdispatcher.job_images.indexing") == "uc-cdis/indexs3client"

    # NDE repo special handling
    assert (
        get_repo_name("portal", is_nde_portal=True) == "uc-cdis/data-ecosystem-portal"
    )

    # repo that is in SERVICE_TO_REPO without a regex
    assert get_repo_name("dashboard") == "uc-cdis/gen3-statics"

    # repo that is in SERVICE_TO_REPO with a regex
    assert get_repo_name("sower.container.image.pelican-export") == "uc-cdis/pelican"
    assert (
        get_repo_name("sower.container.image.manifest-indexing") == "uc-cdis/sower-jobs"
    )
