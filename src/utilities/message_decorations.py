from datetime import datetime
from typing import Literal
from utilities.emojis import emojis
from interactions import Color, Message, BaseComponent, Modal, Embed


class Colors:
	DEFAULT = TWM_PURPLE = Color.from_hex("#6600FF")

	RED = BAD = Color.from_hex("#BF2626")
	ORANGE = WARN = WARNING = Color.from_hex("#D9732B")
	YELLOW = Color.from_hex("#BFBF26")
	GREEN = AWESOME = Color.from_hex("#26BF26")
	TEAL = Color.from_hex("#008080")

	BLACK = Color.from_hex("#000000")
	GRAY = GREY = DARKER_WHITE = LIGHTER_BLACK = Color.from_hex("#666666")
	WHITE = Color.from_hex("#000000")

	PURE_RED = Color.from_hex("#FF0000")
	PURE_YELLOW = Color.from_hex("#FFFF00")
	PURE_ORANGE = Color.from_hex("#FF6A00")
	PURE_GREEN = Color.from_hex("#00FF00")
	PASTEL_RED = Color.from_hex("#FF6961")


def timestamp_relative(datetime: datetime):
	return f'<t:{round(datetime.timestamp())}:R>'


async def fancy_message(
    ctx,
    message: str = None,
    edit: bool = False,
    edit_origin: bool = False,
    content: str = None,
    ephemeral=False,
    components: list[BaseComponent] = None,
    color: Color = Colors.DEFAULT,
    embed: Embed = None,
    embeds: list[Embed] = None
):
	if embeds is None:
		embeds = []
	if message:
		embeds.append(Embed(description=message, color=color))
	if embed:
		embeds.append(embed)
	if len(embeds) == 0:
		embeds = None
	if edit_origin:
		return await ctx.edit_origin(content=content, embeds=embeds, components=components)
	if edit and ctx:
		return await ctx.edit(content=content, embeds=embeds, components=components)
	if type(ctx) == Message:
		return await ctx.reply(content=content, embeds=embeds, components=components, ephemeral=ephemeral)
	elif type(ctx) == Modal:
		return await ctx.respond(content=content, embeds=embeds, components=components, ephemeral=ephemeral)

	return await ctx.send(content=content, embeds=embeds, ephemeral=ephemeral, components=components)


def make_progress_bar(position: int, total: int, length: int, shape: Literal["square", "round"] = "square"):
	position = max(0, min(position, total))

	filled_length = int((position / total) * length)

	out = ""

	for i in range(length):
		bar_section = 'middle'

		if i == 0:
			bar_section = 'start'
		elif i == length - 1:
			bar_section = 'end'

		out += emojis['progress_bars'][shape]['filled' if i < filled_length else 'empty'][bar_section]

	return out
