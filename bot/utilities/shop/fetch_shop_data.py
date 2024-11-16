from datetime import datetime
import random

from database import fetch_items, update_shop
from utilities.config import get_config
from utilities.localization import Localization
from dataclasses import dataclass

@dataclass
class DictItem:
    nid: str
    cost: int
    image: str
    type: int
        
@dataclass
class Item:        
    cost: int
    image: int
    id: str

@dataclass
class ShopData:
    
    last_updated: datetime
    background_stock: list[DictItem]
    treasure_stock: list[DictItem]
    stock_price: float
    stock_value: float
    motd: int

async def fetch_shop_data():
    
    items = await fetch_items()
     
    shop_data = ShopData(
        items['shop']['last_updated'],
        items['shop']['backgrounds'],
        items['shop']['treasures'],
        items['shop']['stock']['price'],
        items['shop']['stock']['value'],
        items['shop']['motd']
    )
    
    return shop_data

async def reset_shop_data():
    
    items = await fetch_items()
    data = items['shop']
    
    all_bgs = items['backgrounds']
    backgrounds = {}
    
    for bg in all_bgs:
        if all_bgs[bg]['purchasable']:
            backgrounds[bg] = all_bgs[bg]
        
    treasures = items['treasures']
    motds = Localization.sl('shop.motds', locale=get_config('localizations.main-locale'))
    
    data['backgrounds'] = []
    data['treasures'] = []
    
    n_backgrounds = random.sample(list(backgrounds.keys()), 3)
    n_treasures = random.sample(list(treasures.keys()), 3)
    
    data['backgrounds'] = n_backgrounds
    data['treasures'] = n_treasures
    data['motd'] = random.randint(0, len(motds) - 1)
    
    now = datetime.now()
    
    data['last_updated'] = datetime(now.year, now.month, now.day, hour=0, minute=0, second=0)
    
    is_positive = random.choice([True, False])
    
    if data['stock']['price'] < 0.5:
        is_positive = True
    
    if data['stock']['price'] > 1.5:
        is_positive = False
    
    if is_positive:
        data['stock']['value'] = round(random.uniform(0.3, 0.7), 1)
    else:
        data['stock']['value'] = round(random.uniform(-0.3, -0.7), 1)    
    
    price_change = data['stock']['price'] + data['stock']['value']
    
    data['stock']['price'] = round(min(2, max(0.2, price_change)), 1)
    
    await update_shop(data)
    
    return await fetch_shop_data()