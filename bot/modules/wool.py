import random
import asyncio
import dataclasses
import database as db
from interactions import *
from utilities.emojis import emojis
from utilities.localization import fnum
from datetime import datetime, timedelta
from utilities.message_decorations import Colors, fancy_message



@dataclasses.dataclass
class Slot:
    emoji: int
    value: float


class WoolModule(Extension):


    current_limit = 0

    wool_finds = [
        {'message': 'and they despise you today... Too bad...', 'amount': 'negative_major', 'chance': 70},
        {'message': 'and they\'re happy with you! Praise be The World Machine!', 'amount': 'positive_normal', 'chance': 30},
        {'message': 'and they see you\'re truly a devoted follower. Praise be The World Machine!', 'amount': 'positive_major', 'chance': 5},
        {'message': 'but they saw your misdeed the other day.', 'amount': 'negative_minimum', 'chance': 40},
        {'message': 'but they aren\'t happy with you today.', 'amount': 'negative_normal', 'chance': 20},
        {'message': 'and they see you\'re doing okay.', 'amount': 'positive_minimum', 'chance': 100}
    ]
    
    wool_values = {
        'positive_minimum': [500, 3000],
        'positive_normal': [1000, 3_000],
        'positive_major': [10_000, 50_000],
        
        'negative_minimum': [-10, -50],
        'negative_normal': [-100, -300],
        'negative_major': [-500, -1000]
    }

    @slash_command(description='All things to do with wool.')
    async def wool(self, ctx: SlashContext):
        pass

    @wool.subcommand(sub_cmd_description='Check your balance.')
    @slash_option(description='Check someone else\'s balance...', name='user', required=True, opt_type=OptionType.USER)
    async def balance(self, ctx: SlashContext, user: User = None):

        if user is None:
            user = ctx.user
            
        user_data: db.UserData = await db.UserData(user.id).fetch()

        wool: int = user_data.wool

        await fancy_message(
            ctx,
            f"[ **{user.username}** has {emojis['icons']['wool']}**{fnum(wool)}**. ]",
        )
        
    @wool.subcommand(sub_cmd_description='Give someone your wool.')
    @slash_option(description='Who to give your wool to...', name='user', required=True, opt_type=OptionType.USER)
    @slash_option(description='The amount to give, as long as you can afford it.', name='amount', required=True, opt_type=OptionType.INTEGER, min_value=-1)
    async def give(self, ctx: SlashContext, user: User, amount: int):
        
        if user.id == ctx.author.id:
            return await fancy_message(ctx, '[ No. ]', color=Colors.BAD)
        
        if user.bot:
            return await fancy_message(ctx, '[ Please do not. ]', Colors.BAD)
        
        this_user: db.UserData = await db.UserData(ctx.author.id).fetch()
        target_user: db.UserData = await db.UserData(user.id).fetch()
        
        if this_user.wool < amount:
            return await fancy_message(ctx, '[ You cannot give this amount of wool because you don\'t have it! ]', color=Colors.BAD)
            
        await this_user.manage_wool(-amount)
        await target_user.manage_wool(amount)

        if amount > 0:
            await fancy_message(
                ctx,
                f"{ctx.author.mention} gave away {emojis['icons']['wool']}{fnum(amount)} to {user.mention}, how generous!",
            )
        elif amount == 0:
            await fancy_message(
                ctx,
                f"{ctx.author.mention} gave away {emojis['icons']['wool']}{fnum(amount)} to {user.mention}, not very generous!",
            )
        else:
            await fancy_message(
                ctx,
                f"{ctx.author.mention} stole a single piece of wool from {user.mention}, why!?",
            )

    @wool.subcommand()
    async def daily(self, ctx: SlashContext):
        '''Command has been renamed to /pray.'''
        
        await self.pray(ctx)

    @slash_command()
    async def pray(self, ctx: SlashContext):
        '''Pray to The World Machine.'''

        user_data: db.UserData = await db.UserData(ctx.author.id).fetch()
        last_reset_time = user_data.daily_wool_timestamp

        now = datetime.now()

        if now < last_reset_time:
           time_unix = last_reset_time.timestamp()
           return await fancy_message(ctx, f"[ You've already prayed in the past 24 hours. You can pray again <t:{int(time_unix)}:R>. ]", ephemeral=True, color=Colors.BAD)

        # reset the limit if it is a new day
        if now >= last_reset_time:
            reset_time = datetime.combine(now.date(), now.time()) + timedelta(days=1)
            await user_data.update(daily_wool_timestamp=reset_time)

        random.shuffle(self.wool_finds)

        response = self.wool_finds[0]

        number = random.randint(0, 100)
        
        amount = 0
        message = ''
        
        for wool_find in self.wool_finds:
            if number <= wool_find['chance']:
                amount = wool_find['amount']
                message = wool_find['message']
                break
            
        response = f'You prayed to The World Machine...'
        
        amount = self.wool_values[amount]
        amount = int(random.uniform(amount[0], amount[1]))
        
        if amount > 0:
            value = f"You got {fnum(amount)} wool!"
            color = Colors.GREEN
        else:
            value = f"You lost {fnum(abs(amount))} wool..."
            color = Colors.BAD

        await user_data.update(wool=user_data.wool + amount)

        await ctx.send(embed=Embed(
            title='Pray',
            description=f'{response}\n{message}',
            footer=EmbedFooter(text=value),
            color=color
        ))
        
    slots = [
        Slot(1290847840397951047, 0.1),
        Slot(1290847480237391955, 0.15),
        Slot(1290847574315499530, 0.2),
        Slot(1290848009315287090, 0.5),
        Slot(1290847840397951047, 0.1),
        Slot(1290847480237391955, 0.15),
        Slot(1290847574315499530, 0.2),
        Slot(1290848009315287090, 0.5),
        Slot(1290847890545180682, 0.8),
        Slot(1290847718566137979, 1.0),
        Slot(1290847647372017786, 1.12),
        Slot(1290847782906761277, 1.5),
        
        Slot(1291071376517501119, -0.2),
        Slot(1291071376517501119, -0.2),
        Slot(1291071376517501119, -0.2)
    ]

    slot_value = 10
    
    @wool.subcommand()
    async def gamble_help(self, ctx: SlashContext):
        '''Read how the gamble command works.'''
        
        await ctx.defer()
        
        text = f'''## Slot Machine
        Gamble any amount of wool as long as you can afford it.
        Here is the following slots you can roll and their value:
        '''
        
        existing_slots = []
        
        for slot in self.slots:
            
            
            if slot.emoji != 1291071376517501119:
                
                if slot.emoji in existing_slots:
                    continue
                
                existing_slots.append(slot.emoji)
                
                text += f'\n- <:icon:{slot.emoji}> **{int(slot.value * 100)} points**'
            
        text += f'\n\n- <:penguin:1291071376517501119> **-20 point penalty.**\n\nPoints are added up and them multiplied by your bet. You also get double points when you hit a jackpot.'

        await fancy_message(ctx, text)
        
    @wool.subcommand()
    @slash_option(description='The amount of wool to gamble.', name='amount', required=True, opt_type=OptionType.INTEGER, min_value=100)
    async def gamble(self, ctx: SlashContext, amount: int):
        '''Waste your wool away with slots. Totally not a scheme by Magpie.'''
        
        await ctx.defer()
        
        user_data: db.UserData = await db.UserData(ctx.author.id).fetch()
        
        if user_data.wool < amount:
            return await fancy_message(ctx, f'[ You don\'t have enough wool to gamble that amount. ]', ephemeral=True, color=Colors.BAD)
        
        await user_data.update(wool=user_data.wool - amount)
        
        random.Random()
        
        slots = []
        
        for i in range(3):
            selected_slots = self.slots.copy()
            random.shuffle(selected_slots)
            
            slots.append(selected_slots)
                
        def generate_column(column: list[list[Slot]], i: int):
            
            def image(slot: Slot):
                return f'<:slot:{slot.emoji}>'
            
            slot_a = 0
            slot_b = 0
            slot_c = 0
            
            if i == len(column) - 1:
                slot_c = column[0]
            else:
                slot_c = column[i + 1]
                
            if i == 0:
                slot_a = column[-1]
            else:
                slot_a = column[i - 1]
                
            slot_b = column[i]
            
            return image(slot_a), image(slot_b), image(slot_c)
        
        slot_images: list[list] = []
        
        def generate_embed(index: int, column: int, slot_images: list[list]):
            
            def grab_slot(i: int):
                column = generate_column(slots[i], index)
                
                if column is None:
                    raise Exception('You fucked up axii')
                
                try:
                    del slot_images[i]
                except:
                    pass
                
                slot_images.insert(i, list(column))
                
                return slot_images
            
            if column == -1:
                grab_slot(0)
                grab_slot(1)
                slot_images = grab_slot(2)
            else:
                slot_images = grab_slot(column)
                
            ticker = ''
            
            for row in range(3):
                for col in range(3):
                
                    # slot_images are columns
                    
                    c = slot_images[col]
                    
                    s = f'{c[row]}'
                    
                    if col == 2:
                        if row == 1:
                            ticker += f'{s} ⇦\n'
                        else:
                            ticker += f'{s}\n'
                    elif col == 0:
                        ticker += f'## {s} ┋ '
                    else:
                        ticker += f'{s} ┋ '
            
            return Embed(
                description=f"## Slot Machine\n\n{ctx.author.mention} has bet {emojis['icons']['wool']}**{fnum(amount)}**.\n{ticker}",
                color=Colors.DEFAULT,
            )
            
        msg = await ctx.send(embed=generate_embed(0, -1, slot_images))
        
        slot_a_value = 0
        slot_b_value = 0
        slot_c_value = 0
        
        for i in range(4):

            await msg.edit(embed=generate_embed(i, 0, slot_images))
            
            slot = slots[0][i]

            slot_a_value = slot.value
            
            await asyncio.sleep(1)
                
        for i in range(4):
            
            await msg.edit(embed=generate_embed(i, 1, slot_images))
            
            slot = slots[1][i]
            
            slot_b_value = slot.value
            
            await asyncio.sleep(1)
                
        result_embed: Embed = None
        
        last_roll = random.randint(4, 5)
                
        for i in range(last_roll):
            
            if i == last_roll - 1:
                await asyncio.sleep(2)
            
            result_embed = generate_embed(i, 2, slot_images)
            
            await msg.edit(embed=result_embed)
            
            slot = slots[2][i]
            
            slot_c_value = slot.value
            
            await asyncio.sleep(1)

        if slot_a_value == slot_b_value == slot_c_value:
            additional_scoring = 100
        else:
            additional_scoring = 1
                
        win_amount = int(
            (slot_a_value + slot_b_value + slot_c_value) * additional_scoring * (amount / 2)
        )
        
        if win_amount < 0:
            win_amount = 0
            
        await user_data.manage_wool(win_amount)
        
        if win_amount > 0:
            if additional_scoring > 1:
                result_embed.color = Colors.PURE_YELLOW
                result_embed.set_footer(
                    text=f"JACKPOT! 🎉 {ctx.author.username} won back {fnum(abs(win_amount))} wool!"
                )
            else:
                result_embed.color = Colors.PURE_GREEN
                result_embed.set_footer(
                    text=f"{ctx.author.username} won back {fnum(abs(win_amount))} wool!"
                )
        else:
            result_embed.color=Colors.PURE_RED
            result_embed.set_footer(text=f'{ctx.author.username} lost it all... better luck next time!')
        
        await msg.edit(embed=result_embed)
        