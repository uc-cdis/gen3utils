import re
import yaml
import json
from cdislogging import get_logger

from gen3utils.assertion import assert_and_log
from gen3utils.etl.dd_utils import init_dictionary
from gen3utils.errors import FieldSyntaxError, FieldError


logger = get_logger("validate-gitops", log_level="info")


def val_gitops(data_dictionary, etl_mapping, gitops):
    with open(gitops, "r") as f:
        gitops_config = json.loads(f.read())
    ok = validate_gitops_syntax(gitops_config)
    if not ok:
        raise AssertionError("gitops validation failed. See errors in previous logs.")

    ok = validate_against_dictionary(gitops_config, data_dictionary)
    if not ok:
        raise AssertionError("gitops validation failed. See errors in previous logs.")
    recorded_errors = validate_against_etl(gitops_config, etl_mapping)
    return recorded_errors


def validate_gitops_syntax(gitops):
    """
    Validates the syntax of gitops.json by checking for required fields
    Args:
        gitops (dict): gitops.json config

    Returns:
        Error: Returns the error if it exists, else returns None.

    TODO
    Currently only checks syntax needed for etl mapping and dictionary validation.
    """
    graphql = gitops.get("graphql")
    ok = assert_and_log(graphql, FieldSyntaxError("graphql"))

    if graphql:
        boardcounts = graphql.get("boardCounts")
        ok = ok and assert_and_log(boardcounts, FieldSyntaxError("graphql.boardCounts"))
        if boardcounts:
            for item in boardcounts:
                checks = ["graphql", "name", "plural"]
                ok = check_required_fields("graphql.boardCounts", checks, item, ok)

        chartcounts = graphql.get("chartCounts")
        ok = ok and assert_and_log(chartcounts, FieldSyntaxError("graphql.chartCounts"))

    components = gitops.get("components")
    ok = ok and assert_and_log(components, FieldSyntaxError("components"))
    if components:
        index = components.get("index")
        ok = ok and assert_and_log(index, FieldSyntaxError("components.index"))

        homepage = index.get("homepageChartNodes")
        ok = ok and assert_and_log(
            index, FieldSyntaxError("components.homepageChartNodes")
        )
        if homepage:
            for item in homepage:
                checks = ["node", "name"]
                ok = check_required_fields(
                    "components.index.homepage", checks, item, ok
                )

    explorerconfig = gitops.get("explorerConfig")
    configs = []
    if not explorerconfig:
        dataConfig = gitops.get("dataExplorerConfig")
        fileConfig = gitops.get("fileExplorerConfig")
        ok = ok and assert_and_log(dataConfig, FieldSyntaxError("(data)explorerConfig"))
        if dataConfig:
            configs.append(dataConfig)
        if fileConfig:
            configs.append(fileConfig)
    else:
        configs = explorerconfig

    for exp_config in configs:
        filters = exp_config.get("filters")
        ok = ok and assert_and_log(filters, FieldSyntaxError("explorerConfig.filters"))
        if filters:
            tabs = filters.get("tabs", [])
            ok = ok and assert_and_log(
                tabs, FieldSyntaxError("explorerConfig.filters.tabs")
            )
            for tab in tabs:
                checks = ["title", "fields"]
                ok = check_required_fields(
                    "explorerConfig.filters.tab", checks, tab, ok
                )

        guppy = exp_config.get("guppyConfig")
        ok = ok and assert_and_log(
            guppy, FieldSyntaxError("explorerConfig.guppyConfig")
        )
        if guppy:
            ok = ok and assert_and_log(
                guppy.get("dataType"),
                FieldSyntaxError("explorerConfig.guppyConfig.dataType"),
            )
            manifest_mapping = guppy.get("manifestMapping")
            ok = ok and assert_and_log(
                manifest_mapping,
                FieldSyntaxError("explorerConfig.guppyConfig.manifestMapping"),
            )

        buttons = exp_config.get("buttons", [])
        ok = ok and assert_and_log(buttons, FieldSyntaxError("explorerConfig.buttons"))
        val_mapping = False
        for button in buttons:
            if button.get("enabled") and button.get("type") == "manifest":
                val_mapping = True
        if manifest_mapping and val_mapping:
            checks = [
                "resourceIndexType",
                "resourceIdField",
                "referenceIdFieldInResourceIndex",
                "referenceIdFieldInDataIndex",
            ]
            ok = check_required_fields(
                "explorerConfig.guppyConfig.manifestMapping",
                checks,
                manifest_mapping,
                ok,
            )

    study_viewer = gitops.get("studyViewerConfig")
    ok = ok and assert_and_log(study_viewer, FieldSyntaxError("studyViewerConfig"))

    if study_viewer:
        checks = ["dataType", "listItemConfig", "rowAccessor"]
        for viewer in study_viewer:
            ok = check_required_fields("studyViewerConfig", checks, viewer, ok)

    return ok


def check_required_fields(path, checks, field, ok):
    for check in checks:
        ok = ok and assert_and_log(
            field.get("check"), FieldSyntaxError(f"{path}.{check}")
        )
    return ok


def check_field_value(path, checks, accepted_values, errors):
    for check in checks:
        if check not in accepted_values:
            errors.append(FieldError("Invalid field {} in {}".format(check, path)))
    return errors


def _validate_itemConfig(item_config, props, errors):
    errors = check_field_value(
        "studyViewerConfig.blockFields.(list/single)ItemConfig",
        item_config.get("blockFields", []),
        props,
        errors,
    )
    errors = check_field_value(
        "studyViewerConfig.tableFields.(list/single)ItemConfig",
        item_config.get("tableFields", []),
        props,
        errors,
    )
    return errors


def _validate_studyViewerConfig_helper(viewer, type_prop_map, errors):
    datatype = viewer.get("dataType")
    props = type_prop_map.get(datatype, [])
    if not props:
        errors.append(
            FieldError(
                "Invalid field {} in studyViewerConfig.dataType".format(datatype)
            )
        )

    listitemconfig = viewer.get("listItemConfig")
    errors = _validate_itemConfig(listitemconfig, props, errors)
    if viewer.get("singleItemConfig"):
        errors = _validate_itemConfig(viewer.get("singleItemConfig"), props, errors)

    for dtype, props in type_prop_map.items():
        if viewer["rowAccessor"] not in props:
            errors.append(
                FieldError(
                    "rowAccessor {} not found in index with type {}".format(
                        viewer["rowAccessor"], dtype
                    )
                )
            )

    return errors


def validate_studyViewerConfig(studyviewer, type_prop_map, errors):
    for viewer in studyviewer:
        errors = _validate_studyViewerConfig_helper(viewer, type_prop_map, errors)
    return errors


def _validate_explorerConfig_helper(explorer_config, type_prop_map, errors):

    datatype = explorer_config["guppyConfig"]["dataType"]
    props = type_prop_map.get(datatype, [])
    if not props:
        errors.append(
            FieldError(
                "Invalid field {} in explorerConfig.guppyConfig.dataType".format(
                    datatype
                )
            )
        )

    tabs = explorer_config["filters"]["tabs"]
    for tab in tabs:
        errors = check_field_value(
            "explorerConfig.filters.tabs.fields", tab.get("fields", []), props, errors
        )

    table = explorer_config["table"]
    if table["enabled"]:
        errors = check_field_value(
            "explorerConfig.table.fields", table.get("fields", []), props, errors
        )

    manifest_map = explorer_config.get("manifestMapping")
    if manifest_map and manifest_map.get("resourceIndexType"):
        resource_props = type_prop_map.get(manifest_map.get("resourceIndexType"))
        if not resource_props:
            errors.append(
                FieldError(
                    "Invalid field {} in manifestMapping.resourceIndexType".format(
                        manifest_map.get("resourceIndexType")
                    )
                )
            )
        elif manifest_map.get("resourceIdField") not in resource_props:
            errors.append(
                FieldError(
                    "Invalid field {} in manifestMapping.resourceIdField".format(
                        manifest_map.get("resourceIdField")
                    )
                )
            )
        # TODO
        # Also consider fields referenceIdFieldInResourceIndex and referenceIdFieldInDataIndex

    return errors


def validate_explorerConfig(gitops, type_prop_map, errors):
    exploreConfig = gitops.get("explorerConfig") or gitops.get("dataExplorerConfig")
    # if explorerConfig exists, ignores (data/files)explorerConfig
    if exploreConfig and type(exploreConfig) == list:
        for config in exploreConfig:
            errors = _validate_explorerConfig_helper(config, type_prop_map, errors)
    else:
        errors = _validate_explorerConfig_helper(exploreConfig, type_prop_map, errors)
        file_exp_config = gitops.get("fileExplorerConfig")
        if file_exp_config:
            errors = _validate_explorerConfig_helper(
                file_exp_config, type_prop_map, errors
            )

    return errors


def validate_against_etl(gitops, mapping_file):
    """
    Validates gitops.json configuration against an etlMapping
    Args:
        gitops (dict): gitops.json config
        mapping_file (str): path to etlMapping file

    Returns:
        Error: Returns a list of any errors encountered.

    """
    with open(mapping_file) as f:
        mappings = yaml.safe_load(f)
    mapping = mappings.get("mappings")
    type_prop_map = map_all_ES_index_props(mapping)
    errors = validate_explorerConfig(gitops, type_prop_map, [])
    studyviewer = gitops.get("studyViewerConfig")
    if studyviewer:
        errors = validate_studyViewerConfig(studyviewer, type_prop_map, errors)

    return errors


def map_all_ES_index_props(mapping):
    all_prop_map = {}
    for index in mapping:
        index_props = []
        props = index.get("props")
        index_props.extend(_extract_props(props))
        agg_props = index.get("aggregated_props")
        index_props.extend(_extract_props(agg_props))
        join_props = index.get("joining_props", [])
        for indx in join_props:
            index_props.extend(_extract_props(index.get("props")))
        inject_props = index.get("injecting_props", {})
        for node, props in inject_props.items():
            index_props.extend(_extract_props(props.get("props")))
        flat_props = index.get("flatten_props", [])
        for node in flat_props:
            index_props.extend(_extract_props(node.get("props")))
        parent_props = index.get("parent_props")
        if parent_props:
            for prop in parent_props:
                item = prop.get("path")
                # to extract values from a string like "subjects[subject_id:id,project_id]"
                [_, str_props] = (
                    list(filter(None, re.split(r"[\[\]]", item)))
                    if "[" in item
                    else [item, None]
                )
                if str_props is not None:
                    props = str_props.split(",")
                    index_props.extend(
                        [
                            p.split(":")[0].strip() if p.find(":") != -1 else p.strip()
                            for p in props
                        ]
                    )

        all_prop_map[index.get("doc_type")] = set(index_props)

    return all_prop_map


def _extract_props(props_to_extract):
    if not props_to_extract:
        return []
    return [p["name"] for p in props_to_extract]


def validate_against_dictionary(gitops, data_dictionary):
    """
    Validates gitops.json configuration against a data dictionary
    Args:
        gitops (dict): gitops.json config
        data_dictionary (str): url of data dictionary

    Returns:
        ok(bool): whether the validation succeeded.

    """

    _, model = init_dictionary(data_dictionary)
    schema = model.dictionary.schema

    ok = True
    graphql = gitops.get("graphql")
    for item in graphql.get("boardCounts"):
        node_count = item.get("graphql")
        # assumes form _{node}_count
        idx = node_count.rfind("_")
        node = node_count[1:idx]

        ok = ok and assert_and_log(
            schema.get(node) is not None,
            "Node: {} in graphql.boardCounts not found in dictionary".format(node),
        )

    for item in graphql.get("chartCounts"):
        node_count = item.get("graphql")
        # assumes form _{node}_count
        idx = node_count.rfind("_")
        node = node_count[1:idx]
        ok = ok and assert_and_log(
            schema.get(node) is not None,
            "Node: {} in graphql.chartCounts not found in dictionary".format(node),
        )

    for item in graphql.get("homepageChartNodes", []):
        node = item.get("node")
        ok = ok and assert_and_log(
            schema.get(node) is not None,
            "Node: {} in graphql.homepageChartNodes not found in dictionary".format(
                node
            ),
        )

    return ok
