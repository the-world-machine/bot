import random

from interactions import *

from data.emojis import emojis
from utilities.message_decorations import *


class ShippingModule(Extension):

    @slash_command(description="Ship two people together.")
    @slash_option(name="who", description="First person. Can be a user.", opt_type=OptionType.STRING, required=True)
    @slash_option(argument_name="whomst", name="with", description="Second person. Can be a user.", opt_type=OptionType.STRING, required=True)
    async def ship(self, ctx: SlashContext, who: str, whomst: str):
        
        if '<' in who:
            parsed_id = who.strip('<@>')
            user = await self.bot.fetch_user(int(parsed_id))

            who = user.display_name
        if '<' in whomst:
            parsed_id = whomst.strip('<@>')
            user = await self.bot.fetch_user(int(parsed_id))

            whomst = user.display_name
        if who == ctx.author.display_name and who == whomst:
            return await fancy_message(ctx, "[ Do you need a hug? ]", color=0xff0000, ephemeral=True)

        seed = len(who) + len(whomst)
        random.seed(seed)

        love_percentage = random.randint(0, 100)

        name_a_part = who[0 : len(who) // 2] # Get the first half of the first name.
        name_b_part = whomst[-len(whomst) // 2 :] # Get the last half of the second name.
        
        name = name_a_part + name_b_part # Combine the names together.

        emoji = '💖'
        description = ''

        if love_percentage == 100:
            emoji = '💛'
            description = 'Perfect compatibility.'
        if love_percentage < 100:
            emoji = '💖'
            description = 'In love.'
        if love_percentage < 70:
            emoji = '❤'
            description = 'There\'s interest!'
        if love_percentage <= 50:
            emoji = '❓'
            description = 'Potentially?'
        if love_percentage < 30:
            emoji = '❌'
            description = 'No interest.'
        if love_percentage < 10:
            emoji = '💔'
            description = 'Not at all.'

        l_length = list("🤍🤍🤍🤍🤍")

        calc_length = round((love_percentage / 100) * len(l_length))

        i = 0
        for _ in l_length:
            if i < calc_length:
                l_length[i] = '❤'
            i += 1

        length = "".join(l_length)

        embed = Embed(
            title=name,
            description=f'{name} has a compatibility of: **{love_percentage}%** {emoji}\n{length}',
            color=0xd72d42
        )

        embed.set_footer(text=description)

        await ctx.send(embeds=embed)