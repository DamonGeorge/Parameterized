import pytest

from parameterized import Parameterized


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
    return {
        'i': 5,
        'b': False,
        's': "Hello"
    }


class TestParameterized():

    def test_simple_get(self, example_class, example_params):
        obj = example_class()
        assert obj.get_params() == example_params

    def test_simple_update(self, example_class):
        obj = example_class()
        new_params = {
            'i': 0,
            'b': True,
            's': 'Goodbye'
        }
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
        example_class.excluded_params = ['i']
        example_params.pop('i')

        # test get
        obj = example_class()
        assert obj.get_params() == example_params

        # test update
        obj.update_from_params({'i': 100, 'no': False})
        assert obj.i == 5
        assert not hasattr(obj, 'no')
