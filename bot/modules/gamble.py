import asyncio
import random
from utilities.emojis import emojis
from dataclasses import dataclass
from utilities.localization import fnum
from utilities.database.main import UserData
from utilities.message_decorations import Colors, fancy_message
from interactions import Embed, Extension, OptionType, SlashContext, slash_command, slash_option


@dataclass
class Slot:
    emoji: int
    value: float
    def __eq__(self, other):
        if isinstance(other, Slot):
            return self.emoji == other.emoji and self.value == other.value
        return False

    def __hash__(self):
        return hash((self.emoji, self.value))
    
    def __lt__(self, other):
        return self.value < other.value

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

class GambleModule(Extension):
  @slash_command(description='All things to do with gambling wool')
  async def gamble(self, ctx: SlashContext):
    pass
    
  @gamble.subcommand()
  @slash_option(description='How much wool would you like to bet?', name='bet', required=True, opt_type=OptionType.INTEGER, min_value=100)
  async def wool(self, ctx: SlashContext, bet: int):
    '''Waste your wool away with slots. Totally not a scheme by Magpie.'''
    await ctx.defer()
    
    user_data: UserData = await UserData(ctx.author.id).fetch()
    
    if user_data.wool < bet:
      return await fancy_message(ctx, f"[ You don\'t have enough wool to bet that amount. ]", ephemeral=True, color=Colors.BAD)
    
    await user_data.update(wool=user_data.wool - bet)
    
    random.Random()
    
    selection = []
    for i in range(3):
      selected_slots = slots.copy()
      random.shuffle(selected_slots)
      
      selection.append(selected_slots)
          
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
        column = generate_column(selection[i], index)
        
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
        description=f"## Slot Machine\n\n{ctx.author.mention} has bet {emojis['icons']['wool']}**{fnum(bet)}**.\n{ticker}",
        color=Colors.DEFAULT,
      )
        
    msg = await ctx.send(embed=generate_embed(0, -1, slot_images))
    
    slot_a_value = 0
    slot_b_value = 0
    slot_c_value = 0
    
    for i in range(4):

        await msg.edit(embed=generate_embed(i, 0, slot_images))
        
        slot = selection[0][i]

        slot_a_value = slot.value
        
        await asyncio.sleep(1)
            
    for i in range(4):
        
        await msg.edit(embed=generate_embed(i, 1, slot_images))
        
        slot = selection[1][i]
        
        slot_b_value = slot.value
        
        await asyncio.sleep(1)
            
    result_embed: Embed = None
    
    last_roll = random.randint(4, 5)
            
    for i in range(last_roll):
        
        if i == last_roll - 1:
            await asyncio.sleep(2)
        
        result_embed = generate_embed(i, 2, slot_images)
        
        await msg.edit(embed=result_embed)
        
        slot = selection[2][i]
        
        slot_c_value = slot.value
        
        await asyncio.sleep(1)

    if slot_a_value == slot_b_value == slot_c_value:
        additional_scoring = 100
    else:
        additional_scoring = 1
            
    win_amount = int(
        (slot_a_value + slot_b_value + slot_c_value) * additional_scoring * (bet / 2)
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
          if win_amount < bet:
            result_embed.color = Colors.PURE_ORANGE
            result_embed.set_footer(
                text=f"{ctx.author.username} got back only {fnum(abs(win_amount))} wool..."
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
      
  @gamble.subcommand()
  async def help(self, ctx: SlashContext):
      '''Read up on how the gamble command works'''
      
      await ctx.defer()
      
      text = f'''## Slot Machine
      Gamble any amount of wool as long as you can afford it.
      Here are the slots you can roll and their values:
      '''
      
      existing_slots = []
      point_rows = []
      reduction = "point reduction"
      normal = "points"
      for slot in sorted(set(slots)):
          existing_slots.append(slot.emoji)
          icon = f"<:icon:{slot.emoji}>"
          value = int(slot.value * 100)
          point_rows.append(f'- {icon} **{value} {reduction if value < 0 else normal}**')
          
      text += "\n".join(point_rows)+'\n\n'+\
          'Points are added up and them multiplied by your bet. You also get double the points when you hit a jackpot.'

      await fancy_message(ctx, text)
      