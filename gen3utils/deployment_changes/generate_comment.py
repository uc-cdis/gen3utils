"""
Comment deployment changes and breaking changes on PRs that update service versions.
Also warn about services pinned to a branch and services that are being downgraded.
"""


import json
import os
from packaging import version
import re
import requests
import sys

from cdislogging import get_logger
import gen3git

from gen3utils.manifest.manifest_validator import version_is_branch
from gen3utils.utils import submit_comment, version_is_monthly_release

logger = get_logger("comment-deployment-changes", log_level="debug")


# whitelist of services to ignore when checking tags and services on branch
# TODO: We're adding access-backend here just to unblock the gen3utils check in gitops-qa's .travis.yml
# This repo is private and there seems to be an issue with gen3utils where it is not picking up the GITHUB_TOKEN
IGNORED_SERVICES = [
    "ambassador",
    "aws-es-proxy",
    "fluentd",
    "jupyterhub",
    "nb2",
    "access-backend",
    "acronymbot",
    "cedar-wrapper",
    "kayako-wrapper",
    "frontend-framework",
]

# update this config if the service name in the manifest "versions"
# block is not the same as the repo name. services that are not
# listed here are assumed to be in repo uc-cdis/<service name>.
SERVICE_TO_REPO = {
    "awshelper": "cloud-automation",
    "dashboard": "gen3-statics",
    "portal": "data-portal",
    "revproxy": "docker-nginx",
    "spark": "gen3-spark",
    "wts": "workspace-token-service",
    "metadata": "metadata-service",
    "covid19-etl": "covid19-tools",
    "covid19-notebook-etl": "covid19-tools",
    "covid19-bayes": "covid19-tools",
    "datareplicate": "dcf-dataservice",
    "cedar-wrapper": "cedar-wrapper-service",
    "kayako-wrapper": "kayako-wrapper-service",
    "frontend-framework": "gen3-frontend-framework",
    "metadata-delete-expired-objects": "sower-jobs",
    "ssjdispatcher.job_images.indexing": "indexs3client",
    "_regex": {
        r"^sower\..*\.pelican-.*$": "pelican",
        r"^sower\..*\.(?:manifest-indexing|download-indexd-manifest|manifest-merging|metadata-manifest-ingestion|get-dbgap-metadata|batch-export|metadata-delete-expired-objects)$": "sower-jobs",
    },
}


def comment_deployment_changes_on_pr(repository, pull_request_number):
    """
    Gets the deployments changes for the specified pull request and write them in a comment, along with a warning if any service is on a branch.

    Args:
        repository (str): "<user>/<repo>"
        pull_request_number (str)
    """
    if "GITHUB_TOKEN" in os.environ:
        token = os.environ["GITHUB_TOKEN"]
        headers = {"Authorization": "token {}".format(token)}
    else:
        logger.warning(
            "Missing GITHUB_TOKEN: NOT commenting deployment changes on pull request. Continuing; but might fail later if the PR is not accessible."
        )
        token = None
        headers = {}

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
        new_versions_block = get_versions_dict(new_file)
        new_portal_type = get_image_name(new_versions_block.get("portal", ""))

        for service_name in IGNORED_SERVICES:
            new_versions_block.pop(service_name, None)

        if old_file:
            old_versions_block = get_versions_dict(old_file)
            for service_name in IGNORED_SERVICES:
                old_versions_block.pop(service_name, None)

            old_portal_type = get_image_name(new_versions_block.get("portal", ""))
            # we only compare portal versions from the same repo
            compared_versions = compare_versions_blocks(
                old_versions_block,
                new_versions_block,
                new_portal_type == old_portal_type,
            )
            deployment_changes, breaking_changes = get_important_changes(
                compared_versions, token, new_portal_type
            )
            downgraded_services = get_downgraded_services(compared_versions)
        else:
            # if this is a new file, there's nothing to compare
            deployment_changes = {}
            breaking_changes = {}
            downgraded_services = {}
        contents = generate_comment(
            deployment_changes,
            breaking_changes,
            check_services_on_branch(new_versions_block),
            downgraded_services,
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


def get_versions_dict(manifest):
    """
    Returns:
    dict { <image name>: <image url> }

    Example:
    { "fence": "quay.io/cdis/fence:1.0.0",  "ssjdispatcher.job_images.indexing": "quay.io/cdis/ssjdispatcher:2.0.0" }

    TODO: check the `manifests/hatchery/hatchery.json` file or `manifest.json->hatchery` section
    """
    versions = manifest.get("versions", {})
    for ssj_name, ssj_image in (
        manifest.get("ssjdispatcher", {}).get("job_images", {}).items()
    ):
        versions[f"ssjdispatcher.job_images.{ssj_name}"] = ssj_image
    for sower_job in manifest.get("sower", []):
        container = sower_job.get("container", {})
        image = container.get("image")
        if image:
            name = image.split("/")[-1].split(":")[0]
            versions[f"sower.container.image.{name}"] = image
    for jupyter_container in manifest.get("jupyterhub", {}).get("containers", []):
        image = jupyter_container.get("image")
        if image:
            versions[
                f"jupyterhub.containers.image.{jupyter_container.get('name')}"
            ] = image
    return versions


def compare_versions_blocks(old_versions_block, new_versions_block, check_portal):
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
        if service == "portal" and not check_portal:
            # skip if portal versions are not from the same repo
            continue

        old_version = old_versions_block.get(service)
        new_version = new_versions_block.get(service)
        if (
            not old_version
            or not new_version
            or (
                "quay.io/cdis" not in old_version
                and "dkr.ecr.us-east-1.amazonaws.com" not in old_version
            )
            or (
                "quay.io/cdis" not in new_version
                and "dkr.ecr.us-east-1.amazonaws.com" not in new_version
            )
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

    logger.info("Updates: {}".format(json.dumps(res, indent=2)))
    return res


def get_important_changes(versions_dict, token, portal_type):
    """
    Uses the gen3git utility to get the release notes between the old and new
    versions for each service, and returns the deployment changes and breaking
    changes only.

    Args:
        versions_dict (dict):
            {
                <service name>: { "old": <version>, "new": <version> }
            }
        token (string): token with read and write access to the repo

    Return:
        (dict, dict) tuple:
            (
                {<service>: [<deployment change 1>, <deployment change 2>]},
                {<service>: [<breaking change 1>, <breaking change 2>]}
            )
    """

    class Gen3GitArgs(object):
        def __init__(self, repo, from_tag, to_tag):
            self.github_access_token = token
            self.repo = repo
            self.from_tag = from_tag
            self.to_tag = to_tag

    deployment_changes = {}
    breaking_changes = {}
    for service, versions in versions_dict.items():
        # only get the deployment changes if the new version is more
        # recent than the old version. ignore services on a branch
        if not version_is_branch(
            versions["old"], release_tag_are_branches=False
        ) and not version_is_branch(versions["new"], release_tag_are_branches=False):
            repo_name = get_repo_name(service, portal_type)
            logger.debug(f"Mapped service/image name '{service}' to repo '{repo_name}'")
            args = Gen3GitArgs(repo_name, versions["old"], versions["new"])
            try:
                release_notes = gen3git.main(args)
                if not release_notes:
                    raise Exception("gen3git did not return release notes")
            except Exception:
                logger.error(
                    "While checking service '{}', repo '{}', unable to get release notes with gen3git:".format(
                        service, repo_name
                    )
                )
                raise
            notes = release_notes.get("deployment changes")
            if notes:
                deployment_changes[service] = update_pr_links(repo_name, notes)
            notes = release_notes.get("breaking changes")
            if notes:
                breaking_changes[service] = update_pr_links(repo_name, notes)
    return deployment_changes, breaking_changes


def get_image_name(version):
    """
    input: "707767160287.dkr.ecr.us-east-1.amazonaws.com/gen3/dataguids:1.0.2"
    output: "dataguids"
    """
    image_name = version.split(":")[0]
    image_name = image_name.split("/")[-1]
    return image_name


def get_repo_name(service, portal_type="data-portal"):
    # by default, assume the code lives in repo uc-cdis/<service name>
    repo_name = SERVICE_TO_REPO.get(service, service)

    # try to match the service name to one of the configured regex
    if service not in SERVICE_TO_REPO:
        for reg, matched_repo in SERVICE_TO_REPO["_regex"].items():
            if re.match(reg, service):
                repo_name = matched_repo
                break

    # repo names special cases
    if service == "portal":
        if portal_type == "data-ecosystem-portal":
            repo_name = "data-ecosystem-portal"
        elif portal_type == "dataguids":
            repo_name = "dataguids.org"

    return "uc-cdis/" + repo_name


def get_downgraded_services(compared_versions):
    """
    Return: list of downgraded services names
    """
    downgraded_services = set()
    for service, versions in compared_versions.items():
        if version_is_branch(
            versions["old"], release_tag_are_branches=False
        ) or version_is_branch(versions["new"], release_tag_are_branches=False):
            # we can't compare branches
            continue
        old_is_monthly = version_is_monthly_release(versions["old"])
        new_is_monthly = version_is_monthly_release(versions["new"])
        if old_is_monthly != new_is_monthly:
            # one is a monthly release, the other is not: we can't compare
            continue
        elif version.parse(versions["new"]) < version.parse(versions["old"]):
            downgraded_services.add(service)
    return downgraded_services


def check_services_on_branch(versions_block):
    """
    Returns the list of all services that are on a branch.
    """
    services_on_branch = []
    for service in versions_block:
        version = versions_block.get(service)
        if (
            "quay.io/cdis" not in version
            and "dkr.ecr.us-east-1.amazonaws.com" not in version
        ) or len(version.split(":")) < 2:
            # ignore non-CTDS repos.
            # version without ":" is not usable.
            continue
        version = version.split(":")[1]
        if version_is_branch(version, release_tag_are_branches=False):
            services_on_branch.append(service)
    return services_on_branch


def update_pr_links(repo_name, notes_list):
    """
    Replace the internal repo PR link with the external repo PR link
    in each release note.
    """
    result = []
    matcher = re.compile(r".*\(#(?P<pr_number>[0-9]+)\)$")
    # e.g. gets the PR number ("12") from "some description (#12)"
    for note in notes_list:
        match = matcher.match(note)
        if match:
            internal_pr_number = "#{}".format(match.groupdict()["pr_number"])
            external_pr_number = "{}{}".format(repo_name, internal_pr_number)
            result.append(note.replace(internal_pr_number, external_pr_number))
        else:
            result.append(note)
    return result


def generate_comment(
    deployment_changes, breaking_changes, services_on_branch, downgraded_services
):
    # TODO: edit the previous comment instead of posting a new one
    contents = ""
    if services_on_branch:
        contents += "## :warning: Services on branch\n- {}\n".format(
            "\n- ".join(services_on_branch)
        )
    if downgraded_services:
        contents += "## :warning: Services are being downgraded\n- {}\n".format(
            "\n- ".join(downgraded_services)
        )
    if deployment_changes:
        contents += "## Deployment changes\n"
        for service, items in deployment_changes.items():
            contents += "- {}\n  - {}\n".format(service, "\n  - ".join(items))
    if breaking_changes:
        contents += "## Breaking changes\n"
        for service, items in breaking_changes.items():
            contents += "- {}\n  - {}\n".format(service, "\n  - ".join(items))
    return contents
