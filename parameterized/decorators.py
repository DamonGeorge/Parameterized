from enum import Enum
from pathlib import Path
from typing import List, Tuple

import numpy as np

from parameterized.parameterized import Parameterized

# =========================================================
# Decorators
# =========================================================


def register_serializers(enum_params: List[Tuple[str, Enum]] = [],
                         numpy_params: List[str] = [],
                         path_params: List[str] = [],
                         parameterized_params: List[Tuple[str, Parameterized]] = []):
    """
    This is a class decorator.

    Use this on a class that inherits Parameterized or ParameterizedABC to
    (1) register any class methods using the following decorators:
        @param_serializer(), @param_deserializer(), @type_serializer() and @type_deserializer()
    and (2) specify any class attributes that are Enums, numpy arrays, Paths or other Parameterized objects.
        Parameterized will handle the serialization and deserialization of those parameters automatically.

    :param enum_params: A list of (attribute name, enum class) tuples that specifies
        attributes on the class that are Enums, and their corresponding Enum class.
        These attribute values are serialized into their enum names.
    :param numpy_params A list of attribute names that are numpy arrays. These are serialized into lists.
    :param path_params: A list of attribute names that are Path objects. These are serialized into strings.
    :param parameterized_params: A list of (attribute name, Parameterized class) tuples that specifies
        attributes on the class that are an object that inherits either Parameterized or ParameterizedABC.
        Specify the class that actually inherits Parameterized or ParameterizedABC as the second value
        in each tuple.
    """
    def wrapper(cls):
        # register callbacks for the enums and np arrays
        # don't need to do deserializers cause the types will work automatically
        for param, enum_cls in enum_params:
            cls._param_deserializers[param] = lambda val: val if isinstance(val, enum_cls) else enum_cls[val]
        for param in numpy_params:
            cls._param_deserializers[param] = lambda val: np.asarray(val)
        for param in path_params:
            cls._param_deserializers[param] = lambda val: Path(val)
        for param, parameterized_cls in parameterized_params:
            cls._param_deserializers[param] = lambda val: parameterized_cls.from_params(val)

            # register callbacks for specific params and types
        for method in cls.__dict__.values():
            if hasattr(method, "_param_serializers"):
                for param in method._param_serializers:
                    cls._param_serializers[param] = method
            if hasattr(method, "_param_deserializers"):
                for param in method._param_deserializers:
                    cls._param_deserializers[param] = method
            if hasattr(method, "_type_serializers"):
                for type_ in method._type_serializers:
                    cls._type_serializers.append((type_, method))
            if hasattr(method, "_type_deserializers"):
                for type_ in method._type_deserializers:
                    cls._type_deserializers.append((type_, method))
        return cls
    return wrapper


def param_serializer(*params: List[str]):
    """
    A decorator for static class methods (i.e. methods without a self parameter).
    This registers the given method as a serializer for the attributes given
    by the params arguments.
    A serializer converts the value of the attribute to a standard value that is saveable
    to common methods such as json or yaml.

    :param params: The attributes of the class to use this serializer function for.
    """
    def wrapper(func):
        func._param_serializers = params
        return func
    return wrapper


def param_deserializer(*params: List[str]):
    """
    A decorator for static class methods (i.e. methods without a self parameter).
    This registers the given method as a deserializer for the attributes given
    by the params arguments.
    A deserializer converts the serialized value of the attribute (used or saving)
    back the required/original python type.

    :param params: The attributes of the class to use this deserializer function for.
    """
    def wrapper(func):
        func._param_deserializers = params
        return func
    return wrapper


def type_serializer(*types: List):
    """
    A decorator for static class methods (i.e. methods without a self parameter).
    This registers the given method as a serializer for the types given
    by the types arguments.
    A serializer converts the value of the attribute to a standard value that is saveable
    to common methods such as json or yaml.

    :param types: Python types to use this serializer function for.
    """
    def wrapper(func):
        func._type_serializers = types
        return func
    return wrapper


def type_deserializer(*types: List):
    """
    A decorator for static class methods (i.e. methods without a self parameter).
    This registers the given method as a deserializer for the types given
    by the types arguments.
    A deserializer converts the serialized value of the attribute (used or saving)
    back the required/original python type.

    :param types: Python types to use this deserializer function for.
    """
    def wrapper(func):
        func._type_deserializers = types
        return func
    return wrapper
