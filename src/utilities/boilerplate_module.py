from interactions import (
	Extension,
	OptionType,
	SlashContext,
	contexts,
	integration_types,
	slash_command,
	slash_option,
)

from utilities.message_decorations import fancy_message


class _Module(Extension):

	@slash_command(description="This is a Boilerplate Command.")
	@slash_option(
		name="option_name",
		description="This is a Boilerplate Option.",
		opt_type=OptionType.STRING,
	)
	@integration_types(guild=True, user=True)
	@contexts(bot_dm=True)
	async def hello(self, ctx: SlashContext, option_name: str):
		return await fancy_message(ctx, "Hello, " + option_name)
