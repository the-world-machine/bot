from .state import command_ as state_cmd
from .facepic_selector import init_facepic_selector, handle_facepic_selection
from interactions import Extension, SlashContext, contexts, integration_types, slash_command
from .create import command as create_cmd, handle_components as create_handle_components, handle_update_text_modal as create_handle_update_text_modal, handle_edit_modal as create_handle_edit_modal


class TextboxCommands(Extension):

	@slash_command(
	    name="textbox",
	    description="Commands related to Textboxes",
	)
	@integration_types(guild=True, user=True)
	@contexts(bot_dm=True)
	async def textbox(self, ctx: SlashContext):
		"""Base command for textboxes."""
		pass

	create = textbox.subcommand(
	    sub_cmd_name="create",
	    sub_cmd_description="Make a textbox or a GIF dialogue between characters, like in OneShot"
	)(create_cmd)

	handle_components = create_handle_components
	handle_update_text_modal = create_handle_update_text_modal
	handle_edit_modal = create_handle_edit_modal

	init_facepic_selector = init_facepic_selector
	handle_facepic_selection = handle_facepic_selection

	state = textbox.subcommand(
	    sub_cmd_name="state",
	    sub_cmd_description="Debugging command for textboxes",
	)(state_cmd)
