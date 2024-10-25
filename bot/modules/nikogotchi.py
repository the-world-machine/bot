from dataclasses import dataclass
import json
import random
from datetime import datetime
import re
import time
from typing import Dict, List, Union

from utilities.emojis import emojis
from dateutil import relativedelta
from interactions import *
from interactions.api.events import Component

from utilities.nikogotchi_metadata import *
from localization.loc import Localization, fnum
from utilities.shop.fetch_items import fetch_treasure
from database import NikogotchiData, StatUpdate, UserData, Nikogotchi
from utilities.fancy_send import *

def generate_progress_bar(value: int, progress_bar_length: int, emojis=emojis):
        progress_bar_l = []
        
        for i in range(progress_bar_length):
            bar_section = 'middle'
            if i == 0:
                bar_section = 'start'
            elif i == progress_bar_length - 1:
                bar_section = 'end'

            if i < value:
                bar_fill = emojis[f'progress_filled_{bar_section}']
            else:
                bar_fill = emojis[f'progress_empty_{bar_section}']

            progress_bar_l.append(bar_fill)

        return ''.join(progress_bar_l)

@dataclass
class TreasureSeekResults:
    found_treasure: Dict[str,int]
    total_treasure: int
    hours_spent: int

class NikogotchiModule(Extension):
    
    async def convert_nikogotchi(self, uid: int):
        data: NikogotchiData = await NikogotchiData(uid).fetch()
        new_data: Nikogotchi = await Nikogotchi(uid).fetch()
        
        ndata: dict = data.data
        nid: str = ndata['original_name']
        
        nid = nid.lower().replace(' ', '_')
        
        await data.update(data={})
        
        await new_data.update(
            nid=nid,
            name=ndata['name'],
            last_interacted=data.last_interacted,
            hatched=data.hatched,
            status=ndata['status'],
            health=ndata['health'],
            hunger=ndata['hunger'],
            happiness=ndata['attention'],
            pancakes=data.pancakes,
            golden_pancakes=data.golden_pancakes,
            glitched_pancakes=data.glitched_pancakes,
            rarity=ndata['rarity'],
            available=data.nikogotchi_available
        )
        
        if ndata['immortal']:
            await new_data.level_up(30)
        
        await self.save_nikogotchi(new_data, uid)
        return new_data

    async def get_nikogotchi(self, uid: int) -> Union[Nikogotchi, None]:
        data: Nikogotchi = await Nikogotchi(uid).fetch()
        
        if data.status > -1:
            return data
        else:
            return None
        
    async def save_nikogotchi(self, nikogotchi: Nikogotchi, uid: int):
        nikogotchi_data: Nikogotchi = await Nikogotchi(uid).fetch()

        data = nikogotchi.__dict__

        await nikogotchi_data.update(**data)
        
    async def delete_nikogotchi(self, uid: int):
        
        nikogotchi_data = await Nikogotchi(uid).fetch()
        
        await nikogotchi_data.update(available=False, status=-1, nid="?")
    
    def nikogotchi_buttons(self, owner_id: int, locale: str):
        prefix = 'action_'
        suffix = f'_{owner_id}'
        
        loc = Localization(locale)

        return [
            Button(
                style=ButtonStyle.SUCCESS,
                label=loc.l('nikogotchi.components.pet'),
                custom_id=f'{prefix}pet{suffix}'
            ),
            Button(
                style=ButtonStyle.SUCCESS,
                label=loc.l('nikogotchi.components.clean'),
                custom_id=f'{prefix}clean{suffix}'
            ),
            Button(
                style=ButtonStyle.PRIMARY,
                label=loc.l('nikogotchi.components.find_treasure'),
                custom_id=f'{prefix}findtreasure{suffix}'
            ),
            Button(
                style=ButtonStyle.GREY,
                emoji=emojis["refresh"],
                custom_id=f'{prefix}refresh{suffix}'
            ), 
            Button(
                style=ButtonStyle.DANGER,
                label='X',
                custom_id=f'{prefix}exit{suffix}'
            )
        ]

    async def get_nikogotchi_age(self, uid: int):
        nikogotchi_data: Nikogotchi = await Nikogotchi(uid).fetch()

        return relativedelta.relativedelta(datetime.now(), nikogotchi_data.hatched)

    async def get_main_embeds(self, ctx: InteractionContext, age: relativedelta.relativedelta, dialogue: str,
                                        treasure_seek_results: TreasureSeekResults | None, n: Nikogotchi, updated_stats: List[StatUpdate] | None):

        metadata = await fetch_nikogotchi_metadata(n.nid)
        loc = Localization(ctx.locale)

        age = loc.l('nikogotchi.age', years=age.years, months=age.months, days=age.days)

        pb_length = 5

        health_value = round((n.health / int(n.max_health)) * pb_length)
        energy_value = round((n.energy / 5) * pb_length)
        hunger_value = round((n.hunger / int(n.max_hunger)) * pb_length)
        happiness_value = round((n.happiness / int(n.max_happiness)) * pb_length)
        cleanliness_value = round((n.cleanliness / int(n.max_cleanliness)) * pb_length)
        
        health_progress_bar = generate_progress_bar(health_value, pb_length)
        hunger_progress_bar = generate_progress_bar(hunger_value, pb_length)
        happiness_progress_bar = generate_progress_bar(happiness_value, pb_length)
        cleanliness_progress_bar = generate_progress_bar(cleanliness_value, pb_length)
        energy_progress_bar = generate_progress_bar(energy_value, pb_length)

        nikogotchi_status = loc.l('nikogotchi.status.normal')

        if n.happiness < 20:
            nikogotchi_status = loc.l('nikogotchi.status.pet', name=n.name)

        if n.cleanliness < 20:
            nikogotchi_status = loc.l('nikogotchi.status.dirty', name=n.name)

        if n.hunger < 20:
            nikogotchi_status = loc.l('nikogotchi.status.hungry', name=n.name)
        treasure_looking=''
        if n.status == 3:
            nikogotchi_status = loc.l('nikogotchi.status.treasure', name=n.name)
            treasure_looking = f'  •  🎒 {loc.l("nikogotchi.status.treasuring_time", hours=round((datetime.now() - n.started_finding_treasure_at).total_seconds() / 3600))}'

        treasure_found = ''
        if treasure_seek_results != None:
            treasures = ''
            total = 0
            for (tid, amount) in treasure_seek_results.found_treasure.items():
                total+=amount
                treasures += loc.l('treasure.item', amount=amount, icon=emojis[f"treasure_{tid}"], name=loc.l(f"items.treasures.{tid}.name"))+"\n"

            treasure_found = loc.l('nikogotchi.treasured.message', treasures=treasures, total=total, hours=treasure_seek_results.hours_spent)
        
        levelled_up_stats = ''
        
        if updated_stats:
            for stat in updated_stats:
                levelled_up_stats += loc.l("nikogotchi.levelupped.stat", 
                        icon=stat.icon, 
                        old_value=stat.old_value, 
                        new_value=stat.new_value, 
                        increase=(stat.new_value - stat.old_value))+"\n"
                
        if n.health < min(20, n.max_health * 0.20):
            nikogotchi_status = loc.l('nikogotchi.status.danger', name=n.name)
            
        # crafting embeds - - -
        embeds = []
        N_embed = Embed( # nikogotchi embed
            title=n.name,
            description=''+
            f"❤️  {health_progress_bar} ({int(n.health)} / {int(n.max_health)})\n"+
            f'⚡  {energy_progress_bar} ({int(n.energy)} / 5)\n'+
            '\n'+
            f'🍴  {hunger_progress_bar} ({int(n.hunger)} / {int(n.max_hunger)})\n'+
            f'🫂  {happiness_progress_bar} ({n.happiness} / {int(n.max_happiness)})\n'+
            f'🧽  {cleanliness_progress_bar} ({int(n.cleanliness)} / {int(n.max_cleanliness)})\n'+
            '\n'+
            f'🗡️  {int(n.attack)}  •  🛡️  {int(n.defense)}{treasure_looking}  •  ⏰  {age}\n'+
            '\n'+
            f'{loc.l("nikogotchi.status.template", status=nikogotchi_status)}',
            footer=dialogue,
            color=0x8b00cc
        )
        N_embed.set_thumbnail(metadata.image_url)
        
        
        if levelled_up_stats:
            L_embed = Embed( # level up embed
                title=loc.l("nikogotchi.levelupped.title", level=n.level),
                description=loc.l("nikogotchi.levelupped.message", stats=levelled_up_stats),
                color=0x8b00cc
            ) 
            embeds.append(L_embed)

        if treasure_found:
            T_embed = Embed( # treasures embed
                title=loc.l("nikogotchi.treasured.title"),
                description=treasure_found,
                color=0x8b00cc
            )
            embeds.append(T_embed)
        embeds.append(N_embed)
        return embeds

    @slash_command(description="All things about your Nikogotchi!")
    @integration_types(guild=True, user=True)
    async def nikogotchi(self, ctx: SlashContext):
        pass

    @nikogotchi.subcommand(sub_cmd_description="Check out your Nikogotchi!")
    async def check(self, ctx: SlashContext):

        uid = ctx.author.id
        loc = Localization(ctx.locale)

        old_nikogotchi: NikogotchiData = await NikogotchiData(uid).fetch()
        nikogotchi: Nikogotchi
        if old_nikogotchi.data:
            nikogotchi = await self.convert_nikogotchi(uid)
        else:
            nikogotchi = await Nikogotchi(uid).fetch()

        metadata = await fetch_nikogotchi_metadata(nikogotchi.nid)
        if nikogotchi.status > -1 and metadata:
            msg = await fancy_message(ctx, loc.l('nikogotchi.loading'))
        else:
            if not metadata and nikogotchi.nid !="?":
                
                buttons = [
                    Button(style=ButtonStyle.GREEN, label=loc.l('nikogotchi.other.error.buttons.rotate'), custom_id=f'rotate'),
                    Button(style=ButtonStyle.GRAY, label=loc.l('nikogotchi.other.error.buttons.send_away'), custom_id=f'_rehome')
                ]

                await fancy_message(ctx, loc.l('nikogotchi.other.error.description', id=nikogotchi.nid), color=0xff0000, ephemeral=True, components=buttons)
                button_ctx = (await self.bot.wait_for_component(components=buttons)).ctx
                
                custom_id = button_ctx.custom_id

                if custom_id == '_rehome':
                    await self.delete_nikogotchi(ctx.author.id)
                    embed = fancy_embed(loc.l('nikogotchi.other.send_away.success', name=nikogotchi.name))
                    return await ctx.edit(embed=embed, components=[])
                else:
                    nikogotchi.available = True
            if not nikogotchi.available:
                return await fancy_message(ctx, loc.l('nikogotchi.invalid'), ephemeral=True, color=0xff0000)
            selected_nikogotchi: NikogotchiMetadata = await pick_random_nikogotchi(nikogotchi.rarity)

            await nikogotchi.update(
                nid = selected_nikogotchi.name,
                name = loc.l(f'nikogotchi.name.{selected_nikogotchi.name}'),

                level = 0,
                health = 50,
                energy = 5,
                hunger = 50,
                cleanliness = 50,
                happiness = 50,

                attack = 5,
                defense = 2,

                max_health = 50,
                max_hunger = 50,
                max_cleanliness = 50,
                max_happiness = 50,
                
                last_interacted = datetime.now(),
                hatched = datetime.now(),
                started_finding_treasure_at = None,
                available = False,
                status = 2
            )

            nikogotchi = await self.get_nikogotchi(ctx.author.id)
 
            hatched_embed = Embed(
                title=loc.l('nikogotchi.found.title', name=nikogotchi.name),
                color=0x8b00cc,
                description=loc.l('nikogotchi.found.description')
            )

            hatched_embed.set_thumbnail(url=selected_nikogotchi.image_url)

            buttons = [
                Button(style=ButtonStyle.GREEN, label=loc.l('nikogotchi.other.renaming.button'), custom_id=f'rename {ctx.author.id}'),
                Button(style=ButtonStyle.GRAY, label=loc.l('general.buttons._continue'), custom_id=f'continue {ctx.author.id}')
            ]
            await ctx.send(embed=hatched_embed, components=buttons, ephemeral=True, edit_origin=True)
            button: Component = await self.bot.wait_for_component(components=buttons)
            button_ctx = button.ctx

            custom_id = button_ctx.custom_id
            if custom_id == f'rename {ctx.author.id}':
                await self.init_rename_flow(button_ctx, nikogotchi.name, True)
            else:
                await button_ctx.defer(edit_origin=True)
                
            await self.save_nikogotchi(nikogotchi, ctx.author.id)

        await self.nikogotchi_interaction(ctx)

    async def calculate_treasure_seek(self, uid: int, hours_taken: int) -> TreasureSeekResults | None:
        user_data: UserData = await UserData(uid).fetch()

        treasures_found = {}
        user_treasures = user_data.owned_treasures
        total_treasures = 0
        for _ in range(hours_taken):
            value = random.randint(0, 5000)
            treasure_id = ''

            if value > 4900:
                treasure_id = random.choice(["die", "sun", "clover"])
            elif value > 3500:
                treasure_id = random.choice(["amber", "pen", "card"]) # TODO: store rarity in DB
            elif value > 100:
                treasure_id = random.choice(["journal", "bottle", "shirt"])
            
            if treasure_id:
                treasures_found.setdefault(treasure_id, 0)
                treasures_found[treasure_id] += 1
                user_treasures.setdefault(treasure_id, 0)
                user_treasures[treasure_id] += 1
                total_treasures += 1
                
        if total_treasures == 0:
            return None
        
        await user_data.update(owned_treasures=user_treasures)
        return TreasureSeekResults(treasures_found, hours_taken, total_treasures)

    r_nikogotchi_interaction = re.compile(r'action_(feed|pet|clean|findtreasure|refresh|callback|exit)_(\d+)$')
    @component_callback(r_nikogotchi_interaction)
    async def nikogotchi_interaction(self, ctx: ComponentContext):
        
        try:
            await ctx.defer(edit_origin=True)
            
            match = self.r_nikogotchi_interaction.match(ctx.custom_id)
        
            if not match:
                return
            
            custom_id = match.group(1)
            uid = int(match.group(2))
            
            if ctx.author.id != uid:
                return
        except:
            uid = ctx.author.id
            custom_id = 'refresh'
            
        if custom_id == 'exit':
            await ctx.delete()
            
        loc = Localization(ctx.locale)
            
        nikogotchi = await self.get_nikogotchi(uid)

        if nikogotchi is None:
            return await ctx.edit_origin(
            embed=Embed(
                title=loc.l('nikogotchi.error_title'),
                description=loc.l('nikogotchi.error_desc')
            ),
            
            components=[
                Button(
                    emoji=emojis["refresh"],
                    custom_id=f'action_refresh_{ctx.author.id}',
                    style=ButtonStyle.GREY)
            ]
        )

        last_interacted = nikogotchi.last_interacted

        current_time = datetime.now()

        time_difference = (current_time - last_interacted).total_seconds() / 3600
        
        age = await self.get_nikogotchi_age(int(ctx.author.id))

        await nikogotchi.update(last_interacted=current_time)

        modifier = 1

        if nikogotchi.status == 3:
            modifier = 2.5
            
        random_stat_modifier = random.uniform(1, 1.50)

        nikogotchi.hunger = round(max(0, nikogotchi.hunger - time_difference * random_stat_modifier * modifier))
        
        random_stat_modifier = random.uniform(1, 1.50)
        
        nikogotchi.happiness = round(max(0, nikogotchi.happiness - time_difference * random_stat_modifier * modifier))
        
        random_stat_modifier = random.uniform(1, 1.50)
        
        nikogotchi.cleanliness = round(max(0, nikogotchi.cleanliness - time_difference * random_stat_modifier * modifier))

        if nikogotchi.hunger <= 0 or nikogotchi.happiness <= 0 or nikogotchi.cleanliness <= 0:
            nikogotchi.health = round(nikogotchi.health - time_difference * 0.5)

        if nikogotchi.health <= 0:
            age = loc.l('nikogotchi.age', years=age.years, months=age.months, days=age.days)
            embed = Embed(
                title=loc.l('nikogotchi.died.title', name=nikogotchi.name),
                color=0x696969,
                description=loc.l('nikogotchi.died.description', name=nikogotchi.name, age=age, time_difference=fnum(time_difference))
            )
            
            await self.delete_nikogotchi(uid)
            
            try:
                await ctx.edit_origin(embed=embed, components=[])
            except:
                await ctx.edit(embed=embed, components=[])
            return
        
        dialogue = '...'
        treasures_found = None
        buttons = self.nikogotchi_buttons(uid, ctx.locale)
        select = await self.feed_nikogotchi(ctx)

        if nikogotchi.status == 2:
            if custom_id == 'pet':
                happiness_increase = 20
                nikogotchi.happiness = min(nikogotchi.max_happiness, nikogotchi.happiness + happiness_increase)
                dialogue = random.choice(loc.l(f'nikogotchi.dialogue.{nikogotchi.nid}.pet'))

            if custom_id == 'clean':
                cleanliness_increase = 30
                nikogotchi.cleanliness = min(nikogotchi.max_cleanliness, nikogotchi.cleanliness + cleanliness_increase)
                dialogue = random.choice(loc.l(f'nikogotchi.dialogue.{nikogotchi.nid}.cleaned'))

            if custom_id == 'findtreasure':
                dialogue = loc.l('nikogotchi.treasured.dialogues.sent')
                nikogotchi.status = 3
                nikogotchi.started_finding_treasure_at = datetime.now()

        if nikogotchi.started_finding_treasure_at != None and custom_id == 'callback':
            treasures_found = await self.calculate_treasure_seek(uid, round((datetime.now() - nikogotchi.started_finding_treasure_at).total_seconds() / 3600))
            nikogotchi.status = 2
            nikogotchi.started_finding_treasure_at = False
            if treasures_found == None:
                dialogue = loc.l('nikogotchi.treasured.dialogues.none_found')
        
        embeds = await self.get_main_embeds(ctx, age, dialogue, treasures_found, nikogotchi, None)

        if not custom_id == 'feed':
            if nikogotchi.status == 2:
                buttons[0].disabled = False
                buttons[1].disabled = False
                buttons[2].disabled = False

                buttons[2].label = str(loc.l('nikogotchi.components.find_treasure'))
                buttons[2].custom_id = f'action_findtreasure_{uid}'
            else:
                select.disabled = True
                buttons[0].disabled = True
                buttons[1].disabled = True
                buttons[2].disabled = False

                buttons[2].label = str(loc.l('nikogotchi.components.call_back'))
                buttons[2].custom_id = f'action_callback_{uid}'
        try:
            await ctx.edit_origin(embeds=embeds, components=[ActionRow(select), ActionRow(*buttons)])
        except:
            await ctx.edit(embeds=embeds, components=[ActionRow(select), ActionRow(*buttons)])
        await self.save_nikogotchi(nikogotchi, ctx.author.id)

    async def feed_nikogotchi(self, ctx):
        food_options = []

        nikogotchi_data: Nikogotchi = await Nikogotchi(ctx.author.id).fetch()
        
        nikogotchi = await self.get_nikogotchi(ctx.author.id)
        
        loc = Localization(ctx.locale)
        
        options = False

        if nikogotchi_data.glitched_pancakes > 0:
            food_options.append(
                StringSelectOption(
                    label=loc.l('nikogotchi.components.feed.glitched_pancakes', amount=nikogotchi_data.glitched_pancakes),
                    emoji=PartialEmoji(1152356972423819436),
                    value=f'pancakeglitched_{ctx.author.id}'
                )
            )
            
            options = True

        if nikogotchi_data.golden_pancakes > 0:
            food_options.append(
                StringSelectOption(
                    label=loc.l('nikogotchi.components.feed.golden_pancakes', amount=nikogotchi_data.golden_pancakes),
                    emoji=PartialEmoji(1152330988022681821),
                    value=f'goldenpancake_{ctx.author.id}'
                )
            )
            
            options = True

        if nikogotchi_data.pancakes > 0:
            food_options.append(
                StringSelectOption(
                    label=loc.l('nikogotchi.components.feed.pancakes', amount=nikogotchi_data.pancakes),
                    emoji=PartialEmoji(1147281411854839829),
                    value=f'pancake_{ctx.author.id}'
                )
            )
            
            options = True
            
        placeholder = loc.l('nikogotchi.components.feed.placeholder', name=nikogotchi.name)
        cannot_feed = False
            
        if not options:
            food_options.append(
                StringSelectOption(
                    label=f'no food',
                    value='nofood'
                )
            )
            
            placeholder = loc.l('nikogotchi.components.feed.no_food')
            cannot_feed = True
            
        select = StringSelectMenu(
            *food_options,
            custom_id='feed_food',
            placeholder=placeholder,
            disabled=cannot_feed
        )

        return select
    
    @component_callback('feed_food')
    async def feed_food(self, ctx: ComponentContext):

        await ctx.defer(edit_origin=True)

        nikogotchi = await self.get_nikogotchi(ctx.author.id)
        data = ctx.values[0].split('_')
        
        value = data[0]
        uid = int(data[1])
        
        if ctx.author.id != uid:
            return

        nikogotchi_data: Nikogotchi = await Nikogotchi(uid).fetch()
        
        pancakes = nikogotchi_data.pancakes
        golden_pancakes = nikogotchi_data.golden_pancakes
        glitched_pancakes = nikogotchi_data.glitched_pancakes

        hunger_increase = 0
        health_increase = 0
        
        updated_stats = []
        
        loc = Localization(ctx.locale)

        if value == 'goldenpancake':
            if golden_pancakes <= 0:
                dialogue = loc.l('nikogotchi.components.feed.invalid')
            else:
                hunger_increase = 50
                health_increase = 25

                golden_pancakes -= 1
                dialogue = random.choice(loc.l(f'nikogotchi.dialogue.{nikogotchi.nid}.fed'))
        elif value == 'pancakeglitched':
            if glitched_pancakes <= 0:
                dialogue = loc.l('nikogotchi.components.feed.invalid')
            else:
                hunger_increase = 9999
                health_increase = 9999
                
                glitched_pancakes -= 1
                updated_stats = await nikogotchi.level_up(5)
                dialogue = loc.l('nikogotchi.components.feed.glitched_powerup')
        else:
            if pancakes <= 0:
                dialogue = loc.l('nikogotchi.components.feed.invalid')
            else:
                hunger_increase = 25
                health_increase = 1
                
                pancakes -= 1
                dialogue = random.choice(loc.l(f'nikogotchi.dialogue.{nikogotchi.nid}.fed'))
                
        await nikogotchi.update(
            pancakes = pancakes,
            golden_pancakes = golden_pancakes,
            glitched_pancakes = glitched_pancakes
        )

        nikogotchi.hunger = min(nikogotchi.max_hunger, nikogotchi.hunger + hunger_increase)
        nikogotchi.health = min(nikogotchi.max_health, nikogotchi.health + health_increase)

        await self.save_nikogotchi(nikogotchi, ctx.author.id)

        buttons = self.nikogotchi_buttons(ctx.author.id, ctx.locale)
        select = await self.feed_nikogotchi(ctx)

        embeds = await self.get_main_embeds(ctx, await self.get_nikogotchi_age(ctx.author.id),
                                                     dialogue, None, nikogotchi, updated_stats)

        await ctx.edit_origin(embeds=embeds, components=[ActionRow(select), ActionRow(*buttons)])

    @nikogotchi.subcommand(sub_cmd_description='Send away your Nikogotchi.')
    async def send_away(self, ctx: SlashContext):
        
        loc = Localization(ctx.locale)

        nikogotchi = await self.get_nikogotchi(ctx.author.id)
        
        if nikogotchi is None:
            return await fancy_message(ctx, loc.l('nikogotchi.other.you_invalid'), ephemeral=True, color=0xff0000)
        
        name = nikogotchi.name

        buttons = [
            Button(style=ButtonStyle.RED, label=loc.l('general.buttons._yes'), custom_id=f'rehome'),
            Button(style=ButtonStyle.GRAY, label=loc.l('general.buttons._cancel'), custom_id=f'cancel')
        ]

        embed = fancy_embed(loc.l('nikogotchi.other.send_away.description', name=name))

        await ctx.send(embed=embed, ephemeral=True, components=buttons)

        button = await self.bot.wait_for_component(components=buttons)
        button_ctx = button.ctx

        custom_id = button_ctx.custom_id

        if custom_id == f'rehome':
            await self.delete_nikogotchi(ctx.author.id)
            embed = fancy_embed(loc.l('nikogotchi.other.send_away.success', name=name))
            await ctx.edit(embed=embed, components=[])
        else:
            await ctx.delete() 

    async def init_rename_flow(self, ctx: ComponentContext | SlashContext, old_name: str, cont: bool = False):
        loc = Localization(ctx.locale)
        modal = Modal(
            ShortText(
                custom_id='name',
                value=old_name,
                label=loc.l('nikogotchi.other.renaming.input.label'),
                placeholder=loc.l('nikogotchi.other.renaming.input.placeholder'),
                max_length=32
            ),
            custom_id='rename_nikogotchi',
            title=loc.l('nikogotchi.other.renaming.title')
        )
        if (cont):
            modal.custom_id = 'rename_nikogotchi continue'
        await ctx.send_modal(modal)

    @modal_callback(re.compile(r'rename_nikogotchi?.+'))
    async def on_rename_answer(self, ctx: ModalContext, name: str):

        if ctx.custom_id.endswith("continue"):
            await ctx.defer(edit_origin=True)
        else:
            await ctx.defer(ephemeral=True)
        loc = Localization(ctx.locale)
        nikogotchi = await self.get_nikogotchi(ctx.author.id)

        old_name = nikogotchi.name
        nikogotchi.name = name
        await self.save_nikogotchi(nikogotchi, ctx.author.id)
        components = []
        if ctx.custom_id.endswith("continue"):
            components.append(Button(
                style=ButtonStyle.GRAY,
                label=loc.l('general.buttons._continue'),
                custom_id=f'action_refresh_{ctx.author_id}'
            ))
        await fancy_message(ctx, loc.l('nikogotchi.other.renaming.response', new_name=name, old_name=old_name), ephemeral=True, components=components)

    @nikogotchi.subcommand(sub_cmd_description='Rename your Nikogotchi.')
    async def rename(self, ctx: SlashContext):
        loc = Localization(ctx.locale)
        nikogotchi = await self.get_nikogotchi(ctx.author.id)

        if nikogotchi is None:
            return await fancy_message(ctx, loc.l('nikogotchi.other.you_invalid'), ephemeral=True, color=0xff0000)

        return await self.init_rename_flow(ctx, nikogotchi.name)

    @nikogotchi.subcommand(sub_cmd_description='Show off your Nikogotchi, or view someone else\'s.!')
    @slash_option('user', description='The user to view.', opt_type=OptionType.USER)
    async def show(self, ctx: SlashContext, user: User = None):
        if user is None:
            user = ctx.user

        uid = user.id

        nikogotchi = await self.get_nikogotchi(uid)
        
        loc = Localization(ctx.locale)

        if nikogotchi is None:
            return await fancy_message(ctx, loc.l('nikogotchi.other.other_invalid'), ephemeral=True, color=0xff0000)
        
        metadata = await fetch_nikogotchi_metadata(nikogotchi.nid)

        age = await self.get_nikogotchi_age(uid)
        age = loc.l('nikogotchi.age', years=age.years, months=age.months, days=age.days)

        embed = Embed(
            title=nikogotchi.name,
            color=0x8b00cc,
        )

        embed.author = EmbedAuthor(
            name=str(loc.l('nikogotchi.other.view.owned', user=user.username)),
            icon_url=user.avatar.url
        )
        
        embed.description = str(loc.l('nikogotchi.other.view.description', age=age, health=nikogotchi.health, max_health=nikogotchi.max_health))

        embed.set_image(url=metadata.image_url)

        await ctx.send(embed=embed)

    """@nikogotchi.subcommand(sub_cmd_description='Trade your Nikogotchi with someone else!')
    @slash_option('user', description='The user to trade with.', opt_type=OptionType.USER, required=True)
    async def trade(self, ctx: SlashContext, user: User):

        nikogotchi_one = await self.get_nikogotchi(ctx.author.id)
        nikogotchi_two = await self.get_nikogotchi(user.id)
        
        loc = Localization(ctx.locale)
        
        if nikogotchi_one is None:
            return await fancy_message(ctx, loc.l('nikogotchi.other.you_invalid'), ephemeral=True, color=0xff0000)
        if nikogotchi_two is None:
            return await fancy_message(ctx, loc.l('nikogotchi.other.other_invalid'), ephemeral=True, color=0xff0000)
        
        one_data = await fetch_nikogotchi_metadata(nikogotchi_one.nid)
        two_data = await fetch_nikogotchi_metadata(nikogotchi_two.nid)
        

        await fancy_message(ctx, loc.l('nikogotchi.other.trade.waiting', user=user.mention), ephemeral=True)

        uid = user.id

        embed = fancy_embed(loc.l('nikogotchi.other.trade.request', user=ctx.author.mention, name_one=nikogotchi_one.name, name_two=nikogotchi_two.name))

        buttons = [
            Button(style=ButtonStyle.SUCCESS, label=loc.l('general.buttons._yes'), custom_id=f'trade {ctx.author.id} {uid}'),
            Button(style=ButtonStyle.DANGER, label=loc.l('general.buttons._no'), custom_id=f'decline {ctx.author.id} {uid}')
        ]

        await user.send(embed=embed, components=buttons)

        button = await self.bot.wait_for_component(components=buttons)
        button_ctx = button.ctx

        await button_ctx.defer(edit_origin=True)

        custom_id = button_ctx.custom_id

        if custom_id == f'trade {ctx.author.id} {uid}':
            await self.save_nikogotchi(nikogotchi_two, ctx.author.id)
            await self.save_nikogotchi(nikogotchi_one, uid)

            embed_two = fancy_embed(loc.l('nikogotchi.other.trade.success', user=user.mention, name=nikogotchi_two.name))
            embed_two.set_image(url=two_data.image_url)

            embed_one = fancy_embed(loc.l('nikogotchi.other.trade.success', user=ctx.author.mention, name=nikogotchi_one.name))
            embed_one.set_image(url=one_data.image_url)

            await button_ctx.edit_origin(embed=embed_one, components=[])
            await ctx.edit(embed=embed_two)
        else:
            embed = fancy_embed(loc.l('nikogotchi.other.trade.declined'))
            await ctx.edit(embed=embed)

            embed = fancy_embed(loc.l('nikogotchi.other.trade.success_decline'))

            await button_ctx.edit_origin(embed=embed, components=[])"""

    @slash_command(description='View what treasure you or someone else has!')
    @integration_types(guild=True, user=True)
    @slash_option('user', description='The person you would like to see treasure of', opt_type=OptionType.USER)
    async def treasures(self, ctx: SlashContext, user: User = None):
        loc = Localization(ctx.locale)

        if user is None:
            user = ctx.user
        if user.bot:
            return await ctx.send(loc.l('treasure.bots', bot=user.mention), ephemeral=True)
        all_treasures = await fetch_treasure()
        treasure_string = ''
        
        user_data: UserData = await UserData(user.id).fetch()
        owned_treasures = user_data.owned_treasures

        for treasure_nid, item in all_treasures.items():
            
            treasure_loc: dict = loc.l(f'items.treasures')
            
            name = treasure_loc[treasure_nid]['name']

            treasure_string += loc.l('treasure.item', amount=owned_treasures.get(treasure_nid, 0), icon=emojis[f"treasure_{treasure_nid}"], name=name)+"\n"
        
        await ctx.send(embed=Embed(
            description=str(loc.l('treasure.message', user=user.mention, treasures=treasure_string)),
            color=0x8b00cc,
        ))
