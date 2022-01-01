from enum import Enum

import numpy as np
import pytest

from parameterized import *


@pytest.fixture
def example_class():
    class Test(Parameterized):
        def __init__(self):
            self.i = 5
            self.b = False
            self.s = "Hello"

    return Test


@pytest.fixture
def example_params():
    return {"i": 5, "b": False, "s": "Hello"}


class TestParameterized:
    def test_simple_get(self, example_class, example_params):
        obj = example_class()
        assert obj.get_params() == example_params

    def test_simple_update(self, example_class):
        obj = example_class()
        new_params = {"i": 0, "b": True, "s": "Goodbye"}
        obj.update_from_params(new_params)

        assert obj.i == 0
        assert obj.b == True
        assert obj.s == "Goodbye"

        assert obj.get_params() == new_params

    def test_simple_from(self, example_class, example_params):
        obj = example_class.from_params(example_params)

        assert obj.i == 5
        assert obj.b == False
        assert obj.s == "Hello"

        assert obj.get_params() == example_params

    def test_simple_str(self, example_class):
        obj = example_class()

        assert str(obj) == '{\n  "i": 5,\n  "b": false,\n  "s": "Hello"\n}'

    def test_excluded_params(self, example_class, example_params):
        example_class.excluded_params = ["i"]
        example_params.pop("i")

        # test get
        obj = example_class()
        assert obj.get_params() == example_params

        # test update
        obj.update_from_params({"i": 100, "no": False})
        assert obj.i == 5
        assert not hasattr(obj, "no")

    def test_param_types(self):
        class TempEnum(Enum):
            ONE = 1
            TWO = 2

        @register_constructors(
            enum_params=[("c", TempEnum), ("d", TempEnum)],
            numpy_params=["a", "b"])
        class TempClass(Parameterized):

            @param_constructor("f", "g")
            def fj_constructor(self, val):
                return str(val)

            @param_constructor("i")
            def i_constructor(self, val):
                return val+1

            def __init__(self):
                self.a = 0
                self.b = 1
                self.c = 2
                self.d = 3
                self.e = 4
                self.f = 5
                self.g = 6
                self.h = 7
                self.i = 8
                self.j = 9

        new_params = {
            "a": [1, 2, 3, 4, 5],
            "b": np.array([10, 20, 30, 40, 50]),
            "c": "ONE",
            "d": TempEnum.TWO,
            "e": 10,
            "f": 100,
            "g": 1000,
            "h": 10000,
            "i": 8
        }

        t = TempClass()
        t.update_from_params(new_params)

        assert(isinstance(t.a, np.ndarray))
        assert(np.array_equal(t.a, new_params["a"]))

        assert(isinstance(t.b, np.ndarray))
        assert(np.array_equal(t.b, new_params["b"]))

        assert(isinstance(t.c, TempEnum))
        assert(t.c == TempEnum.ONE)

        assert(isinstance(t.d, TempEnum))
        assert(t.d == new_params["d"])

        assert(t.e == 10)
        assert(t.f == "100")
        assert(t.g == "1000")
        assert(t.h == 10000)
        assert(t.i == 9)
        assert(t.j == 9)
