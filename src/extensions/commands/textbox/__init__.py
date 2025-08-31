from .state import command as state_cmd
from interactions import ContextType, Extension, IntegrationType, SlashContext, slash_command
from .create import command as create_cmd, handle_components as create_handle_components, handle_update_text_modal as create_handle_update_text_modal, handle_edit_modal as create_handle_edit_modal


class TextboxCommands(Extension):

	@slash_command(
				name="textbox",
				description="Commands related to Textboxes",
				integration_types=[IntegrationType.GUILD_INSTALL, IntegrationType.USER_INSTALL],
				contexts=[ContextType.BOT_DM],
		)
	async def textbox(self, ctx: SlashContext):
		"""Base command for textboxes."""
		pass
	create = textbox.subcommand(
			sub_cmd_name="create",
			sub_cmd_description="Make a OneShot textbox"
	)(create_cmd)
	handle_components = create_handle_components
	handle_update_text_modal = create_handle_update_text_modal
	handle_edit_modal = create_handle_edit_modal
	state = textbox.subcommand(
	    sub_cmd_name="state",
	    sub_cmd_description="Debugging command for textboxes",
	)(state_cmd)

	def __init__(self, client):
		super().__init__()
		print("TextboxCommands Extension loaded.")


def setup(client):
	TextboxCommands(client)
