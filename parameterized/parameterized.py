"""
This file contains the Parameterized and ParameterizedInterface classes
which are interfaces designed to allow implementing classes to
save and load their member variables to and from dictionaries.
"""
import array
import inspect
import json
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path

import numpy as np


# =========================================================
# Decorators
# =========================================================
def register_serializers(enum_params=[], numpy_params=[], path_params=[]):
    def wrapper(cls):
        # register callbacks for the enums and np arrays
        # don't need to do deserializers cause the types will work automatically
        for param, enum_cls in enum_params:
            cls._param_deserializers[param] = lambda val: val if isinstance(val, enum_cls) else enum_cls[val]
        for param in numpy_params:
            cls._param_deserializers[param] = lambda val: np.asarray(val)
        for param in path_params:
            cls._param_deserializers[param] = lambda val: Path(val)

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


def param_serializer(*params):
    def wrapper(func):
        func._param_serializers = params
        return func
    return wrapper


def param_deserializer(*params):
    def wrapper(func):
        func._param_deserializers = params
        return func
    return wrapper


def type_serializer(*types):
    def wrapper(func):
        func._type_serializers = types
        return func
    return wrapper


def type_deserializer(*types):
    def wrapper(func):
        func._type_deserializers = types
        return func
    return wrapper


# =========================================================
# The two main classes to inherit
# =========================================================
@register_serializers()
class Parameterized(object):
    """
    Interface for objects that allow their attributes (params in this case) to
    be updated from dictionaries and loaded to dictionaries

    This also provides factory methods for creating objects from dictionaries.

    DO NOT INSTANTIATE
    """

    excluded_params = []  # Attribute names that should not be considered params
    _param_serializers = {}
    _param_deserializers = {}
    _type_serializers = []
    _type_deserializers = []

    def update_from_params(self, params: dict):
        """
        Update this object's attributes using the params dict.
        Any attributes in the excluded_params list will not be updated,
        and the param_serializers dict will be used to apply any necessary serializers.
        """
        # deserialize the params into self
        deserialize_params(params, self,
                           self.excluded_params, self._param_deserializers, self._type_deserializers)

    def get_params(self) -> dict:
        """
        Returns dict of this object's attributes,
        excluding any attributes in the excluded_params list
        """
        params = self.__dict__.copy()
        # remove excluded params
        for key in self.excluded_params:
            params.pop(key, None)
        # return the serialized params
        serialize_params(params, self._param_serializers, self._type_serializers)
        return params

    @ classmethod
    def from_params(cls, params: dict):
        """
        Factory method for creating an object of this class using the params dict
        and this classes' update_from_params() method.

        **This method is not mean to be overridden by sub classes**
        """
        settings = cls()
        settings.update_from_params(params)
        return settings

    # from Printable
    def __str__(self) -> str:
        """
        The toString method that prints this object's params using json indented formatting
        """
        return json.dumps(self.get_params(), indent=2, default=default_json_serializer)


class ParameterizedInterface(Parameterized, ABC):
    """
    This is an extension of the Parameterized class that can be used for interfaces.

    An interface that extends this class should define the _type_enum,
    and any classes that extend that interface should specify the _type field as a value of the _type_enum.

    This Parameterized extension will then save that _type with the class's parameters and
    then when using the from_params() factory method, the 'type' param will be used to
    construct an object of the appropriate subclass.

    excluded_subclasses should be defined in the superclass and specify the names
    of child classes to ignore (aka treat as abstract)

    DO NOT INSTANTIATE
    """

    excluded_subclasses = []
    excluded_params = []

    @ property
    @ abstractmethod
    def _type(self):
        """Should just be overridden  as a class attribute; not as a function"""
        pass

    @ property
    @ abstractmethod
    def _type_enum(self):
        """Should just be overridden  as a class attribute; not as a function"""
        pass

    def get_params(self) -> dict:
        """ Adds the type to the params"""
        params = super().get_params()
        params.update({"type": self._type})
        return params

    @ classmethod
    def from_params(cls, params: dict):
        """Create the instance given the params, which should contain the instance's "type" """
        if not hasattr(cls, "_type_enum"):
            raise Exception("_type_enum attribute does not exist on the given class!")

        t = params["type"]  # the enum type

        # in case we only have the name of the enum
        if not isinstance(t, Enum):
            t = cls._type_enum[t]

        # get sub classes via inspection
        subclasses = cls.all_parameterized_subclasses()

        # find specific sub class
        found = False
        for c in subclasses:
            if c._type == t:
                found = True
                break

        if not found:
            raise Exception(f"Unable to create subclass of the given type: {t}")

        result = c()

        result.update_from_params(params)
        return result

    @ classmethod
    def all_parameterized_subclasses(cls):
        """Gets all the valid parameterized subclasses of this parameterized superclass"""
        if not hasattr(cls, "_type_enum"):
            raise Exception(
                "Attempted to retrieve parameterized subclasses of a non-parameterized superclass!"
            )

        subs = all_subclasses(cls)

        return {
            s
            for s in subs
            if hasattr(s, "_type")
            and type(s._type) == cls._type_enum
            and not inspect.isabstract(s)
            and s.__name__ not in cls.excluded_subclasses
        }

    @classmethod
    def subclass_type_mapping(cls):
        """
        Gets all the valid parameterized subclasses of this parameterized superclass
        as a dictionary of type:subclass pairs.

        This can be overridden with a custom dictionary if necessary - not preferred though.
        """
        subclasses = cls.all_parameterized_subclasses()

        return {s._type: s for s in subclasses}


# =========================================================
# Helpful Utilities
# =========================================================
def deserialize_params(params, output_obj=None,
                       excluded_params=[],
                       param_deserializers={}, type_deserializers=[]):
    """
    Attributes whose names are listed in excluded_params
    will be excluded from the update.
    """
    def serialize(key):
        value = params[key]  # get the value of the param

        # if param has its own serializer, use it
        if key in param_deserializers:
            return param_deserializers[key](value)
        # use the remaining type handlers
        else:
            for type_, deserializer in type_deserializers:
                if isinstance(value, type_):
                    return deserializer(value)
        return value

    if output_obj is not None:
        # if we have an object, only update attributes on the object
        for attr in output_obj.__dict__:
            if attr in params and attr not in excluded_params:
                output_obj.__dict__[attr] = serialize(attr)

    else:
        # else just update the provided dict
        for attr in params:
            if attr not in excluded_params:
                params[attr] = serialize(attr)


def serialize_params(params, param_serializers={}, type_serializers=[]):
    for key in params:
        value = params[key]  # get the value of the param

        # if param has its own serializer, use it
        if key in param_serializers:
            params[key] = param_serializers[key](value)
        # built-in serializers for Parameretized objects, numpy arrays, enums and Paths
        elif isinstance(value, Parameterized):
            params[key] = value.get_params()
        elif isinstance(value, np.ndarray):
            params[key] = value.tolist()
        elif isinstance(value, Enum):
            params[key] = value.name
        elif isinstance(value, Path):
            params[key] = str(value)
        # use the remaining type handlers
        else:
            for type_, serializer in type_serializers:
                if isinstance(value, type_):
                    params[key] = serializer(value)
                    break


def default_json_serializer(obj):
    """
    This can be used as the 'default' parameter in json.dump
    to allow the serialization of parameterized or enum objects
    """
    if isinstance(obj, Parameterized):
        return obj.get_params()
    elif isinstance(obj, Enum):
        return obj.name
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, Path):
        return str(obj)
    else:
        raise TypeError(f"Attempted to parse unrecognized type {type(obj)}")


def all_subclasses(cls):
    """Returns a set of all the subclasses of the given class"""
    subs = cls.__subclasses__()
    return set(subs).union([s for c in subs for s in all_subclasses(c)])


def enum_serializer(value: str, enum_cls):
    """Converts string value to the given enum"""
    return enum_cls[value]


def numpy_serializer(value):
    """Converts list or number to numpy array"""
    return np.asarray(value)
