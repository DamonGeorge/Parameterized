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
def register_constructors(enum_params=[], numpy_params=[]):
    def wrapper(cls):
        # register callbacks for the enums and np arrays
        # don't need to do deconstructors cause the types will work automatically
        for param, enum_cls in enum_params:
            cls._param_constructors[param] = lambda slf, val: val if isinstance(val, enum_cls) else enum_cls[val]
        for param in numpy_params:
            cls._param_constructors[param] = lambda slf, val: np.asarray(val)

        # register callbacks for specific params and types
        for method in cls.__dict__.values():
            if hasattr(method, "_param_constructors"):
                for param in method._param_constructors:
                    cls._param_constructors[param] = method
            if hasattr(method, "_param_deconstructors"):
                for param in method._param_deconstructor:
                    cls._param_deconstructors[param] = method
            if hasattr(method, "_type_constructors"):
                for type_ in method._type_constructors:
                    cls._type_constructors.append((type_, method))
            if hasattr(method, "_type_deconstructors"):
                for type_ in method._type_deconstructors:
                    cls._type_deconstructors.append((type_, method))
        return cls
    return wrapper


def param_constructor(*params):
    def wrapper(func):
        func._param_constructors = params
        return func
    return wrapper


def param_deconstructor(*params):
    def wrapper(func):
        func._param_deconstructors = params
        return func
    return wrapper


def type_constructor(*types):
    def wrapper(func):
        func._type_constructors = types
        return func
    return wrapper


def type_deconstructor(*types):
    def wrapper(func):
        func._type_deconstructors = types
        return func
    return wrapper


# =========================================================
# The two main classes to inherit
# =========================================================
@register_constructors()
class Parameterized(object):
    """
    Interface for objects that allow their attributes (params in this case) to
    be updated from dictionaries and loaded to dictionaries

    This also provides factory methods for creating objects from dictionaries.

    DO NOT INSTANTIATE
    """

    excluded_params = []  # Attribute names that should not be considered params
    _param_constructors = {}
    _param_deconstructors = {}
    _type_constructors = []
    _type_deconstructors = []

    def update_from_params(self, params: dict):
        """
        Update this object's attributes using the params dict.
        Any attributes in the excluded_params list will not be updated,
        and the param_constructors dict will be used to apply any necessary constructors.
        """
        update_attr_from_dict(self, params,
                              excluded_keys=self.excluded_params,
                              type_constructors=self._type_constructors,
                              param_constructors=self._param_constructors)

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

    @type_deconstructor(np.ndarray, array.array)
    def array_deconstructor(self, arr):
        return arr.tolist()

    @type_deconstructor(Enum)
    @staticmethod
    def enum_deconstructor(self, en):
        return en.name


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
def update_attr_from_dict(obj, params, excluded_keys=[],
                          type_constructors={}, param_constructors=[]):
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
            # get value
            value = params[key]

            # if param has its own constructor, use it
            if key in param_constructors:
                value = param_constructors[key](obj, value)
            else:
                for type_, constructor in type_constructors:
                    if isinstance(value, type_):
                        value = constructor(obj, value)
                        break

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


def enum_constructor(value: str, enum_cls):
    """Converts string value to the given enum"""
    return enum_cls[value]


def numpy_constructor(value):
    """Converts list or number to numpy array"""
    return np.asarray(value)
