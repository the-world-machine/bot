import math
import re
import random
from interactions import *
from asyncio import TimeoutError
from dataclasses import dataclass
from utilities.emojis import emojis
from typing import Dict, List, Union
from datetime import datetime, timedelta
from utilities.nikogotchi_metadata import *
from interactions.api.events import Component
from utilities.shop.fetch_items import fetch_treasure
from utilities.localization import Localization, fnum, ftime
from utilities.message_decorations import Colors, fancy_message, make_progress_bar
from utilities.database.main import NikogotchiData, StatUpdate, UserData, Nikogotchi


@dataclass
class TreasureSeekResults:
	found_treasure: Dict[str, int]
	total_treasure: int
	time_spent: timedelta


class NikogotchiCommands(Extension):

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

		await nikogotchi_data.update(**nikogotchi.__dict__)

	async def delete_nikogotchi(self, uid: int):

		nikogotchi_data = await Nikogotchi(uid).fetch()

		await nikogotchi_data.update(available=False, status=-1, nid="?")

	def nikogotchi_buttons(self, ctx, owner_id: int):
		prefix = 'action_'
		suffix = f'_{owner_id}'

		loc = Localization(ctx.locale)

		return [
		    Button(style=ButtonStyle.SUCCESS, label=loc.l('nikogotchi.components.pet'), custom_id=f'{prefix}pet{suffix}'),
		    Button(style=ButtonStyle.SUCCESS, label=loc.l('nikogotchi.components.clean'), custom_id=f'{prefix}clean{suffix}'),
		    Button(style=ButtonStyle.PRIMARY, label=loc.l('nikogotchi.components.find_treasure'), custom_id=f'{prefix}findtreasure{suffix}'),
		    Button(style=ButtonStyle.GREY, emoji=emojis['icons']["refresh"], custom_id=f'{prefix}refresh{suffix}'),
		    Button(style=ButtonStyle.DANGER, label='X', custom_id=f'{prefix}exit{suffix}')
		]

	async def get_nikogotchi_age(self, uid: int):
		nikogotchi_data: Nikogotchi = await Nikogotchi(uid).fetch()

		return datetime.now() - nikogotchi_data.hatched

	async def get_main_embeds(
	    self,
	    ctx: InteractionContext,
	    n: Nikogotchi,
	    dialogue: str = None,
	    treasure_seek_results: TreasureSeekResults = None,
	    stats_update: List[StatUpdate] = None,
	    preview: bool = False,
	) -> List[Embed] | Embed:

		metadata = await fetch_nikogotchi_metadata(n.nid)
		owner = await ctx.client.fetch_user(n._id)
		loc = Localization(ctx.locale)

		nikogotchi_status = loc.l('nikogotchi.status.normal')

		if random.randint(0, 100) == 20:
			nikogotchi_status = loc.l('nikogotchi.status.normal-rare')

		if n.happiness < 20:
			nikogotchi_status = loc.l('nikogotchi.status.pet', name=n.name)

		if n.cleanliness < 20:
			nikogotchi_status = loc.l('nikogotchi.status.dirty', name=n.name)

		if n.hunger < 20:
			nikogotchi_status = loc.l('nikogotchi.status.hungry', name=n.name)
		treasure_looking = ''
		if n.status == 3:
			nikogotchi_status = loc.l('nikogotchi.status.treasure', name=n.name)
			treasure_looking = f'\n-# 🎒  {ftime(datetime.now() - n.started_finding_treasure_at)}'

		treasure_found = ''
		if treasure_seek_results != None:
			treasures = ''
			total = 0

			max_amount_length = len(fnum(max(treasure_seek_results.found_treasure.values(), default=0), locale=loc.locale))

			for (tid, amount) in treasure_seek_results.found_treasure.items():
				total += amount
				treasures += loc.l(
				    'treasure.item', amount=fnum(amount, loc.locale).rjust(max_amount_length), icon=emojis['treasures'][tid], name=loc.l(f"items.treasures.{tid}.name")
				) + "\n"

			treasure_found = loc.l('nikogotchi.treasured.message', treasures=treasures, total=total, time=ftime(treasure_seek_results.time_spent))

		levelled_up_stats = ''

		if stats_update:
			for stat in stats_update:
				levelled_up_stats += loc.l(
				    "nikogotchi.levelupped.stat", icon=stat.icon, old_value=stat.old_value, new_value=stat.new_value, increase=(stat.new_value - stat.old_value)
				) + "\n"

		if n.health < min(20, n.max_health * 0.20):
			nikogotchi_status = loc.l('nikogotchi.status.danger', name=n.name)

		# crafting embeds - - -
		embeds = []
		age = ftime(await self.get_nikogotchi_age(n._id), minimum_unit="minute")
		age = f"  •  ⏰  {age}" if len(age) != 0 else ""


		def make_pb(current, maximum) -> str:
			return f"{make_progress_bar(current, maximum, 5, 'round')} ({current} / {maximum})"

		info = \
             f"❤️  {make_pb(n.health, n.max_health)}\n"+\
             f'⚡  {make_pb(n.energy, 5)}\n'+\
             '\n'+\
             f'🍴  {make_pb(n.hunger, n.max_hunger)}\n'+\
             f'🫂  {make_pb(n.happiness, n.max_happiness)}\n'+\
             f'🧽  {make_pb(n.cleanliness, n.max_cleanliness)}\n'+\
             '\n'+\
             f'-# 🏆  **{n.level}**  •  🗡️  **{n.attack}**  •  🛡️  **{n.defense}**'+\
             f'{treasure_looking}{age}'
		if not preview:
			if dialogue:
				info += f'\n-# 💬 {dialogue}'
			else:
				info += f'\n-# 💭 {loc.l("nikogotchi.status.template", status=nikogotchi_status)}'
		N_embed = Embed(title=n.name, description=info, color=Colors.DEFAULT)
		N_embed.set_thumbnail(metadata.image_url)

		if preview:
			N_embed.set_author(name=loc.l('nikogotchi.owned', user=owner.username), icon_url=owner.avatar_url)
			return N_embed

		if levelled_up_stats:
			L_embed = Embed(
			    title=loc.l("nikogotchi.levelupped.title", level=n.level), description=loc.l("nikogotchi.levelupped.message", stats=levelled_up_stats), color=Colors.GREEN
			)
			embeds.append(L_embed)

		if treasure_found:
			T_embed = Embed(title=loc.l("nikogotchi.treasured.title"), description=treasure_found, color=Colors.GREEN)
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
			if not metadata and nikogotchi.nid != "?":

				buttons = [
				    Button(style=ButtonStyle.GREEN, label=loc.l('nikogotchi.other.error.buttons.rotate'), custom_id=f'rotate'),
				    Button(style=ButtonStyle.GRAY, label=loc.l('nikogotchi.other.error.buttons.send_away'), custom_id=f'_rehome')
				]

				await fancy_message(ctx, loc.l('nikogotchi.other.error.description', id=nikogotchi.nid), color=Colors.BAD, ephemeral=True, components=buttons)
				button_ctx = (await ctx.client.wait_for_component(components=buttons)).ctx

				custom_id = button_ctx.custom_id

				if custom_id == '_rehome':
					await self.delete_nikogotchi(ctx.author.id)
					return await ctx.edit(embed=Embed(description=loc.l('nikogotchi.other.send_away.success', name=nikogotchi.name), color=Colors.DEFAULT), components=[])
				else:
					nikogotchi.available = True
			if not nikogotchi.available:
				return await fancy_message(ctx, loc.l('nikogotchi.invalid'), ephemeral=True, color=Colors.BAD)
			selected_nikogotchi: NikogotchiMetadata = await pick_random_nikogotchi(nikogotchi.rarity)

			await nikogotchi.update(
			    nid=selected_nikogotchi.name,
			    name=loc.l(f'nikogotchi.name.{selected_nikogotchi.name}'),
			    level=0,
			    health=50,
			    energy=5,
			    hunger=50,
			    cleanliness=50,
			    happiness=50,
			    attack=5,
			    defense=2,
			    max_health=50,
			    max_hunger=50,
			    max_cleanliness=50,
			    max_happiness=50,
			    last_interacted=datetime.now(),
			    hatched=datetime.now(),
			    started_finding_treasure_at=datetime.now(),
			    available=False,
			    status=2
			)

			hatched_embed = Embed(title=loc.l('nikogotchi.found.title', name=nikogotchi.name), color=Colors.GREEN, description=loc.l('nikogotchi.found.description'))

			hatched_embed.set_thumbnail(url=selected_nikogotchi.image_url)

			buttons = [
			    Button(style=ButtonStyle.GREEN, label=loc.l('nikogotchi.other.renaming.button'), custom_id=f'rename {ctx.id}'),
			    Button(style=ButtonStyle.GRAY, label=loc.l('general.buttons._continue'), custom_id=f'continue {ctx.id}')
			]
			await ctx.send(embed=hatched_embed, components=buttons, ephemeral=True, edit_origin=True)
			try:
				button: Component = await ctx.client.wait_for_component(components=buttons, timeout=15.0)
				if button.ctx.custom_id == f'rename {ctx.id}':
					await self.init_rename_flow(button.ctx, nikogotchi.name, True)
			except TimeoutError:
				return await self.check(ctx)
		await self.nikogotchi_interaction(ctx)

	async def calculate_treasure_seek(self, uid: int, time_taken: timedelta) -> TreasureSeekResults | None:
		user_data: UserData = await UserData(uid).fetch()

		amount = math.floor(time_taken.total_seconds() / 3600)

		if amount == 0:
			return None

		treasures_found = {}
		user_treasures = user_data.owned_treasures

		for _ in range(amount):
			value = random.randint(0, 5000)
			treasure_id = ''

			if value > 4900:
				treasure_id = random.choice([ "die", "sun", "clover"])
			elif value > 3500:
				treasure_id = random.choice([ "amber", "pen", "card"]) # TODO: store rarity in DB
			elif value > 100:
				treasure_id = random.choice([ "journal", "bottle", "shirt"])

			if treasure_id:
				treasures_found.setdefault(treasure_id, 0)
				treasures_found[treasure_id] += 1
				user_treasures.setdefault(treasure_id, 0)
				user_treasures[treasure_id] += 1

		await user_data.update(owned_treasures=user_treasures)
		return TreasureSeekResults(treasures_found, amount, time_taken)

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
			    embed=Embed(description=loc.l('nikogotchi.other.you_invalid'), color=Colors.BAD),
			    components=Button(emoji=emojis['icons']["refresh"], custom_id=f'action_refresh_{ctx.author.id}', style=ButtonStyle.SECONDARY)
			)

		last_interacted = nikogotchi.last_interacted

		if nikogotchi.started_finding_treasure_at == False:
			await nikogotchi.update(started_finding_treasure_at=datetime.now())

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
			age = ftime(age)
			embed = Embed(
			    title=loc.l('nikogotchi.died.title', name=nikogotchi.name),
			    color=Colors.DARKER_WHITE,
			    description=loc.l('nikogotchi.died.description', name=nikogotchi.name, age=age, time_difference=fnum(int(time_difference)))
			)

			await self.delete_nikogotchi(uid)

			try:
				await ctx.edit_origin(embed=embed, components=[])
			except:
				await ctx.edit(embed=embed, components=[])
			return

		dialogue = ''
		treasures_found = None
		buttons = self.nikogotchi_buttons(ctx, uid)
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

		if custom_id == 'callback' and nikogotchi.status == 3:
			treasures_found = await self.calculate_treasure_seek(uid, datetime.now() - nikogotchi.started_finding_treasure_at)
			nikogotchi.status = 2
			print(datetime.now(), ctx.author_id, treasures_found)
			if treasures_found == None:
				dialogue = loc.l('nikogotchi.treasured.dialogues.none_found')

		embeds = await self.get_main_embeds(ctx, nikogotchi, dialogue, treasure_seek_results=treasures_found)

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

		if nikogotchi_data.glitched_pancakes > 0:
			food_options.append(
			    StringSelectOption(
			        label=loc.l('nikogotchi.components.feed.glitched_pancakes', amount=nikogotchi_data.glitched_pancakes), emoji=emojis['pancakes']['glitched'], value=f'glitched'
			    )
			)

		if nikogotchi_data.golden_pancakes > 0:
			food_options.append(
			    StringSelectOption(
			        label=loc.l('nikogotchi.components.feed.golden_pancakes', amount=nikogotchi_data.golden_pancakes), emoji=emojis['pancakes']['golden'], value=f'golden'
			    )
			)

		if nikogotchi_data.pancakes > 0:
			food_options.append(
			    StringSelectOption(label=loc.l('nikogotchi.components.feed.pancakes', amount=nikogotchi_data.pancakes), emoji=emojis['pancakes']['normal'], value=f'normal')
			)

		placeholder = loc.l('nikogotchi.components.feed.placeholder', name=nikogotchi.name)
		disabled = False
		if len(food_options) == 0:
			food_options.append(StringSelectOption(label=f'no food', value='nofood')) # invisible to end user but required by api
			disabled = True
			placeholder = loc.l('nikogotchi.components.feed.no_food')

		select = StringSelectMenu(*food_options, custom_id=f'feed_food {ctx.user.id}', placeholder=placeholder, disabled=disabled)

		return select

	ff = re.compile(r'feed_food (\d+)$')

	@component_callback(ff)
	async def feed_food(self, ctx: ComponentContext):

		await ctx.defer(edit_origin=True)

		match = self.ff.match(ctx.custom_id)
		uid = int(match.group(1))

		if ctx.author.id != uid:
			return await ctx.edit()

		nikogotchi: Nikogotchi = await self.get_nikogotchi(uid)
		pancake_type = ctx.values[0]

		normal_pancakes = nikogotchi.pancakes
		golden_pancakes = nikogotchi.golden_pancakes
		glitched_pancakes = nikogotchi.glitched_pancakes

		hunger_increase = 0
		health_increase = 0

		updated_stats = []

		loc = Localization(ctx.locale)

		match pancake_type:
			case 'golden':
				if golden_pancakes <= 0:
					dialogue = loc.l('nikogotchi.components.feed.invalid')
				else:
					hunger_increase = 50
					health_increase = 25

					golden_pancakes -= 1
				dialogue = random.choice(loc.l(f'nikogotchi.dialogue.{nikogotchi.nid}.fed'))
			case 'glitched':
				if glitched_pancakes <= 0:
					dialogue = loc.l('nikogotchi.components.feed.invalid')
				else:
					hunger_increase = 9999
					health_increase = 9999

					glitched_pancakes -= 1
					updated_stats = await nikogotchi.level_up(5)
					dialogue = loc.l('nikogotchi.components.feed.glitched_powerup')
			case 'normal':
				if normal_pancakes <= 0:
					dialogue = loc.l('nikogotchi.components.feed.invalid')
				else:
					hunger_increase = 25
					health_increase = 1

					normal_pancakes -= 1
					dialogue = random.choice(loc.l(f'nikogotchi.dialogue.{nikogotchi.nid}.fed'))
			case _:
				return await ctx.edit()

		nikogotchi = await nikogotchi.update(pancakes=normal_pancakes, golden_pancakes=golden_pancakes, glitched_pancakes=glitched_pancakes)

		nikogotchi.hunger = min(nikogotchi.max_hunger, nikogotchi.hunger + hunger_increase)
		nikogotchi.health = min(nikogotchi.max_health, nikogotchi.health + health_increase)

		await self.save_nikogotchi(nikogotchi, ctx.author.id)

		buttons = self.nikogotchi_buttons(ctx, ctx.author.id)
		select = await self.feed_nikogotchi(ctx)

		embeds = await self.get_main_embeds(ctx, nikogotchi, dialogue, stats_update=updated_stats)

		await ctx.edit_origin(embeds=embeds, components=[ActionRow(select), ActionRow(*buttons)])

	@nikogotchi.subcommand(sub_cmd_description='Part ways with your Nikogotchi')
	async def send_away(self, ctx: SlashContext):

		loc = Localization(ctx.locale)

		nikogotchi = await self.get_nikogotchi(ctx.author.id)

		if nikogotchi is None:
			return await fancy_message(ctx, loc.l('nikogotchi.other.you_invalid'), ephemeral=True, color=Colors.BAD)

		name = nikogotchi.name

		buttons = [
		    Button(style=ButtonStyle.RED, label=loc.l('general.buttons._yes'), custom_id=f'rehome'),
		    Button(style=ButtonStyle.GRAY, label=loc.l('general.buttons._cancel'), custom_id=f'cancel')
		]

		await ctx.send(embed=Embed(description=loc.l('nikogotchi.other.send_away.description', name=name), color=Colors.WARN), ephemeral=True, components=buttons)

		button = await ctx.client.wait_for_component(components=buttons)
		button_ctx = button.ctx

		custom_id = button_ctx.custom_id

		if custom_id == f'rehome':
			await self.delete_nikogotchi(ctx.author.id)
			await ctx.edit(embed=Embed(description=loc.l('nikogotchi.other.send_away.success', name=name), color=Colors.GREEN), components=[])
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
		loc = Localization(ctx.locale)

		if ctx.custom_id.endswith("continue"):
			await ctx.defer(edit_origin=True)
		else:
			await ctx.defer(ephemeral=True)
		nikogotchi = await self.get_nikogotchi(ctx.author.id)
		if nikogotchi is None:
			return await fancy_message(ctx, Localization(ctx.locale).l('nikogotchi.other.rename_you_invalid'), ephemeral=True, color=Colors.BAD)

		old_name = nikogotchi.name
		nikogotchi.name = name
		await self.save_nikogotchi(nikogotchi, ctx.author.id)
		components = []
		if ctx.custom_id.endswith("continue"):
			components.append(Button(style=ButtonStyle.GRAY, label=loc.l('general.buttons._continue'), custom_id=f'action_refresh_{ctx.author_id}'))
		await fancy_message(ctx, loc.l('nikogotchi.other.renaming.response', new_name=name, old_name=old_name), ephemeral=True, components=components)

	@nikogotchi.subcommand(sub_cmd_description='Rename your Nikogotchi')
	async def rename(self, ctx: SlashContext):
		nikogotchi = await self.get_nikogotchi(ctx.author.id)

		if nikogotchi is None:
			return await fancy_message(ctx, Localization(ctx.locale).l('nikogotchi.other.you_invalid'), ephemeral=True, color=Colors.BAD)

		return await self.init_rename_flow(ctx, nikogotchi.name)

	@nikogotchi.subcommand(sub_cmd_description="Show off a nikogotchi in chat")
	@slash_option('user', description="Who's nikogotchi would you like to see?", opt_type=OptionType.USER)
	async def show(self, ctx: SlashContext, user: User = None):
		loc = Localization(ctx.locale)
		if user is None:
			user = ctx.user

		nikogotchi = await self.get_nikogotchi(user.id)

		if nikogotchi is None:
			return await fancy_message(ctx, loc.l('nikogotchi.other.other_invalid'), ephemeral=True, color=Colors.BAD)

		await ctx.send(embed=await self.get_main_embeds(ctx, nikogotchi, preview=True))

	"""@nikogotchi.subcommand(sub_cmd_description='Trade your Nikogotchi with someone else!')
    @slash_option('user', description='The user to trade with.', opt_type=OptionType.USER, required=True)
    async def trade(self, ctx: SlashContext, user: User):
        loc = Localization(ctx.locale)

        nikogotchi_one = await self.get_nikogotchi(ctx.author.id)
        nikogotchi_two = await self.get_nikogotchi(user.id)
        
        
        if nikogotchi_one is None:
            return await fancy_message(ctx, loc.l('nikogotchi.other.you_invalid'), ephemeral=True, color=Colors.BAD)
        if nikogotchi_two is None:
            return await fancy_message(ctx, loc.l('nikogotchi.other.other_invalid'), ephemeral=True, color=Colors.BAD)
        
        one_data = await fetch_nikogotchi_metadata(nikogotchi_one.nid)
        two_data = await fetch_nikogotchi_metadata(nikogotchi_two.nid)
        

        await fancy_message(ctx, loc.l('nikogotchi.other.trade.waiting', user=user.mention), ephemeral=True)

        uid = user.id

        buttons = [
            Button(style=ButtonStyle.SUCCESS, label=loc.l('general.buttons._yes'), custom_id=f'trade {ctx.author.id} {uid}'),
            Button(style=ButtonStyle.DANGER, label=loc.l('general.buttons._no'), custom_id=f'decline {ctx.author.id} {uid}')
        ]

        await user.send(
            embed=Embed(
                description=loc.l('nikogotchi.other.trade.request', user=ctx.author.mention, name_one=nikogotchi_one.name, name_two=nikogotchi_two.name),
                color=Colors.WARN
            ),
            components=buttons
        )

        button = await ctx.client.wait_for_component(components=buttons)
        button_ctx = button.ctx

        await button_ctx.defer(edit_origin=True)

        custom_id = button_ctx.custom_id

        if custom_id == f'trade {ctx.author.id} {uid}':
            del nikogotchi_two._id
            del nikogotchi_one._id
            await self.save_nikogotchi(nikogotchi_two, ctx.author.id)
            await self.save_nikogotchi(nikogotchi_one, uid)
            nikogotchi_two._id = str(ctx.author.id)
            nikogotchi_one._id = str(uid)
            embed_two = Embed(
                description=loc.l('nikogotchi.other.trade.success', user=user.mention, name=nikogotchi_two.name),
                color=Colors.GREEN,
            )
            embed_two.set_image(url=two_data.image_url)

            embed_one = Embed(
                description=loc.l('nikogotchi.other.trade.success', user=ctx.author.mention, name=nikogotchi_one.name),
                color=Colors.GREEN,
            )
            embed_one.set_image(url=one_data.image_url)

            await button_ctx.edit_origin(embed=embed_one, components=[])
            await ctx.edit(embed=embed_two)
        else:
            sender_embed = Embed(
                description=loc.l('nikogotchi.other.trade.declined'),
                color=Colors.RED,
            )
            receiver_embed = Embed(
                description=loc.l('nikogotchi.other.trade.success_decline'),
                color=Colors.RED,
            )
            await asyncio.gather(
                ctx.edit(embed=sender_embed),
                button_ctx.edit_origin(embed=receiver_embed, components=[])
            )"""

	@slash_command(description="View what treasure someone has")
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
		max_amount_length = len(fnum(max(owned_treasures.values(), default=0), locale=loc.locale))

		for treasure_nid, item in all_treasures.items():

			treasure_loc: dict = loc.l(f'items.treasures')

			name = treasure_loc[treasure_nid]['name']

			treasure_string += loc.l(
			    'treasure.item', amount=fnum(owned_treasures.get(treasure_nid, 0), locale=loc.locale).rjust(max_amount_length), icon=emojis['treasures'][treasure_nid], name=name
			) + "\n"

		await ctx.send(embed=Embed(
		    description=str(loc.l('treasure.message', user=user.mention, treasures=treasure_string)),
		    color=Colors.DEFAULT,
		))
