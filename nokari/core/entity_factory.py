from __future__ import annotations

import typing

from hikari import Snowflake, presences, snowflakes, undefined
from hikari.impl.entity_factory import EntityFactoryImpl
from hikari.internal import data_binding

from kita.utils import find

if typing.TYPE_CHECKING:
    from nokari.core.bot import Nokari

__all__ = ("EntityFactory",)


class EntityFactory(EntityFactoryImpl):
    _app: Nokari

    def deserialize_member_presence(
        self,
        payload: data_binding.JSONObject,
        *,
        guild_id: undefined.UndefinedOr[snowflakes.Snowflake] = undefined.UNDEFINED,
    ) -> presences.MemberPresence:
        user_id = Snowflake(payload["user"]["id"])
        if spotify := find(
            lambda x: x.get("name") == "Spotify" and "sync_id" in x,
            payload["activities"],
        ):
            self._app._sync_ids[user_id] = spotify["sync_id"]
        else:
            self._app._sync_ids.pop(user_id, None)

        return super().deserialize_member_presence(payload, guild_id=guild_id)
