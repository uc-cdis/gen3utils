import yaml
import re
from gen3utils.utils.dd import init_dictionary
from gen3utils.errors import MappingError, PropertiesError, PathError, FieldError
from gen3utils.assertion import assert_and_log


class Prop():
    def __init__(self, name):
        self.name = name


class Index():
    def __init__(self, name):
        self.name = name
        id_name = '{}_id'.format(name)
        self.props = { id_name: Prop(id_name) }


def validate_joining_list_props(props_list, recorded_errors, existing_indices):
    if type(props_list) is list:
        for prop in props_list:
            if 'index' in prop and 'join_on' in prop:
                for real_prop in prop.get('props'):
                    validate_joining_prop(real_prop, recorded_errors, existing_indices.get(prop.get('index')))


def validate_list_props(props_list, labels_to_back_refs, nodes_with_props, recorded_errors, grouping_path, index):
    if type(props_list) is list:
        for prop in props_list:
            if 'path' in prop and 'props' in prop and 'index' not in prop and 'join_on' not in prop:
                for real_prop in prop.get('props'):
                    new_props = validate_prop(real_prop, labels_to_back_refs.values(), nodes_with_props, recorded_errors,
                                             prop.get('path', grouping_path))
                    index.props.update({p.name: p for p in new_props})
            elif 'index' not in prop and 'join_on' not in prop:
                new_props = validate_prop(prop, labels_to_back_refs.values(), nodes_with_props, recorded_errors, grouping_path)
                index.props.update({ p.name: p for p in new_props })
    elif type(props_list) is dict:
        for k, v in props_list.items():
            if k in labels_to_back_refs.keys():
                for prop in v.get('props'):
                    new_props = validate_prop(prop, labels_to_back_refs.values(), nodes_with_props, recorded_errors,
                                         labels_to_back_refs.get(k))
                    index.props.update({p.name: p for p in new_props})


def validate_joining_prop(json_obj, recorded_errors, joining_index):
    name = validate_name(json_obj, recorded_errors)
    validate_fn(json_obj, recorded_errors)
    validate_joining_src(json_obj, recorded_errors, joining_index.props)
    return Prop(name)


def validate_prop(json_obj, list_of_nodes, nodes_with_props, recorded_errors, grouping_path = None):
    names = validate_path(json_obj, grouping_path, recorded_errors, list_of_nodes, nodes_with_props)
    if len(names) == 0:
        names.append(validate_name_src(json_obj, json_obj.get('path', grouping_path), recorded_errors, nodes_with_props))

    props = [Prop(n) for n in names]
    return props


def validate_joining_src(json_obj, recorded_errors, joining_props):
    src = json_obj.get('src', json_obj.get('name'))
    if src is not None:
        if src not in joining_props:
            recorded_errors.append(FieldError('src field {} (declared in {}) is not found in joining index.'
                                              .format(src, json_obj)))
    else:
        recorded_errors.append(FieldError('Missing source field for {}'.format(json_obj)))


def validate_fn(json_obj, recorded_errors):
    fn = json_obj.get('fn')
    if fn is not None:
        if fn not in ['set', 'count', 'list', 'sum', 'min', 'max']:
            recorded_errors.append(MappingError('{} function (declared in {}) is not supported in ETL'
                                                .format(fn, json_obj), 'Function'))
    return fn


def validate_name(json_obj, recorded_errors):
    name = json_obj.get('name')
    if name is None:
        recorded_errors.append(PropertiesError('Missing name for mapping property {}.'.format(json_obj)))
    elif name == '':
        recorded_errors.append(PropertiesError('Name should not be empty for mapping property {}.'.format(json_obj)))
    return name

def validate_name_src(json_obj, path, recorded_errors, nodes_with_props):
    name = validate_name(json_obj, recorded_errors)
    fn = validate_fn(json_obj, recorded_errors)
    src = json_obj.get('src', name)
    if src is not None:
        if path is None:
            recorded_errors.append(FieldError('src field must be specified with a path for {}'.format(json_obj)))
        else:
            path_items = path.split('.')
            if fn != 'count' and src not in nodes_with_props[path_items[-1]]:
                recorded_errors.append(FieldError('src field {} (declared in {}) is not found in given dictionary.'
                                                  .format(src, json_obj)))
    return name


def validate_path(json_obj, grouping_path, recorded_errors, list_of_nodes, nodes_with_props):
    path = json_obj.get('path', grouping_path)
    names = []
    if path is None:
        recorded_errors.append(PropertiesError('Missing path declaration for the property {}.'.format(json_obj)))
    else:
        path_items = path.split('.')
        if '_ANY' in path_items:
            path_items.remove('_ANY')
        for item in path_items:
            [edge, str_fields] = list(filter(None, re.split(r'[\[\]]', item))) if item.find('[') != -1 else [item, None]
            if edge not in list_of_nodes:
                recorded_errors.append(PathError(path))
            if str_fields is not None:
                fields = str_fields.split(',')
                for f in fields:
                    src = f.split(':')[-1] if f.find(':') != -1 else f
                    name = f.split(':')[0] if f.find(':') != -1 else f
                    names.append(validate_name_src({'name': name, 'src': src}, edge, recorded_errors, nodes_with_props))
    return names


def get_all_nodes(model):
    labels_to_back_refs = {}
    nodes_with_props = {}
    categories_to_labels = {}
    all_classes = model.Node.get_subclasses()
    for n in all_classes:
        present_node = n._pg_edges
        present_props = n.__pg_properties__
        present_node_props = [k for k in present_props.keys()]
        present_node_props.append('id')
        category = n._dictionary.get('category')
        if category not in categories_to_labels:
            categories_to_labels[category] = []
        categories_to_labels.get(category).append(n.label)
        backref = ''
        if len(present_node) > 0:
            backref = list(present_node.values())[0].get('backref')
            labels_to_back_refs[n.label] = backref
        nodes_with_props.update({backref: present_node_props})
    return labels_to_back_refs, nodes_with_props, categories_to_labels


def validate_mapping(dictionary_url, mapping_file):
    dictionary, model = init_dictionary(dictionary_url)
    mappings = yaml.load(open(mapping_file), Loader=yaml.SafeLoader)

    labels_to_back_refs, nodes_with_props, categories_to_labels = get_all_nodes(model)

    recorded_errors = []
    indices = {}
    for m in mappings.get('mappings'):
        index = Index(m.get('doc_type'))
        indices[index.name] = index
        category = m.get('category')
        if category is not None:
            first_categorized_node = categories_to_labels.get(category)[0]
        else:
            first_categorized_node = m.get('doc_type')
        for key, value in m.items():
            if key.find('props') != -1:
                root_path = labels_to_back_refs.get(first_categorized_node) if key == 'props' else None
                validate_list_props(value, labels_to_back_refs, nodes_with_props, recorded_errors, root_path, index)
    for m in mappings.get('mappings'):
        for k, v in m.items():
            validate_joining_list_props(v, recorded_errors, indices)
    assert_and_log(recorded_errors == [], 'errors list: {}'.format(recorded_errors))
