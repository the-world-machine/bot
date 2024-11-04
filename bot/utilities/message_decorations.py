from interactions import Embed, Message, BaseComponent, Modal
from enum import Enum
from typing import Literal

from data.emojis import emojis


class FColor(Enum):
    RED = 0xfc0000
    GREY = 0x666666
    GREEN = 0x00fc00


def fancy_embed(text: str, color: int = 0x8b00cc):
    return Embed(description=text, color=color)


async def fancy_message(ctx, message: str | None = None, color: int = 0x8b00cc, ephemeral=False, components: list[BaseComponent] = [], embed: Embed | None = None, embeds: list[Embed] | None = None):
    if embed == None:
        embed = fancy_embed(message, color)
    if embeds == None:
        embeds = [embed]

    if type(ctx) == Message:
        return await ctx.reply(embeds=embeds, components=components, ephemeral=ephemeral)
    elif type(ctx) == Modal:
        return await ctx.respond(embeds=embeds, components=components, ephemeral=ephemeral)
    
    return await ctx.send(embeds=embeds, ephemeral=ephemeral, components=components)

def generate_progress_bar(value: int, progress_bar_length: int, shape: Literal["square", "round"] = "square"):
            out = ""
            
            for i in range(progress_bar_length):
                bar_section = 'middle'
                if i == 0:
                    bar_section = 'start'
                elif i == progress_bar_length - 1:
                    bar_section = 'end'

                if i < value:
                    out += emojis['progress_bars'][shape]['filled'][bar_section]
                else:
                    out += emojis['progress_bars'][shape]['empty'][bar_section]

            return out