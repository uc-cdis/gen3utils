import click
import json
import re
import yaml

from cdislogging import get_logger


logger = get_logger("validate-manifest", log_level="info")


def validate_manifest(manifest, validation_requirement):
    """
    Runs all the validation checks against a manifest.json file.

    Args:
        manifest (dict): Contents of manifest.json file.
        validation_requirement (dict): Contents of validation_config.yaml file.
    """

    # remove services in avoid in validation_config which don't need validation
    hostname = manifest["global"].get("hostname")
    if hostname in validation_requirement.get("avoid", []):
        services_to_skip = validation_requirement["avoid"][hostname]
        for s in services_to_skip:
            del manifest["versions"][s]

    ok = True
    if "block" in validation_requirement:
        ok = validate_manifest_block(manifest, validation_requirement["block"]) and ok
    if "versions" in validation_requirement:
        ok = (
            versions_validation(
                manifest.get("versions"), validation_requirement["versions"]
            )
            and ok
        )

    if not ok:
        raise AssertionError(
            "cdis-manifest validation failed. See errors in previous logs."
        )
    logger.info("OK")


def assert_and_log(assertion_success, error_message):
    """
    If an assertion fails, logs the provided error message and updates
    the global variable "failed_validation" for future use.
    
    Args:
        assertion_success (bool): result of an assertion.
        error_message (str): message to display if the assertion failed.

    Return:
        assertion_success(bool): result of the assertion.
    """
    if not assertion_success:
        logger.error(error_message)
    return assertion_success


def validate_manifest_block(manifest, blocks_requirements):
    """
    Validates blocks in cdis-manifest. 

    Args:
        manifest (dict): Contents of manifest.json file.
        blocks_requirements (dict): the "block" requirement under
            validation_config.yaml. The keys of the dict are the service names
            and the values are the requirements for the block associated to
            the service.

    Return:
        ok(bool): whether the validation succeeded.
    """
    ok = True

    for service_name, block in blocks_requirements.items():
        if service_name in manifest["versions"]:
            # Validation for all services has requirement in validation_config.
            should_check_has = "has" in block
            block_requirement_version = manifest_version(
                manifest["versions"], service_name
            )
            if "version" in block and not version_is_branch(block_requirement_version):
                # If we have version requirement for a service, min or max is required.
                # We are not validating branch or master branch
                # min: Version in manifest is equal or greater than the verson in validation_config
                # max: Version in manifest is smaller than the verson in validation_config

                if "min" in block["version"] and "max" in block["version"]:
                    should_check_has = (
                        block_requirement_version >= block["version"]["min"]
                        and block_requirement_version < block["version"]["max"]
                    )
                elif "min" in block["version"]:
                    should_check_has = (
                        block_requirement_version >= block["version"]["min"]
                    )
                elif "max" in block["version"]:
                    should_check_has = (
                        block_requirement_version < block["version"]["max"]
                    )

            if should_check_has:
                # Validation to check if a service has a specific key in its block in cdis-manfiest
                error_msg = "{} is missing in {} block or {} block is missing".format(
                    block["has"], service_name, service_name
                )

                ok = (
                    assert_and_log(
                        service_name in manifest
                        and block["has"] in manifest[service_name]
                        or service_name not in manifest
                        and block.get("optional") == "true",
                        error_msg,
                    )
                    and ok
                )

            if block == "true":
                # Validation to check if a block exists in cdis-manifest
                ok = (
                    assert_and_log(
                        service_name in manifest,
                        service_name + " block is missing in cdis-manifest",
                    )
                    and ok
                )
    return ok


def manifest_version(manifest_versions, service):
    """
    Get the service version from cdis-manifest
        Arg: 
            service: microservice name
            manifest_versions: the versions block from manifest.json
        Return:
            microservice version (None if service not in manifest)
    """
    for manifest_version in manifest_versions:
        if manifest_version == service:
            # if this fails, make sure you check the service is in the manifest before
            # calling manifest_version()! it should never happen
            service_line = manifest_versions[service]
            service_version = service_line.split(":")[1]
            if version_is_branch(service_version):
                logger.warning("  {} is on a branch: not validating".format(service))
            return service_version


def version_is_branch(version):
    """
    Args:
        version (string)

    Returns:
        bool: True if version only contains digits and dots
    """
    reg = re.compile("^[0-9]+(.[0-9]+)*$")
    return not bool(reg.match(version))


def versions_validation(manifest_versions, versions_requirements):
    """
    Validates versions in cdis-manifest 

    Arg:
        manifest_versions: manifest.json "versions" section
        versions_requirements: the "versions" requirement under validation_config.yaml

    Return:
        ok(bool): whether the validation succeeded.
    """
    ok = True

    for versions_requirement in versions_requirements:

        requirement_list = versions_requirement["needs"]
        requirement_key_list = list(requirement_list.keys())
        requirement_key = list(versions_requirement)[0]
        requirement_version = manifest_version(manifest_versions, requirement_key)

        if requirement_key in manifest_versions and not version_is_branch(
            requirement_version
        ):
            # If the first service set to * under validation_config versions, other services should be in the manifest
            # The second condition is ignoring branch on sevice. WHICH IS NOT GOO. Added a warning in the log
            if versions_requirement[requirement_key] == "*":
                for required_service in requirement_key_list:
                    ok = (
                        assert_and_log(
                            required_service in manifest_versions,
                            required_service + " is missing in manifest.json",
                        )
                        and ok
                    )

            elif (
                "min" not in versions_requirement[requirement_key]
                and "max" not in versions_requirement[requirement_key]
                and versions_requirement[requirement_key] <= requirement_version
            ):
                # If the first service set to a specific version in validation_config, other services should matches the version requirements
                ok = (
                    version_requirement_validation(
                        requirement_list,
                        requirement_key_list,
                        manifest_versions,
                        "{} {}".format(requirement_key, requirement_version),
                    )
                    and ok
                )
            elif (
                "min" in versions_requirement[requirement_key]
                and "max" in versions_requirement[requirement_key]
                and versions_requirement[requirement_key]["min"]
                <= requirement_version
                < versions_requirement[requirement_key]["max"]
            ):
                # if service is min_requirement <= service_version < max_requirement, other services should matches the version requirements
                ok = (
                    version_requirement_validation(
                        requirement_list,
                        requirement_key_list,
                        manifest_versions,
                        "{} {}".format(requirement_key, requirement_version),
                    )
                    and ok
                )

    return ok


def version_requirement_validation(
    service_requirement, requirement_key_list, versions_manifest, current_validation
):
    """
    Validates version matches the requirement for a specific service 

    Args:
    service_requirement: service name and its version requirement 
    requirement_key_list: list of service name which need validation 
    versions_manfiest: versions block from manifest
    current_validation (str): service name and version that are currently being validated

    Return:
        ok(bool): whether the validation succeeded. 
    """
    ok = True

    for required_service in requirement_key_list:

        service_version = manifest_version(versions_manifest, required_service)

        if not service_version:
            logger.error(
                'Service "{}" not in manifest but required to validate "{}" with "{}"'.format(
                    required_service, current_validation, service_requirement
                )
            )
            ok = False
            continue

        if (
            "min" not in service_requirement[required_service]
            and "max" not in service_requirement[required_service]
        ):
            ok = (
                assert_and_log(
                    service_requirement[required_service] <= service_version,
                    required_service + " version is not as expected in manifest",
                )
                and ok
            )
        elif (
            "min" in service_requirement[required_service]
            and "max" in service_requirement[required_service]
        ):
            ok = (
                assert_and_log(
                    service_requirement[required_service]["min"] <= service_version
                    and service_version < service_requirement[required_service]["max"],
                    required_service + " version is not as expected in manifest",
                )
                and ok
            )
    return ok