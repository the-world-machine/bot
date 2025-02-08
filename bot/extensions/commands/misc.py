import random
import aiohttp
import platform
import psutil
import platform
from interactions import *
from utilities.emojis import emojis, make_url
from utilities.localization import Localization, fnum, ftime
from utilities.message_decorations import Colors, fancy_message
from datetime import datetime
from utilities.misc import get_git_hash

try:
	commit_hash = get_git_hash()
	print(f"Found git hash: {commit_hash}")
except Exception as e:
	print(f"Error retrieving git hash: {e}")


class MiscellaneousCommands(Extension):

	@slash_command(description='View various statistics about the bot')
	async def stats(self, ctx: SlashContext):
		await ctx.defer()
		loc = Localization(ctx.locale)

		host = f"{platform.system()} {platform.release()} ({platform.architecture()[0]})"
		total_servers = len(ctx.client.guilds)

		embed = Embed(description=loc.l("misc.stats.owner", name=ctx.client.owner.username), color=Colors.DEFAULT)

		embed.add_field(loc.l("misc.stats.names.avg_ping"), loc.l("misc.stats.values.time", sec=fnum(ctx.client.latency, ctx.locale)), inline=True)
		embed.add_field(loc.l("misc.stats.names.cpu_usg"), loc.l("misc.stats.values.percent", num=round(psutil.cpu_percent())), inline=True)
		embed.add_field(loc.l("misc.stats.names.mem_usg"), loc.l("misc.stats.values.percent", num=round(psutil.virtual_memory().percent)), inline=True)
		embed.add_field(loc.l("misc.stats.names.commit_hash"), commit_hash if commit_hash else loc.l("misc.status.values.failed_commit_hash"), inline=True)
		embed.add_field(loc.l("misc.stats.names.server_count"), total_servers, inline=True)
		embed.add_field(loc.l("misc.stats.names.uptime"), ftime(datetime.now() - ctx.client.start_time, ctx.locale), inline=True)
		#embed.add_field(loc.l("misc.stats.names.user_installs"),
		#                len(ctx.client.app.users)) # NONEXISTENT
		#embed.add_field(loc.l("misc.stats.names.host"),
		#                host, inline=True)

		return await ctx.edit(embeds=[embed])

	@slash_command(description='A random wikipedia article')
	async def random_wikipedia(self, ctx: SlashContext):
		loc = Localization(ctx.locale)
		async with aiohttp.ClientSession() as session:
			async with session.get(f'https://en.wikipedia.org/api/rest_v1/page/random/summary') as resp:
				if resp.status == 200:
					get_search = await resp.json()

					await fancy_message(ctx, loc.l("misc.wikipedia", link=get_search['content_urls']['desktop']['page'], title=get_search["title"]))

	@slash_command(description='bogus')
	async def amogus(self, ctx: SlashContext):
		await ctx.send('https://media.discordapp.net/attachments/868336598067056690/958829667513667584/1c708022-7898-4121-9968-0f0d24b8f986-1.gif')

	@slash_command(description='Roll an imaginary dice')
	@slash_option(description='What sided dice to roll', min_value=1, max_value=9999, name='sides', opt_type=OptionType.INTEGER, required=True)
	@slash_option(description='How many times to roll it', min_value=1, max_value=10, name='amount', opt_type=OptionType.INTEGER)
	async def roll(self, ctx: SlashContext, sides: int, amount: int = 1):
		loc = Localization(ctx.locale)

		rolls = [random.randint(1, sides) for _ in range(amount)]

		result = ", ".join(map(str, rolls)) if len(rolls) > 1 else rolls[0] # TODO: replace .join with a function(to be written) from localisation module
		description = loc.l("misc.roll.desc", result=result)

		if len(rolls) > 1:
			description += "\n\n" + loc.l("misc.roll.multi", total=sum(rolls))

		await ctx.send(
		    embeds=Embed(color=Colors.DEFAULT, thumbnail=make_url(emojis["treasures"]["die"]), title=loc.l("misc.roll.title", amount=amount, sides=sides), description=description)
		)

	@slash_command(description="Show a picture of a kitty or a cat or a Catto")
	async def cat(self, ctx: SlashContext):
		loc = Localization(ctx.locale)
		embed = Embed(title=loc.l("misc.miaou.title"), color=Colors.DEFAULT)

		if random.randint(0, 100) == 30 + 6 + 14:
			embed.description = loc.l("misc.miaou.finding.noik")
			embed.set_image('https://cdn.discordapp.com/attachments/1028022857877422120/1075445796113219694/ezgif.com-gif-maker_1.gif')
			embed.set_footer(loc.l("misc.miaou.finding.footer"))
			return await ctx.send(embed=embed)

		async with aiohttp.ClientSession() as session:
			async with session.get('https://api.thecatapi.com/v1/images/search') as response:
				data = await response.json()

		image = data[0]['url']

		embed.description = loc.l("misc.miaou.finding.cat")
		embed.set_image(image)
		return await ctx.send(embed=embed)
