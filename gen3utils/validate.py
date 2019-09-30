from cdislogging import get_logger
import json
import click
import yaml
import logging

logger = get_logger("cdismanifest")
logging.basicConfig()


def validation(manifest, validation_requirement):
    #remove services in avoid in validation_config which don't need validation 
    for commons in validation_requirement['avoid']:
        if manifest["global"].get("hostname") == commons:
            remove_service = validation_requirement['avoid'][commons]
            del manifest['versions'][remove_service]
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
        Arg:
            block_manfiest: manfiest.json
            blocs_requirements: the "block" requirement under validation_config.yaml
    """
    ok = True
    # logger.info('Validating block requirements')

    for service_block in blocks_requirements:
        if service_block in block_manifest["versions"]:
            # Validation for all services has requirement in validation_config.
            should_check_has = "has" in blocks_requirements[service_block]
            if "version" in blocks_requirements[service_block]:
                # Version in manifest is equal or greater than verson in validation_config
                if (
                    "min" in blocks_requirements[service_block]["version"]
                    and "max" in blocks_requirements[service_block]["version"]
                ):
                    should_check_has = (
                        manifest_version(block_manifest["versions"], service_block)
                        >= blocks_requirements[service_block]["version"]["min"]
                        and manifest_version(block_manifest["versions"], service_block)
                        <= blocks_requirements[service_block]["version"]["max"]
                    )
                elif "min" in blocks_requirements[service_block]["version"]:
                    should_check_has = (
                        manifest_version(block_manifest["versions"], service_block)
                        >= blocks_requirements[service_block]["version"]["min"]
                    )
                elif "max" in blocks_requirements[service_block]["version"]:
                    should_check_has = (
                        manifest_version(block_manifest["versions"], service_block)
                        <= blocks_requirements[service_block]["version"]["max"]
                    )

            if should_check_has:
                # Validation to check if a service has a specific key in its block in cdis-manfiest
                # TODO better error msg
                error_msg = (
                    blocks_requirements[service_block]["has"]
                    + " is missing in "
                    + service_block
                    + " block or "
                    + service_block
                    + " block is missing"
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
                ok = (
                    assert_and_log(
                        service_block in block_manifest,
                        service_block + " is missing in cdis-manifest",
                    )
                    and ok
                )
    return ok


def manifest_version(manifest_versions, services):
    """
        Arg: 
            services:microservice name
            manifest_versions: the versions block from manifest.json
        Return:
            microservice version
    """
    for manifest_version in manifest_versions:
        if manifest_version == services:
            # if this fails, make sure you check the service is in the manifest before
            # calling manifest_version()! it should never happen
            microservice_version = manifest_versions.get(services).split(":")[1]
            if "_" in microservice_version:
                logger.warning(services + " is on branch")
            return microservice_version


def versions_validation(versions_manifest, versions_requirements):
    """
        Arg:
            versions_manifest: manfiest.json
            versions_requirements: the "versions" requirement under validation_config.yaml
    """
    ok = True

    for versions_requirement in versions_requirements:
        requirement_key_list = list(versions_requirement.keys())
        requirement_key = requirement_key_list[0]
        if requirement_key in versions_manifest[
            "versions"
        ] and "_" not in manifest_version(
            versions_manifest["versions"], requirement_key
        ):
            """If the first service set to * under validation_config versions, 
            other services under it should be present in the manifest """
            # The second condition is ignoring branch on sevice. WHICH IS NOT GOO. Added a warning in the log
            if (
                versions_requirement[requirement_key] == "*"
                and versions_manifest["global"].get("hostname")
                != "qa-mickey.planx-pla.net"
            ):
                for required_service in requirement_key_list[1:]:
                    ok = (
                        assert_and_log(
                            required_service in versions_manifest["versions"],
                            required_service + " is missing in manifest.json",
                        )
                        and ok
                    )

            # If the first service set to a specific version in config,others services should matches the required version.
            elif versions_requirement[requirement_key] <= manifest_version(
                versions_manifest["versions"], requirement_key
            ):
                for required_service in requirement_key_list[1:]:
                    ok = (
                        assert_and_log(
                            versions_requirement[required_service]
                            <= manifest_version(
                                versions_manifest["versions"], required_service
                            ),
                            required_service
                            + " version is not as expected in manifest",
                        )
                        and ok
                    )
    return ok