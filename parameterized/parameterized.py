"""
This file contains the Parameterized and ParameterizedInterface classes
which are interfaces designed to allow implementing classes to
save and load their member variables to and from dictionaries.
"""
import json
# supported types for parsing to/from json:
from enum import Enum
import numpy as np
from pathlib import Path


class Parameterized(object):
    """
    Interface for objects that allow their attributes (params in this case) to
    be updated from dictionaries and loaded to dictionaries

    This also provides factory methods for creating objects from dictionaries.

    DO NOT INSTANTIATE
    """

    excluded_params = []  # Attribute names that should not be considered params

    def update_from_params(self, params: dict):
        """
        Update this object's attributes using the params dict.
        Any attributes in the excluded_params list will not be updated
        """
        update_attr_from_dict(self, params, excluded_keys=self.excluded_params)

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


class ParameterizedInterface(Parameterized):
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

    _type = None
    _type_enum = {}

    def get_params(self) -> dict:
        """ Adds the type to the params"""
        params = super().get_params()
        params.update({'type': self._type})
        return params

    @classmethod
    def from_params(cls, params: dict):
        """Create the instance given the params, which should contain the instance's "type" """
        if not hasattr(cls, "_type_enum"):
            raise Exception("_type_enum attribute does not exist on the given class!")

        t = params['type']  # the enum type

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
            raise Exception("Attempted to retrieve parameterized subclasses of a non-parameterized superclass!")

        subs = all_subclasses(cls)

        return {s for s in subs if hasattr(s, "_type") and type(s._type) == cls._type_enum and s.__name__ not in cls.excluded_subclasses}

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
def update_attr_from_dict(obj, params, excluded_keys=None):
    """
    Updates class members in obj using the dict params.

    This uses __dict__ to update self's attributes,
    so this will NOT update static class members / constants.
    It will only work on attributes defined in __init__ using self.<attr_name>

    keys in excluded_keys will not be used to update the class members
    """

    if excluded_keys is None:
        excluded_keys = []
    for key in obj.__dict__:  # loop object attributes
        if key in params and key not in excluded_keys:  # update if the key is in the params and is not excluded
            obj.__dict__[key] = params[key]


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
    return set(subs).union(
        [s for c in subs for s in all_subclasses(c)])
