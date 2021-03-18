"""
This file contains the Parameterized and ParameterizedInterface classes
which are interfaces designed to allow implementing classes to
save and load their member variables to and from dictionaries.
"""
import inspect
import json
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path

import numpy as np


class Parameterized(object):
    """
    Interface for objects that allow their attributes (params in this case) to
    be updated from dictionaries and loaded to dictionaries

    This also provides factory methods for creating objects from dictionaries.

    DO NOT INSTANTIATE
    """

    excluded_params = []  # Attribute names that should not be considered params
    param_constructors = {}  # types of params

    def update_from_params(self, params: dict):
        """
        Update this object's attributes using the params dict.
        Any attributes in the excluded_params list will not be updated,
        and the param_constructors dict will be used to apply any necessary constructors.
        """
        update_attr_from_dict(self, params,
                              excluded_keys=self.excluded_params,
                              constructors=self.param_constructors)

    def get_params(self) -> dict:
        """
        Returns dict of this object's attributes,
        excluding any attributes in the excluded_params list
        """
        params = self.__dict__.copy()
        [params.pop(key) for key in self.excluded_params if key in params]
        return params

    @classmethod
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

    @property
    @abstractmethod
    def _type(self):
        """Should just be overridden  as a class attribute; not as a function"""
        pass

    @property
    @abstractmethod
    def _type_enum(self):
        """Should just be overridden  as a class attribute; not as a function"""
        pass

    def get_params(self) -> dict:
        """ Adds the type to the params"""
        params = super().get_params()
        params.update({"type": self._type})
        return params

    @classmethod
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

    @classmethod
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
def update_attr_from_dict(obj, params, excluded_keys=[], constructors={}):
    """
    Updates the instance attributes of obj (value in obj.__dict__)
    using the given params dict.

    Attributes whose names are listed in excluded_keys
    will be excluded from the update.

    The constructors dict can specify a single type constructor or tuple of (type, constructor)
    to be used to convert values in the params dict to the correct type during the update.
    If a tuple of (type, constructor) is provided for a given attribute,
    the constructor function will only be called if the type is None,
    or if the new value of the attribute is not of the given type.
    """

    # loop object attributes
    # and update if the attr is in the params and is not excluded
    for key in obj.__dict__:
        if key in params and key not in excluded_keys:
            # get value and corresponding type
            value = params[key]
            type_ = constructors.get(key, None)
            constructor_ = type_

            # handle if type_ is tuple of (type, constructor)
            if isinstance(type_, tuple):
                if len(type_) >= 2:
                    constructor_ = type_[1]
                    type_ = type_[0]
                else:
                    constructor_ = type_[0]
                    type_ = type_[0]
            # other special types: numpy arrays and enums
            elif type_ == np.ndarray:
                constructor_ = np.array
            elif inspect.isclass(type_) and issubclass(type_, Enum):
                def construct_enum(x): return type_[x]
                constructor_ = construct_enum

            # coerce to correct type if possible
            if constructor_ is not None and callable(constructor_) \
                    and (type_ is None or not isinstance(value, type_)):
                value = constructor_(value)

            # update the attribute
            obj.__dict__[key] = value


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
