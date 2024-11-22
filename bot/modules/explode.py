from interactions import *
from utilities.message_decorations import *
import random
import datetime
import utilities.profile.badge_manager as bm
from utilities.localization import Localization, fnum
from database import UserData

class ExplodeModule(Extension):
    explosion_image = [
        'https://st.depositphotos.com/1001877/4912/i/600/depositphotos_49123283-stock-photo-light-bulb-exploding-concept-of.jpg',
        'https://st4.depositphotos.com/6588418/39209/i/600/depositphotos_392090278-stock-photo-exploding-light-bulb-dark-blue.jpg',
        'https://st.depositphotos.com/1864689/1538/i/600/depositphotos_15388723-stock-photo-light-bulb.jpg',
        'https://st2.depositphotos.com/1001877/5180/i/600/depositphotos_51808361-stock-photo-light-bulb-exploding-concept-of.jpg',
        'https://static7.depositphotos.com/1206476/749/i/600/depositphotos_7492923-stock-photo-broken-light-bulb.jpg',
    ]

    sad_image = 'https://images-ext-1.discordapp.net/external/47E2RmeY6Ro21ig0pkcd3HaYDPel0K8CWf6jumdJzr8/https/i.ibb.co/bKG17c2/image.png'

    last_called = {}

    @slash_command(name='explode', description="💥💥💥💥💥💥💥💥💥")
    async def explode(self, ctx: SlashContext):
        loc = Localization(ctx)
        uid = ctx.user.id
        explosion_amount = (await UserData(uid).fetch()).times_shattered
        if uid in self.last_called:
            elapsed_time = datetime.datetime.now() - self.last_called[uid]
            if elapsed_time.total_seconds() < 20:
                return await fancy_message(ctx, loc.l("explode.cooldown", seconds=round(20 - elapsed_time.total_seconds())), ephemeral=True, color=0xfc0000)

        self.last_called[uid] = datetime.datetime.now()

        random_number = random.randint(1, len(self.explosion_image)) - 1
        random_sadness = random.randint(1, 100)

        sad = False

        if random_sadness == 40:
            sad = True
        if not sad:
            embed = Embed(color=Colors.RED)
        
            dialogues = loc.l("explode.dialogue.why")
            dialogue = random.choice(dialogues)

            if "69" in str(explosion_amount) or "42" in str(explosion_amount):
                dialogue = loc.l("explode.dialogue.sixtyninefourtweny")

            if len(str(explosion_amount)) > 0 and all(char == '9' for char in str(explosion_amount)):
                dialogue = loc.l("explode.dialogue.nineninenineninenine")
            if not dialogue:
                dialogue = "." * random.randint(1, 9)
            
            embed.description = "-# "+dialogue
            embed.set_image(url=self.explosion_image[random_number])
            embed.set_footer(loc.l("explode.info", amount=fnum(explosion_amount, ctx.locale)))
        else:
            embed = Embed(title='...')
            embed.set_image(url=self.sad_image)
            embed.set_footer(loc.l("explode.YouKilledNiko"))

        if not sad:
            await bm.increment_value(ctx, 'times_shattered', 1, ctx.author)

        await ctx.send(embed=embed)
