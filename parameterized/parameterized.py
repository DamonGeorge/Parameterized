"""
This file contains the Parameterized and ParameterizedABC classes
which are interfaces designed to allow implementing classes to
save and load their member variables to and from dictionaries.
"""
from __future__ import annotations

import inspect
import json
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import (Any, Callable, Dict, List, Mapping, Optional, Set, Tuple, Type,
                    TypeVar)

import numpy as np

# helpful type variable
T = TypeVar("T", bound="Parameterized")


# =========================================================
# The two main classes to inherit
# =========================================================
class Parameterized(object):
    """
    DO NOT INSTANTIATE

    Interface for objects that allow their attributes (params in this case) to
    be updated from dictionaries and loaded to dictionaries.
    This also provides factory methods for creating objects from dictionaries.

    Class attributes:
        excluded_params: Set[str] This should contain attribute names to be ignored

    Overrideable methods:
        update_from_params(params)
        get_params()
    Be sure to call the corresponding super() method when overridding those methods.
    """
    _param_serializers = {}
    _param_deserializers = {}
    _type_serializers = []
    _type_deserializers = []

    # Attribute names that should be ignored
    excluded_params = set()

    def get_params(self) -> Dict[str, Any]:
        """
        Returns dict of this object's attributes,
        excluding any attributes in the excluded_params list
        """
        return serialize_params(self.__dict__, self.excluded_params, self._param_serializers, self._type_serializers)

    def update_from_params(self, params: Mapping[str, Any], use_deserializers=True):
        """
        Update this object's attributes using the params dict.
        Any attributes in the excluded_params list will not be updated,
        and the param_serializers dict will be used to apply any necessary serializers.
        """
        # deserialize
        if use_deserializers:
            params = deserialize_params(params, self.excluded_params,
                                        self._param_deserializers, self._type_deserializers)
        # update self
        for attr in self.__dict__:
            try:
                self.__dict__[attr] = params[attr]
            except KeyError:
                pass

    @classmethod
    def from_params(cls: Type[T], params: Mapping[str, Any]) -> T:
        """
        DO NOT OVERRIDE

        Factory method for creating an object of this class using the params dict
        and this classes' update_from_params() method.
        """
        # deserialize
        params = deserialize_params(params, cls.excluded_params,
                                    cls._param_deserializers, cls._type_deserializers)
        # create object
        return create_obj_from_params(cls, params)

    # from Printable
    def __str__(self) -> str:
        """
        The toString method that prints this object's params using json indented formatting
        """
        return json.dumps(self.get_params(), indent=2)


class ParameterizedABC(Parameterized, ABC):
    """
    DO NOT INSTANTIATE

    This is an extension of the Parameterized class that can be used for interfaces.

    An interface that extends this class should define the type_enum,
    and any classes that extend that interface should specify the type_ field as a value of the type_enum.

    This Parameterized extension will then save that type_ with the class's parameters and
    then when using the from_params() factory method, the 'type' param will be used to
    construct an object of the appropriate subclass.

    excluded_subclasses should be defined in the superclass and specify the names
    of child classes to ignore (aka treat as abstract)

    """
    # subclasses of this class hierarchy that should be ignored when using the from_params() factory
    excluded_subclasses = set()

    @property
    @abstractmethod
    def type_(self) -> Enum:
        """Should just be overridden  as a class attribute; not as a function"""
        pass

    @property
    @abstractmethod
    def type_enum(self) -> Type[Enum]:
        """Should just be overridden  as a class attribute; not as a function"""
        pass

    def get_params(self) -> Dict[str, Any]:
        """ Adds the type to the params"""
        params = super().get_params()
        params.update({"type": self.type_.name})
        return params

    @classmethod
    def from_params(cls: Type[T], params: Mapping[str, Any]) -> T:
        """
        DO NOT OVERRIDE

        Create an instance of the given class given the params, which should contain the instance's "type"
        """
        # check for type_enum
        if not hasattr(cls, "type_enum"):
            raise Exception("type_enum attribute does not exist on the given class!")

        # deserialize params
        params = deserialize_params(params, cls.excluded_params,
                                    cls._param_deserializers, cls._type_deserializers)

        # get the enum type which wasn't deserialized
        t = params.pop("type")
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

        return create_obj_from_params(c, params)

    @classmethod
    def all_parameterized_subclasses(cls: T) -> Set[T]:
        """
        DO NOT OVERRIDE

        Gets all the valid parameterized subclasses of this parameterized superclass
        """
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
    def subclass_type_mapping(cls: T) -> Dict[Enum, T]:
        """
        This is a utility function that gets all the valid parameterized subclasses
        of this parameterized superclass as a dictionary of enum type:subclass pairs.
        """
        subclasses = cls.all_parameterized_subclasses()

        return {s.type_: s for s in subclasses}


# =========================================================
# Helpful Utilities
# =========================================================
def deserialize_params(params: Mapping[str, Any],
                       excluded_params: Set[str] = set(),
                       param_deserializers: Mapping[str, Callable] = {},
                       type_deserializers: List[Tuple[Any, Callable]] = []) -> Dict[str, Any]:
    """
    Attributes whose names are listed in excluded_params
    will be excluded from the update.
    """
    # shallow copy params dict without excluded params
    result = {k: v for k, v in params.items() if k not in excluded_params}

    for attr in result:
        value = result[attr]  # get the value of the param

        # if param has its own serializer, use it
        if attr in param_deserializers:
            result[attr] = param_deserializers[attr](value)
        # else use a type handler if possible
        else:
            for type_, deserializer in type_deserializers:
                if isinstance(value, type_):
                    result[attr] = deserializer(value)
                    break

    return result


def serialize_params(params: Mapping[str, Any],
                     excluded_params: Set[str] = set(),
                     param_serializers: Mapping[str, Callable] = {},
                     type_serializers: List[Tuple[Any, Callable]] = []) -> Dict[str, Any]:
    # shallow copy params dict without excluded params
    result = {k: v for k, v in params.items() if k not in excluded_params}

    for attr in result:
        value = result[attr]  # get the value of the param

        # if param has its own serializer, use it
        if attr in param_serializers:
            result[attr] = param_serializers[attr](value)
        # built-in serializers for Parameretized objects, numpy arrays, enums and Paths
        elif isinstance(value, Parameterized):
            result[attr] = value.get_params()
        elif isinstance(value, np.ndarray):
            result[attr] = value.tolist()
        elif isinstance(value, Enum):
            result[attr] = value.name
        elif isinstance(value, Path):
            result[attr] = str(value)
        # use the remaining type handlers
        else:
            for type_, serializer in type_serializers:
                if isinstance(value, type_):
                    result[attr] = serializer(value)
                    break

    return result


def create_obj_from_params(cls: Type[T], params: dict) -> T:
    """
    Creates an instance of the given class using the given params dictionary.

    Using inspection, this function provides any args or kwargs to cls.__init__()
    that exist by name in params.
    Any remaining params are passed in a final call to update_from_params()

    NOTE: This will raise an exception if any necessary positional args in cls.__init__()
    do not exist by name in the params dict.

    This returns the new instance of cls.
    """
    # copy so we don't alter original dict
    params = params.copy()
    # get args and kwargs from cls __init__()
    init_args_spec = inspect.getfullargspec(cls.__init__)

    # build args
    args = []
    for arg in init_args_spec.args[1:]:  # first arg is self
        try:
            args.append(params.pop(arg))
        except KeyError:
            raise Exception(f"Parameterized factory unable to call __init__() due to lack of required arguments")

    # build kwargs
    if init_args_spec.varkw:
        # **kwargs exists in function definition, so give all remaining params
        kwargs = params
        params = {}  # clear the remaining
    else:
        # only give valid kwargs
        kwargs = {kwarg: params.pop(kwarg) for kwarg in init_args_spec.kwonlyargs if kwarg in params}

    # create object
    result = cls(*args, **kwargs)
    # update with remaining params if any remain
    result.update_from_params(params, use_deserializers=False)
    return result


def all_subclasses(cls: T) -> Set[T]:
    """Returns a set of all the subclasses of the given class"""
    subs = cls.__subclasses__()
    return set(subs).union([s for c in subs for s in all_subclasses(c)])


def enum_serializer(value: str, enum_cls: Type[Enum]) -> Enum:
    """Converts string value to the given enum"""
    return enum_cls[value]


def numpy_serializer(value) -> np.ndarray:
    """Converts list or number to numpy array"""
    return np.asarray(value)
