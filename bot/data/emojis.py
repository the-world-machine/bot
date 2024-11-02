import re

def flatten_emojis(data: dict, parent_key: str=''):
  items = []
  for k, v in data.items():
    key = f"{parent_key}.{k}" if parent_key else k
    if isinstance(v, dict):
      items.extend(flatten_emojis(v, key).items())
    else:
      items.append((key, v))
  return dict(items)

def minify_emoji_names(data):
    if isinstance(data, dict):
        return {key: minify_emoji_names(value) for key, value in data.items()}
    elif isinstance(data, str):
        # replaces all names with "i" for more embed space
        return re.sub(r'(?<=[:])\w+(?=:\d)', 'i', data)
    return data

emojis = minify_emoji_names({
   
  # Common
  "icon_loading": '<a:loading:1297357951748669520>',
  "icon_wool": '<:wool:1297359234790588528>',
  "icon_sun": '<:sun:1297359718792298506>',
  "icon_inverted_clover": '<:inverted_clover:1026135536190111755>',
  "icon_capsule": "<:capsule:1147279938660089898>",

  "vibe": "<a:vibe:1297360784325873725>",
  "sleep": "<:sleepy:1297360830924591134>",
  "refresh": "<:refresh:1147696088250335303>",
  
  # Pancakes
  "pancakes": "<:pancakes_:1297375564880941117>",
  "golden_pancakes": "<:golden_pancakes:1297375620073918555>",
  "glitched_pancakes": "<:glitched_pancakes:1297375684791894048>",

  # Treasure Icons
  "treasure_amber": "<:treasure_amulet:1297361078963015775>",
  "treasure_bottle": "<:treasure_bottle:1297360957604892725>",
  "treasure_card": "<:treasure_card:1297360931856322602>",
  "treasure_clover": "<:treasure_clover:1297360984687513602>",
  "treasure_die": "<:treasure_dice:1297361026874081443>",
  "treasure_journal": "<:treasure_journal:1297361121908363326>",
  "treasure_pen": "<:treasure_feather:1297361100681248840>",
  "treasure_shirt": "<:treasure_novelty_shirt:1297360883776884837>",
  "treasure_sun": "<:treasure_sun:1297361056242335834>",

  "progress_bars": {
    # Music
    "square": {
      "empty": {
        "start": '<:square_bar_empty_start:1297359831669280832>',
        "middle": '<:square_bar_empty_middle:1297359933431484466>',
        "end": '<:square_bar_empty_end:1297361887411044352>'
      },
      "filled": {
        "start": '<:square_bar_filled_middle:1297360652599562250>',
        "middle": '<:square_bar_filled_start:1297360697973543026>',
        "end": '<:square_bar_filled_end:1297360738591047691>'
      }
    },
    # Nikogotchi
    "round": {
      "empty": {
        "start": "<:round_bar_empty_start:1297361713980772353>",
        "middle": "<:round_bar_empty_middle:1297361735166197860>",
        "end": "<:round_bar_empty_end:1297361757576232980>"
      },
      "filled": {
        "start": "<:round_bar_filled_start:1297361635375058965>",
        "middle": "<:round_bar_filled_middle:1297361670670254196>",
        "end": "<:round_bar_filled_end:1297361690073108511>"
      }
    }
  }
})