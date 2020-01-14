from cdiserrors import *


class MappingError(object):
    def __init__(self, message, type):
        self.message = '{} error: {}'.format(type, message)
        self.type = type


class PropertiesError(MappingError):
    def __init__(self, message):
        super(MappingError, self).__init__(message, 'Properties')


class PathError(MappingError):
    """
    Path error specifies the path that does not exist in checking dicitonary
    :rtype: PathError object
    """

    def __init__(self, path):
        super(PathError, self).__init__('{} does not exist in this dictionary'.format(path),
                                        'Path')


class FieldError(MappingError):
    def __init__(self, message):
        super(FieldError, self).__init__(message, 'Field')
