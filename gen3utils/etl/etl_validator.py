from gen3utils.utils.dd import init_dictionary
from gen3utils.errors import MappingError, PropertiesError, PathError, FieldError
import yaml


def validate_aggregation_mapping(mapping, list_of_nodes):
    aggregation_key_list = ['name', 'doc_type', 'type', 'root', 'props', 'flatten_props', 'aggregated_props']
    props_attr_list = ['name', 'src', 'path', 'fn', 'value_mappings', 'props', 'sorted_by']
    nodes_with_props = {}

    for key, value in mapping.items():
        if key in aggregation_key_list:
            check_none = mapping.get(key)
            if check_none == '':
                raise Exception('Error in root properties values')
            elif key == 'props':
                for n in value:
                    if n['name'] not in nodes_with_props['subjects']:
                        raise Exception('Something wrong with root node properties, not found in dictionary')

            elif key == 'flatten_props':
                for n in value:
                    if not all(elem in props_attr_list for elem in n.keys()):
                        raise Exception('Error-Node name wrong')
                    if n['path'] not in list_of_nodes:
                        raise Exception("Path doesn't exist in dictionary")
                    elif n.values() == '':
                        raise Exception("Error in Flatten properties")
                    for l in n['props']:
                        if l['name'] == '':
                            raise Exception("Error in Flatten properties- Null Values")
                        elif l['name'] not in nodes_with_props[n['path']]:
                            raise Exception("Something wrong with Flatten properties, not found in dictionary")

            elif key == 'aggregated_props':
                for n in value:
                    if not all(elem in props_attr_list for elem in n.keys()):
                        raise Exception("Error-Node name wrong")
                    elif n.values() == '':
                        raise Exception("Error in properties value- name, src, fn etc - Null values")
                    if 'fn' in n.keys():
                        if n['fn'] not in ['set', 'count', 'list', 'sum', 'min']:
                            raise Exception("Error in Function under mapping file - " + n['fn'])
                    if 'path' in n.keys():
                        split_node = n['path'].split('.')
                        if '_ANY' in split_node:
                            split_node.remove("_ANY")
                            for s in split_node:
                                if s not in list_of_nodes:
                                    raise Exception("Aggregated props path not find in dictionary")
                        else:
                            for s in split_node:
                                if s not in list_of_nodes:
                                    raise Exception("Aggregated props path not find under dictionary")

                    if 'src' in n.keys():
                        split_node = n['path'].split('.')
                        if n['src'] not in nodes_with_props[split_node[-1]]:
                            raise Exception("src not find under dictionary")

            elif key == 'joining_props':
                join_list = ['index', 'join_on', 'props']
                # print value
                for n in value:
                    if not all(elem in join_list for elem in n.keys()):
                        raise Exception("Error-Node name wrong")
                    elif n.values() == '':
                        raise Exception("Error in properties value- index, join_on, props etc - Null values")

                    for i in n['props']:
                        if not all(elem in props_attr_list for elem in i.keys()):
                            raise Exception("Error-Node name wrong")
                        if 'fn' in i.keys():
                            if i['fn'] not in ['set', 'count', 'list', 'sum', 'min']:
                                raise Exception("Error in Function under mapping file - " + i['fn'])

        else:
            raise Exception("Root Aggregation node attributes are missing")


def validate_collector(mapping, list_of_nodes):
    props_attr_list = ['name', 'src', 'path', 'fn', 'value_mappings', 'props', 'sorted_by']
    collector_keys_list = ['name', 'doc_type', 'type', 'root', 'category', 'props', 'injecting_props']

    for key, value in mapping.items():
        if key in collector_keys_list:
            collector_key_value = mapping.get(key)
            if collector_key_value == '':
                raise Exception("Error in Collector Properties")
            elif key == 'props':
                for n in value:
                    if n.values() == '':
                        raise Exception("Error in properties of collector -")

            elif key == 'injecting_props':
                for k, v in value.items():
                    inject_props = v.get('props')
                    for a in inject_props:
                        if not all(elem in props_attr_list for elem in a.keys()):
                            raise Exception("Error in collector properties attributes - 'props'")
                        elif a.values() == '':
                            raise Exception("Error in properties of collector - Blank values")
                        else:
                            raise Exception("Error in Collector Attributes, some attributes are missing")
        else:
            raise Exception("Error in Collector Attributes, some attributes are missing")


def validate_list_props(props_list, list_of_back_refs, list_of_labels, nodes_with_props):
    if props_list is list:
        for prop in props_list.items():
            if 'path' in prop and 'props' in prop:
                for real_prop in prop.get('props'):
                    validate_prop(real_prop, list_of_back_refs, nodes_with_props, [], prop.get('path'))
            else:
                validate_prop(prop, list_of_back_refs, nodes_with_props, [])
    elif props_list is dict:
        for k, v in props_list.items():
            if k in list_of_labels:
                for prop in v.get('props'):
                    validate_prop(prop, list_of_back_refs, nodes_with_props, [])


def validate_prop(json_obj, list_of_nodes, nodes_with_props, recorded_errors, grouping_path = None):
    validate_name(json_obj.get('name'), recorded_errors)
    validate_path(json_obj.get('path', grouping_path), recorded_errors, list_of_nodes)
    validate_fn(json_obj.get('fn'), recorded_errors)
    validate_src(json_obj.get('src'), json_obj.get('path'), recorded_errors, nodes_with_props)


def validate_src(src, path, recorded_errors, nodes_with_props):
    if src is not None:
        if path is None:
            recorded_errors.append(FieldError('src field must be specified with a path'))
        else:
            path_items = path.split('.')
            if src not in nodes_with_props[path_items[-1]]:
                recorded_errors.append(FieldError('src field {} is not found in given dictionary.'.format(src)))


def validate_fn(fn, recorded_errors):
    if fn is not None:
        if fn not in ['set', 'count', 'list', 'sum', 'min', 'max']:
            recorded_errors.append(MappingError('{} function is not supported in ETL'.format(fn), 'Function'))


def validate_name(name, recorded_errors):
    if name is None:
        recorded_errors.append(PropertiesError('Missing name for a property.'))
    elif name == '':
        recorded_errors.append(PropertiesError('Name should not be empty.'))


def validate_path(path, recorded_errors, list_of_nodes):
    if path is None:
        recorded_errors.append(PropertiesError('Missing path declaration for the property.'))
    else:
        path_items = path.split('.')
        if '_ANY' in path_items:
            path_items.remove('_ANY')
        for item in path_items:
            if item not in list_of_nodes:
                recorded_errors.append(PathError(path))


def get_all_nodes(model):
    list_of_backrefs = []
    list_of_node_labels = []
    nodes_with_props = {}
    all_classes = model.Node.get_subclasses()
    for n in all_classes:
        present_node = n._pg_edges
        present_props = n.__pg_properties__
        present_node_props = [k for k in present_props.keys()]
        for v in present_node.values():
            backref = v.get('backref')
            nodes_with_props.update({backref: present_node_props})
            list_of_backrefs.append(backref)
        list_of_node_labels.append(n.get('label'))
    list_of_backrefs = list(set(list_of_backrefs))
    return list_of_backrefs, list_of_node_labels, nodes_with_props


def validate_mapping(dictionary_url, mapping_file):
    dictionary, model = init_dictionary(dictionary_url)
    mappings = yaml.load(open(mapping_file), Loader=yaml.SafeLoader)

    list_of_backrefs, list_of_labels, nodes_with_props = get_all_nodes(model)

    for m in mappings:
        for key, value in m.items():
            for n in value:
                validate_list_props(n, list_of_backrefs, list_of_labels, nodes_with_props)
