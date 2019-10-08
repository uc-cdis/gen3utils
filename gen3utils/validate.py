from cdislogging import get_logger
import json
import click
import yaml
import logging

logger = get_logger("cdismanifest")
logging.basicConfig()


def validation(manifest, validation_requirement):
    """
    Runs all the validation checks against a manifest.json file.

    Args:
        manifest (str): Contents of manifest.json file.
        validation_requirement (str): Contents of validation_config.yaml file.
    """

    # remove services in avoid in validation_config which don't need validation
    hostname = manifest["global"].get("hostname")
    if hostname in validation_requirement.get("avoid", []):
        service_to_skip = validation_requirement["avoid"][hostname]
        del manifest["versions"][service_to_skip]

    for r in validation_requirement:
        if r == "block":
            ok_b = blocks_validation(manifest, validation_requirement[r])
        elif r == "versions":
            ok_v = versions_validation(manifest, validation_requirement[r])

    if not ok_b or not ok_v:
        raise AssertionError(
            "cdis-manifest validation failed. See errors in previous logs."
        )
    else:
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


def blocks_validation(block_manifest, blocks_requirements):
    """
    Validates blocks in cdis-manifest. 

    Args:
        block_manfiest: manfiest.json
        blocs_requirements: the "block" requirement under validation_config.yaml

    Return:
        ok(bool): whether the validation succeeded.
    """
    ok = True

    for service_block in blocks_requirements:
        if service_block in block_manifest["versions"]:
            # Validation for all services has requirement in validation_config.
            should_check_has = "has" in blocks_requirements[service_block]
            if "version" in blocks_requirements[service_block]:
                # If we have version requirement for a service, min or max is required.
                # min: Version in manifest is equal or greater than the verson in validation_config
                # max: Version in manifest is smaller than the verson in validation_config
                if (
                    "min" in blocks_requirements[service_block]["version"]
                    and "max" in blocks_requirements[service_block]["version"]
                ):
                    should_check_has = (
                        manifest_version(block_manifest["versions"], service_block)
                        >= blocks_requirements[service_block]["version"]["min"]
                        and manifest_version(block_manifest["versions"], service_block)
                        < blocks_requirements[service_block]["version"]["max"]
                    )
                elif "min" in blocks_requirements[service_block]["version"]:
                    should_check_has = (
                        manifest_version(block_manifest["versions"], service_block)
                        >= blocks_requirements[service_block]["version"]["min"]
                    )
                elif "max" in blocks_requirements[service_block]["version"]:
                    should_check_has = (
                        manifest_version(block_manifest["versions"], service_block)
                        < blocks_requirements[service_block]["version"]["max"]
                    )

            if should_check_has:
                # Validation to check if a service has a specific key in its block in cdis-manfiest
                error_msg = "{} is missing in {} block or {} block is missing".format(
                    blocks_requirements[service_block]["has"],
                    service_block,
                    service_block,
                )

                ok = (
                    assert_and_log(
                        service_block in block_manifest
                        and blocks_requirements[service_block]["has"]
                        in block_manifest[service_block],
                        error_msg,
                    )
                    and ok
                )

            if blocks_requirements[service_block] == "true":
                # Validation to check if a block exists in cdis-manifest
                ok = (
                    assert_and_log(
                        service_block in block_manifest,
                        service_block + " block is missing in cdis-manifest",
                    )
                    and ok
                )
    return ok


def manifest_version(manifest_versions, service):
    """
    Get the service version from cdis-manifest
        Arg: 
            service:microservice name
            manifest_versions: the versions block from manifest.json
        Return:
            microservice version
    """
    for manifest_version in manifest_versions:
        if manifest_version == service:
            # if this fails, make sure you check the service is in the manifest before
            # calling manifest_version()! it should never happen
            service_line = manifest_versions[service]
            service_version = service_line.split(":")[1]
            if "_" in service_version or service_version == "master":
                logger.warning(service + " is on branch or master, we can't validate")
            return service_version


def versions_validation(manifest, versions_requirements):
    """
    Validates versions in cdis-manifest 

    Arg:
        manifest: manfiest.json
        versions_requirements: the "versions" requirement under validation_config.yaml

    Return:
        ok(bool): whether the validation succeeded.
    """
    ok = True

    for versions_requirement in versions_requirements:
        requirement_key_list = list(versions_requirement.keys())
        print('!!!!requirement_key_list' + requirement_key_list)
        requirement_key = requirement_key_list[0]
        if requirement_key in manifest["versions"] and "_" not in manifest_version(
            manifest["versions"], requirement_key
        ):
            # If the first service set to * under validation_config versions, other services should be in the manifest
            # The second condition is ignoring branch on sevice. WHICH IS NOT GOO. Added a warning in the log
            if versions_requirement[requirement_key] == "*":
                for required_service in requirement_key_list[1:]:
                    ok = (
                        assert_and_log(
                            required_service in manifest["versions"],
                            required_service + " is missing in manifest.json",
                        )
                        and ok
                    )

            elif (
                "min" not in versions_requirement[requirement_key]
                and "max" not in versions_requirement[requirement_key]
                and versions_requirement[requirement_key]
                <= manifest_version(manifest["versions"], requirement_key)
            ):
                # If the first service set to a specific version in validation_config, other services should matches the version requirements
                ok = (
                    version_requirement_validation(
                        versions_requirement, requirement_key_list, manifest["versions"]
                    )
                    and ok
                )
            elif (
                "min" in versions_requirement[requirement_key]
                and "max" in versions_requirement[requirement_key]
                and versions_requirement[requirement_key]["min"]
                <= manifest_version(manifest["versions"], requirement_key)
                < versions_requirement[requirement_key]["max"]
            ):
                # if service is min_requirement <= service_version < max_requirement, other services should matches the version requirements
                ok = (
                    version_requirement_validation(
                        versions_requirement, requirement_key_list, manifest["versions"]
                    )
                    and ok
                )

    return ok


def version_requirement_validation(
    service_requirement, requirement_key_list, versions_manifest
):
    """
    Validates version matches the requirement for a specific service 

    Args:
    service_requirement: service name and its version requirement 
    requirement_key_list: list of service name which need validation 
    versions_manfiest: versions block from manifest

    Return:
        ok(bool): whether the validation succeeded. 
    """
    ok = True

    for required_service in requirement_key_list[1:]:
        if (
            "min" not in service_requirement[required_service]
            and "max" not in service_requirement[required_service]
        ):
            ok = (
                assert_and_log(
                    service_requirement[required_service]
                    <= manifest_version(versions_manifest, required_service),
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
                    service_requirement[required_service]["min"]
                    <= manifest_version(versions_manifest, required_service)
                    < service_requirement[required_service]["max"],
                    required_service + " version is not as expected in manifest",
                )
                and ok
            )
    return ok
