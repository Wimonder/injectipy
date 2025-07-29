from typing import Any, Generic, Type, TypeVar, Union

from typing_extensions import TypeAlias

T = TypeVar("T")
InjectKeyType: TypeAlias = Union[str, Type]


class _TypingMeta(type):
    def __getitem__(cls, item: Any) -> Any:
        return cls(item)


class _Inject(Generic[T]):
    _inject_key: InjectKeyType

    def __init__(
        self,
        inject_key: InjectKeyType,
    ) -> None:
        self._inject_key = inject_key

    def get_inject_key(self) -> InjectKeyType:
        return self._inject_key

    def __call__(self) -> T:
        return self  # type: ignore


class Inject(_Inject, metaclass=_TypingMeta):
    ...


__all__ = ["Inject"]
