import os
import interactions
from utilities.config import debugging, get_config
loaded_modules = []

def load_modules(client: interactions.Client):
	global loaded_modules
	loaded_modules = []

	files = [f for f in os.listdir('bot/modules') if f != '__pycache__']
	modules = [f.replace('.py', '') for f in files]

	if not get_config("music.enabled"):
		modules = [module for module in modules if module != 'music']

	if debugging():
		print("Loading modules")
	else:
		print("Loading modules ... \033[s", flush=True)
	for module in modules:
		if debugging():
			print("| " + module)
		client.load_extension(f"modules.{module}")
		loaded_modules.append(module)

	if not debugging():
		print("\033[udone ({})".format(len(loaded_modules)), flush=True)
		print("\033[999B", end="", flush=True)
	else:
		print(f"Done ({len(loaded_modules)})")



def reload_modules(client: interactions.Client):
	global loaded_modules

	if len(loaded_modules) > 0:
		_loaded_modules = loaded_modules
		loaded_modules = []
		print(f"Reloading modules...")
		for module in _loaded_modules:
			print("| "+module)
			client.reload_extension(f"modules.{module}")
			loaded_modules.append(module)

	print(f"Done ({len(loaded_modules)})")
	return loaded_modules