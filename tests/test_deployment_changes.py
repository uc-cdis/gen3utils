import os

from gen3utils.deployment_changes.generate_comment import (
    compare_versions_blocks,
    check_services_on_branch,
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
