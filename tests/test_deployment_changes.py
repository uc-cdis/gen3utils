import os

from gen3utils.deployment_changes.generate_comment import (
    compare_versions_blocks,
    check_services_on_branch,
)


def test_compare(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake_token")
    old_versions = {
        "arborist": "quay.io/cdis/arborist:2.0.0",
        "fence": "quay.io/cdis/fence:2.0.0",
        "indexd": "quay.io/cdis/indexd:2.0.0",
        "peregrine": "quay.io/cdis/peregrine:2.0.0",
        "sheepdog": "quay.io/cdis/sheepdog:master",  # old and new on branch
        "guppy": "quay.io/cdis/pidgin:2.0.0",  # deleted service
        "revproxy": "quay.io/cdis/nginx:1.15.5-ctds",
    }
    new_versions = {
        "arborist": "quay.io/cdis/arborist:3.0.0",  # new > old
        "fence": "quay.io/cdis/fence:1.0.0",  # new < old
        "indexd": "quay.io/cdis/indexd:2.0.0",  # new == old
        "peregrine": "quay.io/cdis/peregrine:feat_something",  # new on branch
        "sheepdog": "quay.io/cdis/sheepdog:master",  # old and new on branch
        "pidgin": "quay.io/cdis/pidgin:2.0.0",  # new service
        "revproxy": "quay.io/cdis/nginx:1.15.5-ctds",  # branch to ignore
    }

    compared = compare_versions_blocks(old_versions, new_versions, True)
    print("Compared versions:", compared)

    assert "arborist" in compared
    assert compared["arborist"]["old"] == "2.0.0"
    assert compared["arborist"]["new"] == "3.0.0"
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
    assert "revproxy" not in compared

    services_on_branch = check_services_on_branch(new_versions)
    print("Services on branch:", services_on_branch)
    assert services_on_branch == ["peregrine", "sheepdog"]
