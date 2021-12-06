from __future__ import annotations

import typing as t
from inspect import Signature

from hikari.channels import ChannelType
from hikari.commands import CommandChoice, CommandOption, OptionType
from hikari.undefined import UNDEFINED, UndefinedOr

from kita.typedefs import Callable, ICommandCallback
from kita.utils import ensure_options, ensure_signature

__all__ = ("with_option",)


def with_option(
    type_: OptionType,
    name: str,
    description: str,
    choices: UndefinedOr[t.Sequence[CommandChoice]] = UNDEFINED,
    channel_types: UndefinedOr[t.Sequence[t.Union[ChannelType, int]]] = UNDEFINED,
) -> t.Callable[[Callable], ICommandCallback]:
    def decorator(func: Callable) -> ICommandCallback:
        cast_func = t.cast(ICommandCallback, func)
        ensure_signature(cast_func)
        ensure_options(cast_func)
        if name not in cast_func.__code__.co_varnames:
            return cast_func

        cast_func.options.insert(
            0,
            CommandOption(
                type=type_,
                name=name,
                description=description,
                is_required=cast_func.__signature__.parameters[name].default
                is Signature.empty,
                choices=choices or None,
                channel_types=channel_types or None,
            ),
        )
        return cast_func

    return decorator
