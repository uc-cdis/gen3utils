import json
import requests
import os

from cdislogging import get_logger
import gen3git

from gen3utils.manifest.manifest_validator import version_is_branch


logger = get_logger("comment-deployment-changes", log_level="info")


# whitelist of services to ignore when checking if services are on a branch
IGNORE_SERVICE_ON_BRANCH = ["revproxy", "jupyterhub"]


def comment_deployment_changes_on_pr(repository, pull_request_number):
    """
    Gets the deployments changes for the specified pull request and write them in a comment, along with a warning if any service is on a branch.

    Args:
        repository (str): "<user>/<repo>"
        pull_request_number (str)
    """
    token = os.environ["GITHUB_TOKEN"]
    headers = {"Authorization": "token {}".format(token)}

    repository = repository.strip("/")
    base_url = "https://api.github.com/repos/{}".format(repository)
    logger.info("Checking pull request: {} #{}".format(repository, pull_request_number))
    pr_files_url = "{}/pulls/{}/files".format(base_url, pull_request_number)
    pr_comments_url = "{}/issues/{}/comments".format(base_url, pull_request_number)

    # get list of files from PR
    files = requests.get(pr_files_url, headers=headers).json()
    if not isinstance(files, list):
        logger.error(files)
        raise Exception("Unable to get PR files")

    # only keep manifest.json files
    manifest_files = [f for f in files if f["filename"].endswith("manifest.json")]
    if not manifest_files:
        logger.info("No manifest files to check - exiting")
        return

    # for each modified manifest file, compare versions to master versions
    logger.info("Checking manifest files")
    full_comment = ""
    for file_info in manifest_files:
        logger.info("- {}".format(file_info["filename"]))
        url = file_info["raw_url"]
        old_file, new_file = get_files(get_master_url(url), url, headers)
        new_versions_block = new_file.get("versions", {})
        if old_file:
            old_versions_block = old_file.get("versions", {})
            deployment_changes = get_deployment_changes(
                compare_versions_blocks(old_versions_block, new_versions_block), token
            )
        else:
            # if this is a new file, there's nothing to compare
            deployment_changes = {}
        contents = generate_comment(
            deployment_changes, check_services_on_branch(new_versions_block)
        )
        if contents:
            full_comment += "# {}\n{}".format(file_info["filename"], contents)
    if full_comment:
        logger.info(full_comment)
        submit_comment(full_comment, headers, pr_comments_url)


def get_master_url(modified_file_url):
    """
    Returns the URL to the current version of the modified file, assuming
    the current version is on branch "master".

    Args:
        modified_file_url (str): URL to the modified version of the file
    """
    parts = modified_file_url.split("/")
    hash_index = parts.index("raw") + 1
    parts[hash_index] = "master"
    return "/".join(parts)


def get_files(master_url, pr_url, headers):
    """
    Returns the contents of the current version of the file and
    of the modified version of the file in a tuple.
    
    Args:
        master_url (str): URL to the current version of the file
        pr_url (str): URL to the modified version of the file
        headers (dict): Authorization heading with a token with read and
            write access to the repo
    """
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
        old_version = old_versions_block.get(service)
        new_version = new_versions_block.get(service)
        if (
            not old_version
            or not new_version
            or "quay.io/cdis" not in old_version
            or "quay.io/cdis" not in new_version
            or len(old_version.split(":")) < 2
            or len(new_version.split(":")) < 2
        ):
            # new service, or deleted service: nothing to compare.
            # non-CTDS repo: no deployment changes to get.
            # version without ":" is not usable.
            continue
        old_version = old_version.split(":")[1]
        new_version = new_version.split(":")[1]
        if old_version != new_version:
            res[service] = {"old": old_version, "new": new_version}

    logger.info("Updates: ", json.dumps(res, indent=2))
    return res


def get_deployment_changes(versions_dict, token):
    """
    Uses the gen3git utility to get the release notes between the old and new
    versions for each service, and returns the deployment changes only.
    
    Args:
        versions_dict (dict):
            {
                <service name>: { "old": <version>, "new": <version> }
            }
        token (string): token with read and write access to the repo
    """

    class Gen3GitArgs(object):
        def __init__(self, repo, from_tag, to_tag):
            self.github_access_token = token
            self.repo = repo
            self.from_tag = from_tag
            self.to_tag = to_tag

    res = {}
    for service, versions in versions_dict.items():
        # only get the deployment changes if the new version is more
        # recent than the old version. ignore services on a branch
        if (
            not version_is_branch(versions["old"])
            and not version_is_branch(versions["new"])
            and versions["old"] < versions["new"]
        ):
            repo_name = "data-portal" if service == "portal" else service
            args = Gen3GitArgs("uc-cdis/" + repo_name, versions["old"], versions["new"])
            try:
                release_notes = gen3git.main(args)
                if not release_notes:
                    raise Exception("gen3git did not return release notes")
            except:
                logger.error("Unable to get release notes with gen3git:")
                raise
            notes = release_notes.get("deployment changes")
            if notes:
                res[service] = notes
    return res


def check_services_on_branch(versions_block):
    """
    Returns the list of all services that are on a branch, except for the services listed in the IGNORE_SERVICE_ON_BRANCH whitelist.
    """
    services_on_branch = []
    for service in versions_block:
        version = versions_block.get(service)
        if "quay.io/cdis" not in version or len(version.split(":")) < 2:
            # ignore non-CTDS repos.
            # version without ":" is not usable.
            continue
        version = version.split(":")[1]
        if service not in IGNORE_SERVICE_ON_BRANCH and version_is_branch(version):
            services_on_branch.append(service)
    return services_on_branch


def generate_comment(deployment_changes, services_on_branch):
    # TODO: edit the previous comment instead of posting a new one
    contents = ""
    if services_on_branch:
        contents += "## :warning: Services on branch\n- {}\n".format(
            "\n- ".join(services_on_branch)
        )
    if deployment_changes:
        contents += "## Deployment changes\n"
        for service, items in deployment_changes.items():
            contents += "- {}\n  - {}\n".format(service, "\n  - ".join(items))
    return contents


def submit_comment(contents, headers, pr_comments_url):
    res = requests.post(pr_comments_url, json={"body": contents}, headers=headers)
    if res.status_code != 201:
        logger.error("Failed to write comment:", res.status_code, res.json())