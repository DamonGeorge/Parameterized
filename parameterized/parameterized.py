"""
This file contains the Parameterized and ParameterizedABC classes
which are interfaces designed to allow implementing classes to
save and load their member variables to and from dictionaries.
"""
import inspect
import json
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path

import numpy as np


# =========================================================
# The two main classes to inherit
# =========================================================
class Parameterized(object):
    """
    Interface for objects that allow their attributes (params in this case) to
    be updated from dictionaries and loaded to dictionaries

    This also provides factory methods for creating objects from dictionaries.

    DO NOT INSTANTIATE
    """

    excluded_params = set()  # Attribute names that should not be considered params
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
        return json.dumps(self.get_params(), indent=2)


class ParameterizedABC(Parameterized, ABC):
    """
    This is an extension of the Parameterized class that can be used for interfaces.

    An interface that extends this class should define the type_enum,
    and any classes that extend that interface should specify the type_ field as a value of the type_enum.

    This Parameterized extension will then save that type_ with the class's parameters and
    then when using the from_params() factory method, the 'type' param will be used to
    construct an object of the appropriate subclass.

    excluded_subclasses should be defined in the superclass and specify the names
    of child classes to ignore (aka treat as abstract)

    DO NOT INSTANTIATE
    """

    excluded_subclasses = set()

    @property
    @abstractmethod
    def type_(self):
        """Should just be overridden  as a class attribute; not as a function"""
        pass

    @property
    @abstractmethod
    def type_enum(self):
        """Should just be overridden  as a class attribute; not as a function"""
        pass

    def get_params(self) -> dict:
        """ Adds the type to the params"""
        params = super().get_params()
        params.update({"type": self.type_})
        return params

    @classmethod
    def from_params(cls, params: dict):
        """Create the instance given the params, which should contain the instance's "type" """
        if not hasattr(cls, "type_enum"):
            raise Exception("type_enum attribute does not exist on the given class!")

        t = params["type"]  # the enum type

        # in case we only have the name of the enum
        if not isinstance(t, Enum):
            t = cls.type_enum[t]

        # get sub classes via inspection
        subclasses = cls.all_parameterized_subclasses()

        # find specific sub class
        found = False
        for c in subclasses:
            if c.type_ == t:
                found = True
                break

        if not found:
            raise Exception(f"Unable to create subclass of the given type: {t}")

        result = c()

        result.update_from_params(params)
        return result

    @classmethod
    def all_parameterized_subclasses(cls):
        """Gets all the valid parameterized subclasses of this parameterized superclass"""
        if not hasattr(cls, "type_enum"):
            raise Exception(
                "Attempted to retrieve parameterized subclasses of a non-parameterized superclass!"
            )

        subs = all_subclasses(cls)

        return {
            s
            for s in subs
            if hasattr(s, "type_")
            and type(s.type_) == cls.type_enum
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

        return {s.type_: s for s in subclasses}


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
