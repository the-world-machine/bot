import psutil
import random
import aiohttp
import platform
from datetime import datetime, timezone
from utilities.misc import get_git_hash
from utilities.emojis import emojis, make_url
from utilities.localization import Localization, fnum, ftime
from utilities.message_decorations import Colors, fancy_message
from interactions import Embed, EmbedAttachment, Extension, Message, OptionType, SlashContext, contexts, integration_types, slash_command, slash_option

try:
	commit_hash = get_git_hash()
	print(f"Found git hash: {commit_hash}")
except Exception as e:
	print(f"Error retrieving git hash: {e}")


class MiscellaneousCommands(Extension):

	@slash_command(description='About the bot (ping, stats)')
	@slash_option(
	    description="Whether you want the response to be visible for others in the channel",
	    name="public",
	    opt_type=OptionType.BOOLEAN
	)
	@integration_types(guild=True, user=True)
	@contexts(bot_dm=True)
	async def about(self, ctx: SlashContext, public: bool = False):
		loc = Localization(ctx.locale)
		checkpoint = datetime.now(timezone.utc)  # timezone :aware: date
		_ = await fancy_message(ctx, loc.l("general.loading_hint"), ephemeral=not public)
		if not isinstance(_, Message):
			return
		checkpoint2 = datetime.fromtimestamp(_.created_at.timestamp()) - checkpoint  # time it took to reply
		checkpoint = checkpoint - ctx.id.created_at  # time it took to receive the command
		host = f"{platform.system()} {platform.release()} ({platform.architecture()[0]})"
		total_servers = len(ctx.client.guilds)
		team = ctx.client.app.team
		members = [ctx.client.app.owner]
		if team:
			members = [member.user for member in team.members]
		embed = Embed(
		    description=loc.l(
		        "misc.stats.layout", owners=" & ".join(map(str, members)), description=ctx.client.app.description
		    ),
		    color=Colors.DEFAULT
		)
		embed.add_field(
		    loc.l("misc.stats.names.avg_ping"),
		    loc.l("misc.stats.values.time", sec=fnum(ctx.client.latency, ctx.locale)),
		    inline=True
		)
		embed.add_field(
		    loc.l("misc.stats.names.latency"),
		    loc.l("misc.stats.values.time", sec=fnum(checkpoint.microseconds / 1e6, ctx.locale)) + " / " +
		    loc.l("misc.stats.values.time", sec=fnum(checkpoint2.microseconds / 1e6, ctx.locale)),
		    inline=True
		)
		embed.add_field(
		    loc.l("misc.stats.names.cpu_usg"),
		    loc.l("misc.stats.values.percent", num=round(psutil.cpu_percent())),
		    inline=True
		)
		embed.add_field(
		    loc.l("misc.stats.names.mem_usg"),
		    loc.l("misc.stats.values.percent", num=round(psutil.virtual_memory().percent)),
		    inline=True
		)
		embed.add_field(loc.l("misc.stats.names.server_count"), total_servers, inline=True)
		embed.add_field(
		    loc.l("misc.stats.names.commit_hash"),
		    commit_hash if commit_hash else loc.l("misc.status.values.failed_commit_hash"),
		    inline=True
		)
		embed.add_field(
		    loc.l("misc.stats.names.uptime"), ftime(datetime.now() - ctx.client.start_time, ctx.locale), inline=True
		)
		# embed.add_field(loc.l("misc.stats.names.user_installs"),
		#                 len(ctx.client.app.users)) # NONEXISTENT
		embed.add_field(loc.l("misc.stats.names.host"), host, inline=True)

		return await ctx.edit(embeds=[embed])

	@slash_command(description='A random wikipedia article')
	@slash_option(
	    description="Whether you want the response to be visible for others in the channel",
	    name="public",
	    opt_type=OptionType.BOOLEAN
	)
	@integration_types(guild=True, user=True)
	@contexts(bot_dm=True)
	async def random_wikipedia(self, ctx: SlashContext, public: bool = False):
		loc = Localization(ctx.locale)
		await ctx.defer(ephemeral=not public)
		async with aiohttp.ClientSession() as session:
			async with session.get(f'https://en.wikipedia.org/api/rest_v1/page/random/summary') as resp:
				if resp.status == 200:
					get_search = await resp.json()

					await fancy_message(
					    ctx,
					    loc.l(
					        "misc.wikipedia",
					        link=get_search['content_urls']['desktop']['page'],
					        title=get_search["title"]
					    ),
					    edit=True
					)

	@slash_command(description='bogus')
	@slash_option(
	    description="Whether you want the response to be visible for others in the channel",
	    name="public",
	    opt_type=OptionType.BOOLEAN
	)
	@integration_types(guild=True, user=True)
	@contexts(bot_dm=True)
	async def amogus(self, ctx: SlashContext, public: bool = False):
		await ctx.send(
		    'https://media.discordapp.net/attachments/868336598067056690/958829667513667584/1c708022-7898-4121-9968-0f0d24b8f986-1.gif',
		    ephemeral=not public
		)

	@slash_command(description='Roll an imaginary dice')
	@slash_option(
	    description='What sided dice to roll',
	    min_value=1,
	    max_value=9999,
	    name='sides',
	    opt_type=OptionType.INTEGER,
	    required=True
	)
	@slash_option(
	    description='How many times to roll it', min_value=1, max_value=10, name='amount', opt_type=OptionType.INTEGER
	)
	@slash_option(
	    description="Whether you want the response to be visible for others in the channel",
	    name="public",
	    opt_type=OptionType.BOOLEAN
	)
	@integration_types(guild=True, user=True)
	@contexts(bot_dm=True)
	async def roll(self, ctx: SlashContext, sides: int, amount: int = 1, public: bool = False):
		loc = Localization(ctx.locale)

		rolls = [random.randint(1, sides) for _ in range(amount)]

		result = ", ".join(
		    map(str, rolls)
		) if len(rolls) > 1 else rolls[0]  # TODO: replace .join with a function(to be written) from localisation module
		description = loc.l("misc.roll.desc", result=result)

		if len(rolls) > 1:
			description += "\n\n" + loc.l("misc.roll.multi", total=sum(rolls))

		await ctx.send(
		    embeds=Embed(
		        color=Colors.DEFAULT,
		        thumbnail=EmbedAttachment(url=make_url(emojis["treasures"]["die"])),
		        title=loc.l("misc.roll.title", amount=amount, sides=sides),
		        description=description
		    ),
		    ephemeral=not public
		)

	@slash_command(description="Show a picture of a kitty or a cat or a Catto")
	@slash_option(
	    description="Whether you want the response to be visible for others in the channel",
	    name="public",
	    opt_type=OptionType.BOOLEAN
	)
	@integration_types(guild=True, user=True)
	@contexts(bot_dm=True)
	async def cat(self, ctx: SlashContext, public: bool = False):
		loc = Localization(ctx.locale)
		embed = Embed(title=loc.l("misc.miaou.title"), color=Colors.DEFAULT)

		if random.randint(0, 100) == 30 + 6 + 14:
			embed.description = loc.l("misc.miaou.finding.noik")
			embed.set_image(
			    'https://cdn.discordapp.com/attachments/1028022857877422120/1075445796113219694/ezgif.com-gif-maker_1.gif'
			)
			embed.set_footer(loc.l("misc.miaou.finding.footer"))
			return await ctx.send(embed=embed)

		async with aiohttp.ClientSession() as session:
			async with session.get('https://api.thecatapi.com/v1/images/search') as response:
				data = await response.json()

		image = data[0]['url']

		embed.description = loc.l("misc.miaou.finding.cat")
		embed.set_image(image)
		return await ctx.send(embed=embed, ephemeral=not public)
