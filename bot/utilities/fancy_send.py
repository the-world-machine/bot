from interactions import Embed, Message, BaseComponent, Modal
from enum import Enum


class FColor(Enum):
    RED = 0xfc0000
    GREY = 0x666666
    GREEN = 0x00fc00


async def fancy_embed(text: str, color: int = 0x8b00cc):
    return Embed(description=text, color=color)


async def fancy_message(ctx, message: str, color: int = 0x8b00cc, ephemeral=False, components: list[BaseComponent] = []):
    embed = await fancy_embed(message, color)

    if type(ctx) == Message:
        return await ctx.reply(embed=embed, components=components, ephemeral=ephemeral)
    elif type(ctx) == Modal:
        return await ctx.respond(embed=embed, components=components, ephemeral=ephemeral)
    
    return await ctx.send(embed=embed, ephemeral=ephemeral, components=components)
