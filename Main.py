import asyncio

from interactions import *
from interactions.api.events import MessageCreate, MemberAdd, Ready, GuildJoin
import interactions.ext.prefixed_commands as prefixed_commands

from database import Database
from load_data import *
import load_commands
import os
import random
import Utilities.profile_viewer as view
import Utilities.badge_manager as badge_manager
import Data.capsule_characters as chars
from Localization.Localization import load_languages

from Utilities.ShopData import fetch_shop_data

print('\nStarting The World Machine... 1/4')
intents = Intents.DEFAULT | \
          Intents.MESSAGE_CONTENT | \
          Intents.MESSAGES

client = Client(
    intents=intents,
    disable_dm_commands=True,
    send_command_tracebacks=False
)

prefixed_commands.setup(client, default_prefix='*')

print("\nLoading Commands... 2/4")
load_commands.load_commands(client)

print('\nLoading Additional Extensions... 3/4')
client.load_extension('database')
print('Successfully loaded database.')
client.load_extension("interactions.ext.sentry", token=load_config("SENTRY-TOKEN"))  # Debugging and errors.
client.load_extension("Utilities.dev_commands")


async def pick_avatar():
    get_avatars = os.listdir('Images/Profile Pictures')
    random_avatar = random.choice(get_avatars)

    avatar = File('Images/Profile Pictures/' + random_avatar)

    await client.user.edit(avatar=avatar)


@listen(Ready)
async def on_ready():
    print("\nFinalizing... 4/4")

    await client.change_presence(status=Status.ONLINE,
                                 activity=Activity(name=load_config("MOTD"), type=ActivityType.PLAYING))
    chars.get_characters()
    await view.load_badges()

    if client.user.id == 1015629604536463421:
        await pick_avatar()
    else:
        try:
            await client.user.edit(avatar=File('Images/Unstable.png'))
        except:
            pass
        
    load_languages()
    
    print('Successfully loaded languages.')

    print("\n----------------------------------------")
    print("\nThe World Machine is ready!\n\n")


@listen(MessageCreate)
async def on_message(event: MessageCreate):
    if event.message.author.bot:
        return

    await badge_manager.increment_value(event.message, 'times_messaged', event.message.author)


client.start(load_config("Token"))

@listen(MemberAdd)
async def on_guild_join(event: MemberAdd):
    
    print('someone joined the server')


    await event.guild.system_channel.send('welcome ' + event.member.mention)