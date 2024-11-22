from typing import Literal
from utilities.emojis import emojis
from interactions import Color, Message, BaseComponent, Modal, Embed


class Colors:
    PURE_RED = Color.from_hex("FF0000")
    RED = BAD = Color.from_hex("bf2626")
    GRAY = GREY = DARKER_WHITE = LIGHTER_BLACK = Color.from_hex("666666")
    GREEN = Color.from_hex("26bf26")
    WARN = WARNING = ORANGE = Color.from_hex("d9732b")
    PURE_ORANGE = Color.from_hex("ff6a00")
    PURE_GREEN = Color.from_hex("00ff00")
    DEFAULT = TWM_PURPLE = Color.from_hex("6600ff")
    
async def fancy_message(ctx,
                        message: str = None, 
                        edit: bool = False,
                        content: str = None,
                        ephemeral=False, 
                        components: list[BaseComponent] = [],
                        color: Color = Colors.DEFAULT,
                        embed: Embed = None, 
                        embeds: list[Embed] = None):
    if embeds is None:
        embeds = []
    if message:
        embeds.append(Embed(description=message, color=color))
    if embed:
        embeds.append(embed)
    
    if edit and ctx:
        return await ctx.edit(content=content, embeds=embeds if embeds else [], components=components if components else [])
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
