# import yaml

# from cdislogging import get_logger

# from .dd_utils import init_dictionary

# logger = get_logger("validate-etl-mapping", log_level="info")


# class ValidationException(Exception):
#     def __init__(self, message, code=500):
#         self.message = str(message)
#         self.code = code


# def validate_aggregation_mapping(mapping, list_of_nodes):
#     aggregation_key_list = [
#         "name",
#         "doc_type",
#         "type",
#         "root",
#         "props",
#         "flatten_props",
#         "aggregated_props",
#     ]
#     props_attr_list = [
#         "name",
#         "src",
#         "path",
#         "fn",
#         "value_mappings",
#         "props",
#         "sorted_by",
#     ]
#     nodes_with_props = {}

#     for key, value in mapping.items():
#         if key in aggregation_key_list:
#             check_none = mapping.get(key)
#             if check_none == "":
#                 raise ValidationException("Error in root properties values")
#             elif key == "props":
#                 for n in value:
#                     if n["name"] not in nodes_with_props["subjects"]:
#                         raise ValidationException(
#                             "Something wrong with root node properties, not find in dictionary"
#                         )

#             elif key == "flatten_props":
#                 for n in value:
#                     if not all(elem in props_attr_list for elem in n.keys()):
#                         raise ValidationException("Error-Node name wrong")
#                     if n["path"] not in list_of_nodes:
#                         raise ValidationException("Path doesn't exist in dictionary")
#                     elif n.values() == "":
#                         raise ValidationException("Error in Flatten properties")
#                     for l in n["props"]:
#                         if l["name"] == "":
#                             raise ValidationException(
#                                 "Error in Flatten properties- Null Values"
#                             )
#                         elif l["name"] not in nodes_with_props[n["path"]]:
#                             raise ValidationException(
#                                 "Something wrong with Flatten properties, not find in dictionary"
#                             )

#             elif key == "aggregated_props":
#                 for n in value:
#                     if not all(elem in props_attr_list for elem in n.keys()):
#                         raise ValidationException("Error-Node name wrong")
#                     elif n.values() == "":
#                         raise ValidationException(
#                             "Error in properties value- name, src, fn etc - Null values"
#                         )
#                     if "fn" in n.keys():
#                         if n["fn"] not in ["set", "count", "list", "sum", "min"]:
#                             raise ValidationException(
#                                 "Error in Function under mapping file - " + n["fn"]
#                             )
#                     if "path" in n.keys():
#                         split_node = n["path"].split(".")
#                         if "_ANY" in split_node:
#                             split_node.remove("_ANY")
#                             for s in split_node:
#                                 if s not in list_of_nodes:
#                                     raise ValidationException(
#                                         "Aggregated props path not find in dictionary"
#                                     )
#                         else:
#                             for s in split_node:
#                                 if s not in list_of_nodes:
#                                     raise ValidationException(
#                                         "Aggregated props path not find under dictionary"
#                                     )

#                     if "src" in n.keys():
#                         split_node = n["path"].split(".")
#                         if n["src"] not in nodes_with_props[split_node[-1]]:
#                             raise ValidationException("src not find under dictionary")

#             elif key == "joining_props":
#                 join_list = ["index", "join_on", "props"]
#                 # print value
#                 for n in value:
#                     if not all(elem in join_list for elem in n.keys()):
#                         raise ValidationException("Error-Node name wrong")
#                     elif n.values() == "":
#                         raise ValidationException(
#                             "Error in properties value- index, join_on, props etc - Null values"
#                         )

#                     for i in n["props"]:
#                         if not all(elem in props_attr_list for elem in i.keys()):
#                             raise ValidationException("Error-Node name wrong")
#                         if "fn" in i.keys():
#                             if i["fn"] not in ["set", "count", "list", "sum", "min"]:
#                                 raise ValidationException(
#                                     "Error in Function under mapping file - " + i["fn"]
#                                 )

#         else:
#             raise ValidationException("Root Node attributes are missing")


# def validate_collector(mapping, list_of_nodes):
#     props_attr_list = [
#         "name",
#         "src",
#         "path",
#         "fn",
#         "value_mappings",
#         "props",
#         "sorted_by",
#     ]
#     collector_keys_list = [
#         "name",
#         "doc_type",
#         "type",
#         "root",
#         "category",
#         "props",
#         "injecting_props",
#     ]

#     for key, value in mapping.items():
#         if key in collector_keys_list:
#             collector_key_value = mapping.get(key)
#             if collector_key_value == "":
#                 raise ValidationException("Error in Collector Properties")
#             elif key == "props":
#                 for n in value:
#                     if n.values() == "":
#                         raise ValidationException("Error in properties of collector -")

#             elif key == "injecting_props":
#                 for k, v in value.items():
#                     inject_props = v.get("props")
#                     for a in inject_props:
#                         if not all(elem in props_attr_list for elem in a.keys()):
#                             raise ValidationException(
#                                 "Error in collector properties attributes - 'props'"
#                             )
#                         elif a.values() == "":
#                             raise ValidationException(
#                                 "Error in properties of collector - Blank values"
#                             )
#                         else:
#                             raise ValidationException(
#                                 "Error in Collector Attributes, some attributes are missing"
#                             )
#         else:
#             raise ValidationException(
#                 "Error in Collector Attributes, some attributes are missing"
#             )


# def get_all_nodes(model):
#     list_of_nodes = []
#     nodes_with_props = {}
#     all_classes = model.Node.get_subclasses()
#     for n in all_classes:
#         present_node = n._pg_edges
#         present_props = n.__pg_properties__
#         present_node_props = [k for k in present_props.keys()]
#         for v in present_node.values():
#             respo = v["backref"]
#             nodes_with_props.update({respo: present_node_props})
#             list_of_nodes.append(respo)
#     list_of_nodes = list(set(list_of_nodes))
#     return list_of_nodes, nodes_with_props


# def validate_etl_mapping(dictionary_url, etl_mappings):
#     logger.info("Initializing dictionary from URL...")
#     _, model = init_dictionary(dictionary_url)
#     list_of_nodes, _ = get_all_nodes(model)

#     for m in etl_mappings:
#         if m["type"] == "aggregator":
#             validate_aggregation_mapping(m, list_of_nodes)
#         elif m["type"] == "collector":
#             validate_collector(m, list_of_nodes)
