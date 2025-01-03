from interactions import *
from utilities.message_decorations import *
import utilities.profile.badge_manager as badge_manager
from utilities.emojis import emojis


class _Module(Extension):

	@slash_command(description="This is a Boilerplate Command.")
	@slash_option(name="option_name",
	              description="This is a Boilerplate Option.",
	              opt_type=OptionType.STRING)
	async def hello(self, ctx: SlashContext, option_name: str):
		await fancy_message(ctx, "Hello, " + option_name)
