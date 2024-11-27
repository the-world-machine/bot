from interactions import *
from interactions.api.events import MessageCreate
from utilities.dev_commands import execute_dev_command
from utilities.loc_commands import execute_loc_command
from utilities.message_decorations import *
from utilities.emojis import emojis

class MarkerCommandsModule(Extension):
  @listen(MessageCreate)
  async def on_message_create(self, event: MessageCreate):
    res = await execute_dev_command(event.message)
    if not res:
      await execute_loc_command(event.message)