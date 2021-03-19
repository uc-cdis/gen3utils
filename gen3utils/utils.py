import os
import requests

from cdislogging import get_logger

logger = get_logger("Submit comments to PR", log_level="info")


def comment_errors_on_pr(repository, pull_request_number, file_name, errors):
    token = os.environ["GITHUB_TOKEN"]
    headers = {"Authorization": "token {}".format(token)}

    repository = repository.strip("/")
    base_url = "https://api.github.com/repos/{}".format(repository)
    logger.info("Checking pull request: {} #{}".format(repository, pull_request_number))
    pr_comments_url = "{}/issues/{}/comments".format(base_url, pull_request_number)
    contents = ""
    for error in errors:
        contents += "## {}\n".format(error)
    full_comment = "# {}\n{}".format(file_name, contents)

    submit_comment(full_comment, headers, pr_comments_url)


def submit_comment(contents, headers, pr_comments_url):
    res = requests.post(pr_comments_url, json={"body": contents}, headers=headers)
    if res.status_code != 201:
        logger.error("Failed to write comment:", res.status_code, res.json())