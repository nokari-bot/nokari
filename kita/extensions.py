from __future__ import annotations

import importlib
import inspect
import logging
import sys
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Optional,
    Tuple,
    Type,
    TypeVar,
    cast,
    get_type_hints,
)

from hikari.events.base_events import Event
from typing_extensions import TypeGuard

from kita.typedefs import (
    CommandCallback,
    EventCallback,
    Extension,
    ExtensionFinalizer,
    ExtensionInitializer,
    IExtensionCallback,
)
from kita.utils import ensure_signature

if TYPE_CHECKING:
    from hikari.api.event_manager import CallbackT, EventT_co

    from kita.command_handlers import GatewayCommandHandler

__all__ = ("initializer", "finalizer", "listener")
T = TypeVar("T")
_LOGGER = logging.getLogger("kita.extensions")


def _is_command(obj: Any) -> TypeGuard[CommandCallback]:
    return (
        getattr(obj, "__is_command__", False)
        and hasattr(obj, "group")
        and hasattr(obj, "command")
    )


def _is_listener(obj: Any) -> TypeGuard[EventCallback]:
    return getattr(obj, "__is_listener__", False)


def _get_default_einit(_mod: Extension) -> ExtensionInitializer:
    @initializer
    def _default_einit(handler: GatewayCommandHandler) -> None:
        for g in _mod.__dict__.values():
            if _is_command(g):
                handler.add_command(g)
            elif _is_listener(g):
                handler.subscribe(g)

    return _default_einit


def _get_default_edel(_mod: Extension) -> ExtensionFinalizer:
    @finalizer
    def _default_edel(handler: GatewayCommandHandler) -> None:
        for g in _mod.__dict__.values():
            if _is_command(g):
                handler.remove_command(g)
            elif _is_listener(g):
                handler.unsubscribe(g)

    return _default_edel


def load_extension(name: str) -> Extension:
    mod = cast(Extension, importlib.import_module(name))

    if not hasattr(mod, "__einit__"):
        _LOGGER.debug(
            "no initializer for %s was found, using the default one...", mod.__name__
        )
        mod.__einit__ = _get_default_einit(mod)

    return mod


def unload_extension(name: str) -> Extension:
    try:
        mod = cast(Extension, sys.modules.pop(name))
    except KeyError as e:
        raise RuntimeError("extension wasn't found.") from e
    else:
        if not hasattr(mod, "__edel__"):
            _LOGGER.debug(
                "no finalizer for %s was found, using the default one...", mod.__name__
            )
            mod.__edel__ = _get_default_edel(mod)
        return mod


def reload_extension(name: str) -> Tuple[Extension, Extension]:
    old = unload_extension(name)
    try:
        new = load_extension(name)
    except Exception as e:
        sys.modules[name] = old  # type: ignore
        raise e from None
    else:
        return old, new


def _get_module(func: IExtensionCallback) -> Optional[Extension]:
    if func.__module__ != __name__ and (mod := inspect.getmodule(func)):
        return cast(Extension, mod)

    return None


def initializer(func: IExtensionCallback) -> ExtensionInitializer:
    func = cast(ExtensionInitializer, func)
    func.__name__ = "__einit__"

    if mod := _get_module(func):
        mod.__einit__ = func

    return func


def finalizer(func: IExtensionCallback) -> ExtensionFinalizer:
    func = cast(ExtensionFinalizer, func)
    func.__name__ = "__edel__"

    if mod := _get_module(func):
        mod.__edel__ = func

    return func


def listener(
    event: Optional[Type[EventT_co]] = None,
) -> Callable[[CallbackT[EventT_co]], EventCallback[EventT_co]]:
    def decorator(func: CallbackT[EventT_co]) -> EventCallback[EventT_co]:
        cast_func = cast("EventCallback[EventT_co]", func)
        nonlocal event
        ensure_signature(cast_func)
        if event is None:
            if (
                param := next(iter(cast_func.__signature__.parameters.values()))
            ) is inspect.Signature.empty:
                raise RuntimeError(
                    "please either provide the event type or annotate the event parameter."
                )

            annotation = param.annotation
            if not (isinstance(annotation, type) and issubclass(annotation, Event)):
                annotation = get_type_hints(func)[param.name]
            event = cast("Type[EventT_co]", annotation)

        cast_func.__etype__ = event
        cast_func.__is_listener__ = True
        return cast_func

    return decorator
