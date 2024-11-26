import os
import interactions
from utilities.config import debugging, get_config
loaded_modules = []

def load_modules(client: interactions.Client, unload: bool=False, print=print):
	global loaded_modules
	loaded_modules = []

	files = [f for f in os.listdir('bot/modules') if f != '__pycache__']
	modules = [f.replace('.py', '') for f in files]

	if not get_config("music.enabled"):
		modules = [module for module in modules if module != 'music']

	if debugging():
		print("Loading modules" if not unload else "Reloading modules")
	else:
		print(("Loading modules" if not unload else "Reloading modules") + " ... \033[s", flush=True)
	for module in modules:
		if unload: 
			client.unload_extension(f"modules.{module}")
		if debugging():
			print("| " + module)
		client.load_extension(f"modules.{module}")
		loaded_modules.append(module)

	if not debugging():
		print("\033[udone ({})".format(len(loaded_modules)), flush=True)
		print("\033[999B", end="", flush=True)
	else:
		print(f"Done ({len(loaded_modules)})")