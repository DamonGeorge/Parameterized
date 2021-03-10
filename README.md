[![Format, Lint, Test](https://github.com/DamonGeorge/Parameterized/actions/workflows/python-main.yml/badge.svg)](https://github.com/DamonGeorge/Parameterized/actions/workflows/python-main.yml)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/DamonGeorge/Parameterized)

# Parameterized
A simple Python library for creating Parameterized objects that can be saved and loaded to or from dictionaries (and json).

## Installation
```
python -m pip install git+https://github.com/DamonGeorge/Parameterized.git
```
Feel free to specify a release tag or other commit or marker (eg by appending `@v0.1`).

## Usage
Basic import example: `import parameterized`

Specified import example: `from parameterized import Parameterized`

### Parameterized
Import and extend the `Parameterized` class in order to gain its functionality.

The `Parameterized` class provides functions that allow an object to update its attributes from a dictionary using the `update_params()` method. The `Parameterized` class only works with attributes accessible from `obj.__dict__` (i.e. attributes defined using `self`). `Parameterized` also allows one to retrieve those attributes in dictionary form using `get_params()`. Lastly, this class provides the `from_params()` factory method which creates an object of the given class using a params dictionary. This class allows Parameterized objects to easily be shared across code, saved and loaded to and from json files, and edited by users in json files or in graphical interfaces.

One last important note: The `excluded_params` class attribute allows the developer to specify a list of attribute names that will be excluded from the dictionary parsing. In other words, if an attribute's name is in that list, then `update_params()` can't update that attribute, `get_params()` won't include that attribute in the returned dict, and `from_params()` won't set that attribute when creating a new object.

### ParameterizedInterface
The `ParameterizedInterface` class adds more functionality. This class is intended to be inherited by class structures that have a single abstract interface. An abstract interface that inherits the ParameterizedInterface, must define a `_type_enum` attribute.

The `_type_enum` is an Enum whose attributes define all the sub classes of the abstract interface. Ideally the names of such an Enum should be short and sweet, and the values of the Enum should be readable.

All the child classes that implement the abstract interface must include a `_type` class attribute that is the value of the `_type_enum` corresponding to that child class.

These additions result in the `_type` attribute of a class being included in the parameters returned from `get_params()` as the key `"type"`. This then allows the developer to create an instance of the specified class by passing the param dictionary to `ParameterizedInterface.from_params()`.

The abstract parent class that extends `ParameterizedInterface` can also specify a list of names of child classes to exclude from this heirarchy in the `excluded_subclasses` class attribute.

### Helper Utilities
#### `update_attr_from_dict(obj, params, excluded_keys=None)`
This utility updates the instance attributes of `obj` using the `params` dictionary, ignoring any attributes in the `excluded_keys` list

#### `default_json_serializer(obj)`
This utility can be used as the `default` parameter in `json.dump()` to allow the serialization of `Parameterized` objects, `Enum` objects, `numpy` arrays, and `pathlib.Path` objects.

#### `all_subclasses(cls)`
This utility returns a set of all the subclasses of the given class.
