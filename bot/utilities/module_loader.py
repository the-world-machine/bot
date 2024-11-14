import os
import interactions
from utilities.config import get_config
loaded_modules = []

def reload_modules(client: interactions.Client, message: interactions.Message = None):

    files = [f for f in os.listdir('bot/modules') if f != '__pycache__']
    modules = [f.replace('.py', '') for f in files]
    
    if not get_config("music.enabled"):
        modules = [module for module in modules if module != 'music']
    print(f"Loading modules...")
    for module in modules:
        print("| "+module)
        client.load_extension(f"modules.{module}")
        loaded_modules.append(module)
    print(f"Done ({len(loaded_modules)})")
