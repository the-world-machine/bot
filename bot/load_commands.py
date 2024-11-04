import os
import interactions
from data.config import get_config

def load_commands(client: interactions.Client):

    files = [f for f in os.listdir('bot/modules') if f != '__pycache__']
    modules = [f.replace('.py', '') for f in files]
    
    if not get_config("music.enabled"):
        modules = [module for module in modules if module != 'music']  # Assuming the music module is named 'music.py'

    # Load each module using the client.load method
    for module in modules:
        client.load_extension(f"modules.{module}") 

    print(f"Loaded {len(modules)} modules.")