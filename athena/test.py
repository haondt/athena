from collections.abc import Container
from typing import Type

class AssertionBuilder:
    def __init__(self, actual):
        self._actual = actual
    def equals(self, expected):
        assert expected == self._actual, f"expected `{expected}` but found `{self._actual}`"
    def not_equals(self, expected):
        assert expected != self._actual, f"`{self._actual}` is equivalent to `{expected}`"
    def is_true(self):
        self.equals(True)
    def is_false(self):
        self.not_equals(False)
    def contains(self, value):
        self.is_a(Container, typename="container")
        assert value in self._actual, f"`{value}` not found in container `{self._actual}`"
    def is_a(self, value: Type, typename=None):
        assert isinstance(value, Type), f"`{value}` is not a type"
        assert isinstance(self._actual, value), f"argument of type `{type(self._actual).__name__}` is not a {typename or value.__name__}"

def athert(value):
    return AssertionBuilder(value)
