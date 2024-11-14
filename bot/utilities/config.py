import yaml
from utilities.misc import rabbit

with open('bot-config.yml', 'r') as f:
    config = yaml.safe_load(f)
    print("Loaded configuration")

def get_config(path: str, data=config, ignore_None: bool = False):
    return rabbit(value=data, raw_path=path, raise_on_not_found=ignore_None, _error_message="Configuration does not have [path]")