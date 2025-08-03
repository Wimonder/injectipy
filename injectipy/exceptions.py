"""Custom exception hierarchy for injectipy."""


class InjectipyError(Exception):
    """Base exception for all injectipy errors."""

    pass


class DependencyError(InjectipyError):
    """Base class for dependency-related errors.

    This covers all errors related to dependency registration, resolution,
    and injection failures.
    """

    pass


class DependencyNotFoundError(DependencyError):
    """Raised when a dependency cannot be resolved."""

    def __init__(
        self,
        key: str | type,
        *,
        function_name: str | None = None,
        module_name: str | None = None,
        available_keys: list[str | type] | None = None,
        parameter_name: str | None = None,
    ):
        self.key = key
        self.available_keys = available_keys or []

        # Simple error message
        message = f"Dependency '{key}' not found"
        if function_name:
            message += f" in function '{function_name}'"

        super().__init__(message)


class CircularDependencyError(DependencyError):
    """Raised when circular dependencies are detected."""

    def __init__(self, dependency_chain: list[str | type], new_key: str | type, conflicting_key: str | type):
        chain_str = " -> ".join(str(key) for key in dependency_chain)
        message = f"Circular dependency: {chain_str} -> {new_key}"
        super().__init__(message)


class DuplicateRegistrationError(DependencyError):
    """Raised when attempting to register a key that already exists."""

    def __init__(self, key: str | type, existing_type: str = "unknown"):
        message = f"Key '{key}' is already registered as {existing_type}"
        super().__init__(message)


class ParameterValidationError(DependencyError):
    """Raised when resolver parameters have unsupported types."""

    def __init__(self, resolver_key: str | type, parameter_name: str, parameter_kind: str):
        message = f"Resolver '{resolver_key}' parameter '{parameter_name}' has unsupported kind '{parameter_kind}'"
        super().__init__(message)


class InjectionError(InjectipyError):
    """Base class for errors that occur during injection (runtime).

    This covers errors that happen when the @inject decorator is applied
    or when injected functions are called.
    """

    pass


class PositionalOnlyInjectionError(InjectionError):
    """Raised when trying to inject into positional-only parameters."""

    def __init__(
        self, function_name: str, parameter_name: str, dependency_key: str | type, module_name: str | None = None
    ):
        message = (
            f"Cannot inject '{dependency_key}' into positional-only parameter '{parameter_name}' in '{function_name}'"
        )
        super().__init__(message)


class AsyncDependencyError(InjectionError):
    """Raised when attempting to use @inject with async dependencies."""

    def __init__(
        self,
        function_name: str,
        parameter_name: str,
        dependency_key: str | type,
        module_name: str | None = None,
    ):
        self.function_name = function_name
        self.parameter_name = parameter_name
        self.dependency_key = dependency_key
        self.module_name = module_name

        module_info = f" in module {module_name}" if module_name else ""
        super().__init__(
            f"Cannot use @inject with async dependency '{dependency_key}' "
            f"for parameter '{parameter_name}' in function '{function_name}'{module_info}. "
            f"Use @ainject instead for async dependency injection."
        )


class StoreOperationError(InjectipyError):
    """Base class for errors in store operations.

    This covers errors in the DependencyScope that aren't dependency-related,
    such as invalid operations or store state issues.
    """

    pass


class InvalidStoreOperationError(StoreOperationError):
    """Raised when an invalid operation is attempted on the store."""

    def __init__(self, operation: str, reason: str):
        message = f"Invalid operation '{operation}': {reason}"
        super().__init__(message)


__all__ = [
    "InjectipyError",
    "DependencyError",
    "DependencyNotFoundError",
    "CircularDependencyError",
    "DuplicateRegistrationError",
    "ParameterValidationError",
    "InjectionError",
    "PositionalOnlyInjectionError",
    "AsyncDependencyError",
    "StoreOperationError",
    "InvalidStoreOperationError",
]
