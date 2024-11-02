emojis = {

  # Common
  "icon_loading": '<a:loading:1290848643561164902>',
  "icon_wool": '<:wool:1290848297698852947>',
  "icon_sun": '<:sun:1290848333610618967>',
  "icon_inverted_clover": '<:inverted_clover:1026135536190111755>',
  "icon_capsule": "<:capsule:1147279938660089898>",

  "vibe": "<a:vibe:1290847354542489660>",
  "sleep": "<:sleepy:1290849529670664283>",
  "refresh": "<:refresh:1147696088250335303>",
  
  # Pancakes
  "pancakes": "<:pancakes_:1290847273210740757>",
  "golden_pancakes": "<:golden_pancakes:1290847240247574610>",
  "glitched_pancakes": "<:glitched_pancakes:1290847200112545804>",

  # Treasure Icons
  "treasure_amber": "<:treasure_amulet:1290847574315499530>",
  "treasure_bottle": "<:treasure_bottle:1290847840397951047>",
  "treasure_card": "<:treasure_card:1290847890545180682>",
  "treasure_clover": "<:treasure_clover:1290847782906761277>",
  "treasure_die": "<:treasure_dice:1290847718566137979>",
  "treasure_journal": "<:treasure_journal:1290847480237391955>",
  "treasure_pen": "<:treasure_feather:1290847530980212756>",
  "treasure_shirt": "<:treasure_novelty_shirt:1290848009315287090>",
  "treasure_sun": "<:treasure_sun:1290847647372017786>",

  # Progress Bars
  # Music
  "bar_empty_start": '<:bar_empty_start:1280362762651828255>',
  "bar_empty_middle": '<:bar_empty_middle:1280362590379446293>',
  "bar_empty_end": '<:bar_empty_end:1280362634591338537>',
  "bar_filled_middle": '<:bar_filled_middle:1280362609648074792>',
  "bar_filled_start": '<:bar_filled_start:1280362778946699275>',
  "bar_filled_end": '<:bar_filled_end:1280362656364105800>',

  # Nikogotchi
  "progress_filled_start": "<:progress_filled_start:1291069871181922448>",
  "progress_filled_middle": "<:progress_filled_middle:1291069976769200209>",
  "progress_filled_end": "<:progress_filled_end:1291070082998341642>",
  "progress_empty_start": "<:progress_empty_start:1291069773739982901>",
  "progress_empty_middle": "<:progress_empty_middle:1291069936927637565>",
  "progress_empty_end": "<:progress_empty_end:1291070042095616041>",
}
# replaces all names with "i" for more embed/message space
emojis = {key: re.sub(r'(?<=[:])\w+(?=:\d)', 'i', value) for key, value in emojis.items()}
