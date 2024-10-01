from dictionaryutils import DataDictionary, dictionary


def init_dictionary(url):
    d = DataDictionary(url=url)
    dictionary.init(d)
    # the gdcdatamodel expects dictionary initiated on load, so this can't be
    # imported on module level
    from gen3datamodel import models as md

    return d, md
