from packaging import version
import re
from cdislogging import get_logger
from gen3utils.assertion import assert_and_log


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
            block_requirement_version = get_manifest_version(
                manifest["versions"], service_name
            )
            is_branch = version_is_branch(block_requirement_version)
            should_check_has = "has" in block and not is_branch
            if "version" in block and not is_branch:
                # If we have version requirement for a service, min or max is required.
                # We are not validating branch or master branch
                # min: Version in manifest is equal or greater than the verson in validation_config
                # max: Version in manifest is smaller than the verson in validation_config

                min_version = block["version"].get("min")
                max_version = block["version"].get("max")
                if min_version:
                    min_version = version.parse(min_version)
                if max_version:
                    max_version = version.parse(max_version)

                if min_version and max_version:
                    should_check_has = (
                        block_requirement_version >= min_version
                        and block_requirement_version < max_version
                    )
                elif min_version:
                    should_check_has = block_requirement_version >= min_version
                elif max_version:
                    should_check_has = block_requirement_version < max_version

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


def get_manifest_version(manifest_versions, service):
    """
    Get the service version from cdis-manifest
        Arg: 
            service: microservice name
            manifest_versions: the versions block from manifest.json
        Return:
            parsed microservice version (or None if service not in manifest)
    """
    for manifest_version in manifest_versions:
        if manifest_version == service:
            # if this fails, make sure you check the service is in the manifest before
            # calling get_manifest_version()! it should never happen
            service_line = manifest_versions[service]
            service_version = service_line.split(":")[1]
            if version_is_branch(service_version):
                logger.warning(
                    "{} is on a branch ({}): not validating".format(
                        service, service_version
                    )
                )
                return service_version
            try:
                return version.parse(service_version)
            except:
                return service_version


def version_is_branch(version, release_tag_are_branches=True):
    """
    Args:
        version (string)
        release_tag_are_branches (bool): whether release tags in format
            <dddd.dd> should be considered branches or not.
            - For manifest validation, we want to skip validation for release
            tags because the semantic versions comparison would not work.
            - For checking deployment changes, we do want release tags to be
            included like other tags.

    Returns:
        bool: True if version only contains digits and dots BUT is
            not a release tag in format <dddd.dd>
    """
    # check if it looks like semantic versioning
    reg = re.compile("^[0-9]+[.[0-9]+]*$")
    is_branch = not bool(reg.match(str(version)))

    # check if it's a release tag
    if not is_branch and release_tag_are_branches:
        reg = re.compile("^[0-9]{4}.[0-9]{2}$")
        is_branch = bool(reg.match(str(version)))

    return is_branch


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
        actual_version = get_manifest_version(manifest_versions, requirement_key)

        if requirement_key in manifest_versions and not version_is_branch(
            actual_version
        ):

            required_version = versions_requirement[requirement_key]

            # If the first service set to * under validation_config versions, other services should be in the manifest
            # The second condition is ignoring branch on sevice. WHICH IS NOT GOO. Added a warning in the log
            if required_version == "*":
                for required_service in requirement_key_list:
                    ok = (
                        assert_and_log(
                            required_service in manifest_versions,
                            required_service + " is missing in manifest.json",
                        )
                        and ok
                    )

            elif (
                "min" not in required_version
                and "max" not in required_version
                and version.parse(required_version) <= actual_version
            ):
                # If the first service set to a specific version in validation_config, other services should matches the version requirements
                ok = (
                    version_requirement_validation(
                        requirement_list,
                        requirement_key_list,
                        manifest_versions,
                        "{} {}".format(requirement_key, actual_version),
                    )
                    and ok
                )
            elif (
                "min" in required_version
                and "max" in required_version
                and version.parse(required_version["min"]) <= actual_version
                and actual_version < version.parse(required_version["max"])
            ):
                # if service is min_requirement <= service_version < max_requirement, other services should matches the version requirements
                ok = (
                    version_requirement_validation(
                        requirement_list,
                        requirement_key_list,
                        manifest_versions,
                        "{} {}".format(requirement_key, actual_version),
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

        actual_version = get_manifest_version(versions_manifest, required_service)

        if not actual_version:
            logger.error(
                'Service "{}" not in manifest but required to validate "{}" with "{}"'.format(
                    required_service, current_validation, service_requirement
                )
            )
            ok = False
            continue

        if version_is_branch(actual_version):
            # ignoring service on branch - user was already informed of this
            # by the log in `manifest_version()`
            continue

        if (
            "min" not in service_requirement[required_service]
            and "max" not in service_requirement[required_service]
        ):
            ok = (
                assert_and_log(
                    version.parse(service_requirement[required_service])
                    <= actual_version,
                    'Service "{}" version "{}" does not respect requirement "{}" for "{}"'.format(
                        required_service,
                        actual_version,
                        service_requirement,
                        current_validation,
                    ),
                )
                and ok
            )
        elif (
            "min" in service_requirement[required_service]
            and "max" in service_requirement[required_service]
        ):
            ok = (
                assert_and_log(
                    version.parse(service_requirement[required_service]["min"])
                    <= actual_version
                    and actual_version
                    < version.parse(service_requirement[required_service]["max"]),
                    'Service "{}" version "{}" does not respect requirement "{}" for "{}"'.format(
                        required_service,
                        actual_version,
                        service_requirement,
                        current_validation,
                    ),
                )
                and ok
            )
    return ok
