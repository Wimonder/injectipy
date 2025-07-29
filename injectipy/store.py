import inspect
from dataclasses import dataclass
from typing import Any, Callable, Type, TypeVar, Union, overload

from typing_extensions import TypeAlias

from injectipy.models.inject import Inject

_ParamNameType: TypeAlias = str
_ParamType: TypeAlias = Type
StoreKeyType = Union[_ParamNameType, _ParamType]
StoreResolverType = Callable[..., Any]


@dataclass(frozen=True)
class _StoreResolverWithArgs:
    resolver: StoreResolverType
    evaluate_once: bool


_StoreValueType = Union[_StoreResolverWithArgs, Any]

T = TypeVar("T")


class InjectipyStore:
    _instance: "InjectipyStore"
    _registry: dict[StoreKeyType, _StoreValueType]
    _cache: dict[StoreKeyType, Any]

    def __new__(cls):
        if not hasattr(cls, "_instance") or cls._instance is None:
            cls._instance = super(InjectipyStore, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self._registry = {}
        self._cache = {}

    def register_resolver(
        self,
        key: StoreKeyType,
        resolver: StoreResolverType,
        *,
        evaluate_once: bool = False,
    ):
        self._raise_if_key_already_registered(key)
        self._validate_resolver_signature(key, resolver)
        self._registry[key] = _StoreResolverWithArgs(resolver, evaluate_once)

    def _validate_resolver_signature(self, resolver_key: StoreKeyType, resolver: StoreResolverType):
        resolver_signature = inspect.signature(resolver)
        resolver_parameters = resolver_signature.parameters
        for param in resolver_parameters.values():
            if param.kind not in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            ):
                raise ValueError(
                    f"Resolver {resolver_key} has unsupported parameter kind {param.kind} for parameter {param.name}"
                )

            if param.default is not inspect.Parameter.empty and isinstance(param.default, Inject):
                if param.default.get_inject_key() not in self._registry:
                    raise ValueError(
                        f"Resolver {resolver_key} has unresolved parameter {param.name} with inject key"
                        f" {param.default.get_inject_key()}"
                    )
            elif param.name not in self._registry:
                raise ValueError(f"Resolver {resolver_key} has unresolved parameter {param.name}")

    def register_value(self, key: StoreKeyType, value: Any):
        self._raise_if_key_already_registered(key)
        self._registry[key] = value
        self._cache[key] = value

    def _raise_if_key_already_registered(self, key: StoreKeyType):
        if key in self._registry:
            raise ValueError(f"Key {key} already registered")

    def __setitem__(self, key: Any) -> None:
        raise NotImplementedError("Use register_resolver or register_value instead")  # noqa E501

    @overload
    def __getitem__(self, key: _ParamNameType) -> Any:
        ...

    @overload
    def __getitem__(self, key: Type[T]) -> T:
        ...

    def __getitem__(self, key: Any) -> Any:
        if key in self._cache:
            return self._cache[key]
        if key in self._registry:
            value_or_resolver_with_args = self._registry[key]

            result: Any
            if isinstance(value_or_resolver_with_args, _StoreResolverWithArgs):
                resolver_with_args = value_or_resolver_with_args
                result = self._resolve(resolver_with_args.resolver)
                if resolver_with_args.evaluate_once:
                    self._cache[key] = result
            else:
                result = value_or_resolver_with_args

            return result
        raise KeyError(f"Key {key} not found in the store")

    def _resolve(
        self,
        resolver: StoreResolverType,
    ) -> Any:
        resolver_signature = inspect.signature(resolver)
        resolver_parameters = resolver_signature.parameters
        resolver_args: dict[str, Any] = {}

        for param_name, param in resolver_parameters.items():
            if param.default is not inspect.Parameter.empty and isinstance(param.default, Inject):
                try:
                    resolver_args[param_name] = self[param.default.get_inject_key()]
                    continue
                except KeyError:
                    pass
            else:
                try:
                    resolver_args[param_name] = self[param_name]
                    continue
                except KeyError:
                    pass

        return resolver(**resolver_args)


injectipy_store = InjectipyStore()


__all__ = ["InjectipyStore", "injectipy_store"]
