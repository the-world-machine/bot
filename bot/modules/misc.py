import random
from interactions import *
from localization.loc import fnum
from utilities.fancy_send import fancy_message
import aiohttp

class MiscellaneousModule(Extension):
    ''' For "one off" commands. '''

    @slash_command(description='View how many servers the bot is in.')
    async def server_count(self, ctx: SlashContext):
        await fancy_message(ctx, f'[ I am in **{len(self.bot.guilds)}** servers. ]')
        
    @slash_command(description='View the bot\'s status.')
    async def bot_status(self, ctx: SlashContext):
        
        embed = Embed(description="WIP")
        
        embed.add_field('♥️ Average latency:', fnum(self.bot.average_latency))
        await fancy_message(ctx, embed=embed)
        
    @slash_command(description='A random wikipedia article.')
    async def random_wikipedia(self, ctx: SlashContext):
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://en.wikipedia.org/api/rest_v1/page/random/summary') as resp:
                if resp.status == 200:
                    get_search = await resp.json()

                    result = get_search['content_urls']['desktop']['page']

                    await fancy_message(ctx, f'[ [Here]({result}) is your random wikipedia article. It\'s about {get_search["title"]}... I think... ]')

    @slash_command(description='bogus')
    async def amogus(self, ctx: SlashContext):
        await ctx.send(
            'https://media.discordapp.net/attachments/868336598067056690/958829667513667584/1c708022-7898-4121-9968-0f0d24b8f986-1.gif')
        
    
    @slash_command(description='Roll a dice.')
    @slash_option(description='What sided dice to roll.', min_value=1, max_value=9999, name='sides', opt_type=OptionType.INTEGER, required=True)
    @slash_option(description='How many to roll.', min_value=1, max_value=10, name='amount', opt_type=OptionType.INTEGER)
    async def roll(self, ctx: SlashContext, sides: int, amount: int = 1):

        dice = random.randint(1, sides)

        if amount == 1:
            description = f'[ Rolled a **{dice}**. ]'
        else:
            text = ''
            previous_total = 0
            total = 0

            for num in range(amount):

                dice = random.randint(1, sides)

                if num == 0:
                    text = f'**{dice}**'

                    previous_total = dice
                    continue

                text = f'{text}, **{dice}**'

                total = previous_total + dice

                previous_total = total

            description = f'[ Rolled a {text}, totaling at **{total}**. ]'

        embed = Embed(title=f'Rolling d{sides}...', description=description, color=0x8b00cc)
        embed.set_thumbnail('https://cdn.discordapp.com/emojis/1026181557230256128.png?size=96&quality=lossless')

        await ctx.send(embeds=embed)
        
    @slash_command(description="Get a random picture of a cat.")
    async def cat(self, ctx: SlashContext):

        embed = Embed(
            title='You found...',
            color=0x7e00b8
        )

        if random.randint(0, 100) == 67:
            embed.description = 'Niko!'
            embed.set_image(
                'https://cdn.discordapp.com/attachments/1028022857877422120/1075445796113219694/ezgif.com-gif-maker_1.gif')
            embed.set_footer('A 1 in 100 chance! Lucky!')
            return await ctx.send(embed=embed)

        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.thecatapi.com/v1/images/search') as response:
                data = await response.json()

        image = data[0]['url']

        embed.description = 'a cat!'
        embed.set_image(image)
        return await ctx.send(embed=embed)