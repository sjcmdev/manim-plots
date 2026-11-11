"""Versioned parameter values, descriptors and explicit binding polls."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Generic, TypeVar, cast, overload

import numpy as np
from numpy.typing import ArrayLike

T = TypeVar("T")


def _snapshot[T](value: T) -> T:
    if isinstance(value, np.ndarray):
        array = value.copy()
        array.flags.writeable = False
        return cast(T, array)
    if isinstance(value, (list, tuple)):
        numbers = np.asarray(value)
        if np.issubdtype(numbers.dtype, np.number) or numbers.dtype == np.bool_:
            numbers = numbers.copy()
            numbers.flags.writeable = False
            return cast(T, numbers)
    return value


def _same(left: object, right: object) -> bool:
    if isinstance(left, np.ndarray) or isinstance(right, np.ndarray):
        a, b = cast(ArrayLike, left), cast(ArrayLike, right)
        try:
            return bool(np.array_equal(a, b, equal_nan=True))
        except TypeError:
            return bool(np.array_equal(a, b))
    if left is right:
        return True
    if (
        isinstance(left, (float, np.floating))
        and isinstance(right, (float, np.floating))
        and np.isnan(left)
        and np.isnan(right)
    ):
        return True
    return bool(left == right)


# Property accessors need a module-scoped TypeVar for get_type_hints on 3.12/3.13.
class Parameter(Generic[T]):  # noqa: UP046
    """Hold an immutable value and a version counter with an optional binding.

    Parameters
    ----------
    value
        Initial value, validated and snapshotted on construction.
    name
        Public parameter name.
    validate
        Optional conversion or validation function, whose exceptions propagate.
    """

    def __init__(
        self,
        value: object,
        *,
        name: str,
        validate: Callable[[Any], T] | None = None,
    ) -> None:
        self._name = name
        self._validate = validate
        self._value = self._checked(value)
        self._version = 0
        self._source: object | None = None
        self._reader: Callable[[], Any] | None = None
        self._foreign = False
        self._token: int | None = None

    def _checked(self, value: object) -> T:
        converted = cast(T, value) if self._validate is None else self._validate(value)
        return _snapshot(converted)

    @property
    def name(self) -> str:
        """Return the parameter's public name."""
        return self._name

    @property
    def value(self) -> T:
        """Return the last stored value without polling its binding."""
        return self._value

    @value.setter
    def value(self, value: object) -> None:
        checked = self._checked(value)
        self.unbind()
        self._value = checked
        self._version += 1

    @property
    def tracker(self) -> object | None:
        """Return the bound source, or None when unbound."""
        return self._source

    @property
    def version(self) -> int:
        """Return the current version without polling."""
        return self._version

    def bind(self, source: object) -> None:
        """Bind a foreign get_value source or a zero-argument callable.

        Parameters
        ----------
        source
            Object exposing a callable get_value, or another callable.

        Raises
        ------
        TypeError
            If source supplies neither calling convention.
        """
        reader = getattr(source, "get_value", None)
        foreign = callable(reader)
        if not foreign:
            if not callable(source):
                raise TypeError("source must expose get_value() or be callable")
            reader = source
        self._source = source
        self._reader = reader
        self._foreign = foreign
        self._token = None

    def unbind(self) -> None:
        """Remove the binding and keep the last stored value and version."""
        self._source = None
        self._reader = None
        self._foreign = False
        self._token = None

    def poll(self, token: int | None = None) -> int:
        """Read a binding, comparing foreign snapshots or dirtying once per token.

        Parameters
        ----------
        token
            Synchronisation token, required for a callable binding.

        Returns
        -------
        int
            Version after polling.

        Raises
        ------
        ValueError
            If a callable binding is polled without a token.
        """
        if self._reader is None:
            return self._version
        if not self._foreign:
            if token is None:
                raise ValueError("token is required for a callable binding")
            if token == self._token:
                return self._version
        checked = self._checked(self._reader())
        if not self._foreign or not _same(self._value, checked):
            self._version += 1
        self._value = checked
        self._token = token
        return self._version


class Param(Generic[T]):  # noqa: UP046
    """Describe a lazily created, per-instance Parameter attribute.

    Parameters
    ----------
    default
        Initial value independently snapshotted for every instance.
    validate
        Optional conversion or validation function, determining the value type.
    """

    def __init__(
        self, default: object, *, validate: Callable[[Any], T] | None = None
    ) -> None:
        self._default = default
        self._validate = validate
        self._name = ""
        self._storage_key = "__manim_plots_parameter_"

    def __set_name__(self, owner: type[object], name: str) -> None:
        self._name = name
        self._storage_key = f"__manim_plots_parameter_{name}"

    @overload
    def __get__(
        self, instance: None, owner: type[object] | None = None
    ) -> Param[T]: ...

    @overload
    def __get__(
        self, instance: object, owner: type[object] | None = None
    ) -> Parameter[T]: ...

    def __get__(
        self,
        instance: object | None,
        owner: type[object] | None = None,
    ) -> Param[T] | Parameter[T]:
        if instance is None:
            return self
        key = self._storage_key
        storage = vars(instance)
        if key not in storage:
            storage[key] = Parameter(
                self._default, name=self._name, validate=self._validate
            )
        return cast(Parameter[T], storage[key])

    def __set__(self, instance: object, value: object) -> None:
        self.__get__(instance).value = value
