from cdislogging import get_logger
import json
import click
import logging
import os
import yaml
import sys

from gen3utils.deployment_changes.post_changes import comment_deployment_changes_on_pr
from gen3utils.etl.etl_validator import validate_etl_mapping as val_etl_mapping
from gen3utils.manifest.manifest_validator import validate_manifest as val_manifest

logger = get_logger("cdismanifest", None, "info")
logging.basicConfig()


CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))


@click.group()
def main():
    """Utils for Gen3 cdis-manifest management."""


@main.command()
@click.argument("manifest_files", type=str, nargs=-1, required=True)
def validate_manifest(manifest_files):
    """Validate one or more MANIFEST_FILES against a REQUIREMENTS_FILE."""

    requirements_file = os.path.join(CURRENT_DIR, "manifest", "validation_config.yaml")
    with open(requirements_file, "r") as f:
        requirements = yaml.safe_load(f.read())

    failed_validation = False
    for f_name in manifest_files:
        logger.info("Validating manifest {}".format(f_name))
        try:
            with open(f_name, "r") as f:
                cdis_manifest = json.loads(f.read())
            val_manifest(cdis_manifest, requirements)
        except AssertionError as e:
            logger.error("{}: {}".format(type(e).__name__, e))
            failed_validation = True
    if failed_validation:
        raise AssertionError("manifest validation failed. See errors in previous logs.")


@main.command()
@click.argument("etl_mapping_file", type=str, nargs=1, required=True)
@click.argument("manifest_file", type=str, nargs=1, required=True)
def validate_etl_mapping(etl_mapping_file, manifest_file):
    """Validate an ETL_MAPPING_FILE against the dictionary specified in the MANIFEST_FILE."""

    with open(manifest_file, "r") as f1:
        manifest = json.loads(f1.read())
        dictionary_url = manifest.get("global", {}).get("dictionary_url")
        assert dictionary_url, "No dictionary URL in manifest {}".format(manifest_file)
        with open(etl_mapping_file, "r") as f2:
            etl_mappings = yaml.safe_load(f2.read()).get("mappings")
            val_etl_mapping(dictionary_url, etl_mappings)


@main.command()
@click.argument("repository", type=str, nargs=1, required=True)
@click.argument("pull_request_number", type=int, nargs=1, required=True)
def post_deployment_changes(repository, pull_request_number):
    """
    Comment on a pull request with any deployment changes when updating
    manifest services. Also comment a warning if a service is on a branch.
    """

    if not "GH_TOKEN" in os.environ:
        print("Exiting: Missing GH_TOKEN")
        sys.exit(1)

    comment_deployment_changes_on_pr(repository, pull_request_number)


if __name__ == "__main__":
    main()
