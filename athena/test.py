from collections.abc import Container
from typing import Type

class AssertionBuilder:
    """Builder class for creating assertions."""
    def __init__(self, actual):
        self._actual = actual
    def equals(self, expected):
        """Assert equality.

        Args:
            expected (Any): the expected value.

        Raises:
            AssertionError: If the actual value does not equal the expected value.
        """
        assert expected == self._actual, f"expected `{expected}` but found `{self._actual}`"
    def not_equals(self, expected):
        """Assert inequality.

        Args:
            expected (Any): the value that the actual value should not equal.

        Raises:
            AssertionError: If the actual value equals the expected value.
        """
        assert expected != self._actual, f"`{self._actual}` is equivalent to `{expected}`"
    def is_true(self):
        """Assert that the value is `True`.

        Raises:
            AssertionError: If the actual value is not `True`.
        """
        self.equals(True)
    def is_false(self):
        """Assert that the value is `False`.

        Raises:
            AssertionError: If the actual value is not `False`.
        """
        self.equals(False)
    def contains(self, value):
        """Assert that the actual value contains the given value.

        Args:
            value (Any): the value that should be present.

        Raises:
            AssertionError: If the actual value is not a container, or the actual value does not contain the given value.
        """
        self.is_a(Container, typename="container")
        assert value in self._actual, f"`{value}` not found in container `{self._actual}`"
    def is_a(self, value: Type, typename=None):
        """Assert that the actual value is an instance of the given type.

        Args:
            value (Type): The type to check against.
            typename (str | None): The name of the type to use in the error message.

        Raises:
             AssertionError: If the actual value is not an instance of the specified type.
        """
        assert isinstance(value, Type), f"`{value}` is not a type"
        assert isinstance(self._actual, value), f"argument of type `{type(self._actual).__name__}` is not a {typename or value.__name__}"

def athert(value) -> AssertionBuilder:
    """Perform an assertion.

    Args:
        value: The value to perform the assertion on.

    Returns:
        AssertionBuilder: An AssertionBuilder initialized with the given value.
    """
    return AssertionBuilder(value)
