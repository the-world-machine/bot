from datetime import datetime
from utilities.emojis import emojis, make_emoji_cdn_url
from typing import Any, Dict, Iterable, List, Literal
from interactions import Color, Message, BaseComponent, Embed, ModalContext
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
	from utilities.textbox.facepics import Face
else:
	try:
		from utilities.textbox.facepics import Face
	except ImportError:
		Face = None


class Colors:
	DEFAULT = TWM_PURPLE = Color.from_hex("#6600FF")

	RED = BAD = Color.from_hex("#BF2626")
	ORANGE = WARN = WARNING = Color.from_hex("#D9732B")
	YELLOW = Color.from_hex("#BFBF26")
	GREEN = AWESOME = Color.from_hex("#26BF26")
	SHOP = TEAL = Color.from_hex("#008080")

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


def fancy_message(
    ctx,
    message: str | None = None,
    edit: bool = False,
    edit_origin: bool = False,
    content: str | None = None,
    ephemeral=False,
    components: Iterable[Iterable[BaseComponent | dict[Any, Any]]] | Iterable[BaseComponent | dict[Any, Any]] |
    BaseComponent | dict[Any, Any] | None = None,
    color: Color = Colors.DEFAULT,
    facepic: Optional[Face] = None,  # only emoji supported
    embed: Embed | Dict | None = None,
    embeds: List[Embed | Dict] | None = None
):
	if embeds is None:
		embeds = []
	if message:
		emb = Embed(description=message, color=color)
		if facepic and facepic.icon:
			emb.set_thumbnail(make_emoji_cdn_url(emoji_id=facepic.icon, size=4096))
		embeds.append(emb)
	if embed:
		embeds.append(embed)
	if len(embeds) == 0:
		embeds = None
	if edit_origin:
		return ctx.edit_origin(content=content, embeds=embeds, components=components)
	if edit and ctx:
		return ctx.edit(content=content, embeds=embeds, components=components)
	if type(ctx) == Message:
		kwargs = { 'content': content, 'embeds': embeds, 'components': components, 'ephemeral': ephemeral}
		return ctx.reply(**kwargs)
	elif type(ctx) == ModalContext:
		return ctx.respond(content=content, embeds=embeds, components=components, ephemeral=ephemeral)

	return ctx.send(content=content, embeds=embeds, ephemeral=ephemeral, components=components)


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
