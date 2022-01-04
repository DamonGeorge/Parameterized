import json
from enum import Enum

import pytest

from parameterized import ParameterizedABC


@pytest.fixture
def example_enum():
    class TestEnum(Enum):
        ONE = 1
        TWO = 2
        THREE = 3

    return TestEnum


class TestParameterizedABC:
    def test_abc(self, example_enum):
        class BadParent(ParameterizedABC):
            def __init__(self):
                pass

        class BadBadChild(BadParent):
            def __init__(self):
                super().__init__()

        class GoodParent(ParameterizedABC):
            _type_enum = example_enum

            def __init__(self):
                pass

        class BadChild(GoodParent):
            def __init__(self):
                super().__init__()

        class GoodChild(GoodParent):
            _type = example_enum.ONE

            def __init__(self):
                super().__init__()

        with pytest.raises(TypeError):
            t = BadParent()  # pylint:disable=abstract-class-instantiated

        with pytest.raises(TypeError):
            t = BadBadChild()  # pylint:disable=abstract-class-instantiated

        with pytest.raises(TypeError):
            t = BadChild()  # pylint:disable=abstract-class-instantiated

        # this shouldn't error
        GoodChild()
