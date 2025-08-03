import psutil
import platform
from datetime import datetime
from utilities.misc import get_git_hash
from utilities.localization import Localization, fnum, ftime
from utilities.message_decorations import Colors, fancy_message
from interactions import Embed, Extension, Message, OptionType, SlashContext, contexts, integration_types, slash_command, slash_option


try:
	commit_hash = get_git_hash()
	print(f"Found git hash: {commit_hash}")
except Exception as e:
	print(f"Error retrieving git hash: {e}")
	
class AboutCommand(Extension):
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
		checkpoint = datetime.now()  # timezone :aware: date
		_ = await fancy_message(ctx, loc.l("global.loading_hint"), ephemeral=not public)
		if not isinstance(_, Message):
			return
		checkpoint2 = datetime.fromtimestamp(_.created_at.timestamp()) - checkpoint  # time it took to reply
		checkpoint = checkpoint - datetime.fromtimestamp(
		    ctx.id.created_at.timestamp()
		)  # time it took to receive the command
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