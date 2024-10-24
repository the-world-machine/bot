from interactions import Embed, Message, BaseComponent, Modal
from enum import Enum


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
