from cdislogging import get_logger
import json
import click
import os
import yaml
import logging

from gen3utils.validate import validate_manifest

logger = get_logger("cdismanifest", None, "info")
logging.basicConfig()


CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))


@click.group()
def main():
    """Utils for Gen3 cdis-manifest management."""


@main.command()
@click.argument("manifest_files", type=str, nargs=-1, required=True)  #
# @click.argument("requirements_file", type=str, required=True)
def validate(manifest_files):
    """Validate one or more MANIFEST_FILES against a REQUIREMENTS_FILE."""

    requirements_file = os.path.join(CURRENT_DIR, "validation_config.yaml")
    with open(requirements_file, "r") as f:
        requirements = yaml.safe_load(f.read())

    failed_validation = False
    for f_name in manifest_files:
        logger.info("Validating manifest {}".format(f_name))
        try:
            with open(f_name, "r") as f:
                cdis_manifest = json.loads(f.read())
            validate_manifest(cdis_manifest, requirements)
        except AssertionError as e:
            logger.error("{}: {}".format(type(e).__name__, e))
            failed_validation = True
    if failed_validation:
        raise AssertionError("manifest validation failed. See errors in previous logs.")


if __name__ == "__main__":
    main()
