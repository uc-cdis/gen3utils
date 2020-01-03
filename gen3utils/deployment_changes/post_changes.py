import json
import requests
import os

import gen3git

from gen3utils.manifest.manifest_validator import version_is_branch


IGNORE_SERVICE_ON_BRANCH = ["fluentd", "revproxy"]


def get_master_version(modified_file_url):
    parts = modified_file_url.split("/")
    hash_index = parts.index("raw") + 1
    parts[hash_index] = "master"
    return "/".join(parts)


def get_files(master_url, pr_url, headers):
    old_res = requests.get(master_url, headers=headers)
    new_res = requests.get(pr_url, headers=headers)
    if (
        old_res.status_code != 200 and old_res.status_code != 404
    ) or new_res.status_code != 200:
        raise Exception(
            f"Unable to get files:\n{master_url} {old_res.status_code}\n{pr_url} {new_res.status_code}"
        )

    old_file = None if old_res.status_code == 404 else old_res.json()
    new_file = new_res.json()
    return old_file, new_file


def compare_versions_blocks(old_versions_block, new_versions_block):
    """
    Returns a dict:
    {
        <service name>: { "old": <version>, "new": <version> }
    }
    """
    services = list(
        set(old_versions_block.keys()).union(set(new_versions_block.keys()))
    )
    services.sort()

    res = {}
    for service in services:
        old_version = old_versions_block.get(service).split(":")[1]
        new_version = new_versions_block.get(service).split(":")[1]
        if old_version != new_version:
            # print("{}: {} to {}".format(service, old_version, new_version))
            res[service] = {"old": old_version, "new": new_version}

    print(json.dumps(res, indent=2))
    return res


def get_deployment_changes(versions_dict, token):
    """
    Uses the gen3git utility to get the release notes between the versions for each service, and returns the deployment changes only.
    
    Args:
        versions_dict ([type]):
            {
                <service name>: { "old": <version>, "new": <version> }
            }
        token ([type]): [description]
    """

    class Gen3GitArgs(object):
        def __init__(self, repo, from_tag, to_tag):
            self.github_access_token = token
            self.repo = repo
            self.from_tag = from_tag
            self.to_tag = to_tag

    res = {}
    for service, versions in versions_dict.items():
        if (
            not version_is_branch(versions["old"])
            and not version_is_branch(versions["new"])
            and versions["old"] < versions["new"]
        ):
            args = Gen3GitArgs("uc-cdis/" + service, versions["old"], versions["new"])
            release_notes = gen3git.main(args)
            res[service] = release_notes.get("deployment changes")
    return res


def check_services_on_branch(versions_block):
    services_on_branch = []
    for service in versions_block:
        version = versions_block.get(service).split(":")[1]
        if service not in IGNORE_SERVICE_ON_BRANCH and version_is_branch(version):
            services_on_branch.append(service)
    return services_on_branch


def generate_comment(deployment_changes, services_on_branch):
    contents = ""
    if services_on_branch:
        contents += "## :warning: Services on branch\n- {}\n".format(
            "\n- ".join(services_on_branch)
        )
    if deployment_changes:
        contents += "## Deployment changes\n"
        for service, items in deployment_changes.items():
            contents += "- {}\n  - {}\n".format(service, "\n  - ".join(items))
    print(contents)
    return contents


def submit_comment(contents, headers):
    pass


def comment_deployment_changes_on_pr(repository, pull_request_number):
    token = os.environ["GITHUB_TOKEN"]
    headers = {"Authorization": "token {}".format(token)}

    repository = repository.strip("/")
    base_url = "https://api.github.com/repos/{}".format(repository)
    print("Checking pull request: {} #{}".format(repository, pull_request_number))
    pr_files_url = "{}/pulls/{}/files".format(base_url, pull_request_number)
    # pr_comments_url = "{}/issues/{}/comments".format(base_url, pull_request_number)

    # get list of files from PR
    files = requests.get(pr_files_url, headers=headers).json()
    if not isinstance(files, list):
        print(files)
        raise Exception("Unable to get PR files")

    # only keep manifest.json files
    manifest_files = [f for f in files if f["filename"].endswith("manifest.json")]
    if not manifest_files:
        print("No manifest files to check - exiting")
        return

    # for each modified manifest file, compare versions to master versions
    print("Checking manifest files")
    for file_info in files:
        print("- {}".format(file_info["filename"]))
        url = file_info["raw_url"]
        old_file, new_file = get_files(get_master_version(url), url, headers)
        old_versions_block = old_file.get("versions", {})
        new_versions_block = new_file.get("versions", {})
        deployment_changes = get_deployment_changes(
            compare_versions_blocks(old_versions_block, new_versions_block), token
        )
        contents = generate_comment(
            deployment_changes, check_services_on_branch(new_versions_block)
        )
        submit_comment(contents, headers)


# TODO print -> logging
