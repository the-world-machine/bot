from pathlib import Path
import yaml
from utilities.misc import rabbit

bcpath = Path("bot-config.yml")
try:
    with open(bcpath, 'r') as f:
        config = yaml.safe_load(f)
        print("Loaded configuration")
except FileNotFoundError as e:
    print(f"{bcpath.resolve()} was not found. Are you sure you set it up correctly?")
    exit(1)

def get_config(path: str, data=config, ignore_None: bool = False):
    return rabbit(value=data, raw_path=path, raise_on_not_found=ignore_None, _error_message="Configuration does not have [path]")