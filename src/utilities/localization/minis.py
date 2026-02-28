import asyncio
from typing import Literal

from utilities.database.schemas import UserData
from utilities.localization.localization import Localization

limits: dict[str, int] = {
	"treasure.tip": 5,
	"nikogotchi.tipnvalid": 5,
	"nikogotchi.found.renamenote": 5,
	"wool.transfer.errors.note_nuf": -1,
	"textbox.errors.ephemeral_warnote": 9,
	"settings.errors.channel_lost_warn": -1,
	"wool.transfer.to.bot.notefirmation": 10,
	"settings.welcome.enabled.default_tip": 15,
	"settings.welcome.editor.disabled_note": -1,
	"nikogotchi.treasured.dialogues.senote": 25,
}


async def put_mini(
	loc: Localization,
	message: str,
	user_id: str | int | None = None,
	type: Literal["note", "tip", "warn", "err"] = "note",
	pre: str = "",
	markdown: bool = True,
) -> str:
	if user_id:
		user_data: UserData = await UserData(str(user_id)).fetch()
		reacher = user_data.minis_shown.get(message, 0)
		if limits.get(message) != -1 and limits.get(message, 0) <= reacher:
			return ""
		asyncio.create_task(user_data.minis_shown.increment_key(message))
	name: str = await loc.format(loc.l(f"generic.minis.{type}"))
	msg: str = await loc.format(loc.l(message))
	return f"{pre}{'-# ' if markdown else ''}{name} {msg}"
