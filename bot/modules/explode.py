from interactions import *
from utilities.message_decorations import *
import random
import datetime
import utilities.profile.badge_manager as bm
from data.localization import Localization, fnum


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
        loc = Localization(ctx.locale)
        user_id = ctx.user.id

        if user_id in self.last_called:
            elapsed_time = datetime.datetime.now() - self.last_called[user_id]
            if elapsed_time.total_seconds() < 20:
                return await fancy_message(ctx, loc.l("explode.cooldown", seconds=round(20 - elapsed_time.total_seconds(), ndigits=0)), ephemeral=True, color=0xfc0000)

        self.last_called[user_id] = datetime.datetime.now()

        with open('bot/data/explosions.txt', 'r') as f:
            try:
                explosion_amount = int(f.read())
            except ValueError:
                explosion_amount = 99999

        random_number = random.randint(1, len(self.explosion_image)) - 1
        random_sadness = random.randint(1, 100)

        sad = False

        if random_sadness == 40:
            sad = True
        dialogue 
        if not sad:
            embed = Embed(description=' ')
            
            sexy_amounts = [69, 420, 42069, 69420]
            
            if explosion_amount in sexy_amounts:
                dialogue = loc.l("explode.sixtyninefourtweny")
                
            if explosion_amount >= 99999:
                explosion_amount = 99999
                dialogue = loc.l("explode.nineninenineninenine")
                           
            explosion_amount = ctx.author_id # TODO: figure this out

            embed.set_image(url=self.explosion_image[random_number])
            embed.set_footer(loc.l("explode.info", amount=fnum(explosion_amount, ctx.locale)))
        else:
            embed = Embed(title='...')
            embed.set_image(url=self.sad_image)
            embed.set_footer(loc.l("explode.YouKilledNiko"))

        with open('bot/data/explosions.txt', 'w') as f:
            try:
                f.write(str(explosion_amount + 1))
            except ValueError:
                f.write(explosion_amount)

        if not sad:
            await bm.increment_value(ctx, 'times_shattered', 1, ctx.author)

        await ctx.send(embed=embed)
