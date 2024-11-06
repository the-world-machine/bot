<div align="center">
    <img src="https://avatars.githubusercontent.com/u/160534184?s=280&v=4" width="128" height="128">
</div>

# <div align="center"> The World Machine </div>

<div align="center">

### A discord bot based off the videogame OneShot, and built using the `interactions-py` library.

For more information on what you can do with this bot, check out our [website.](https://www.theworldmachine.xyz/invite)
</div>

---
## Contributing:

### Localization
In `bot/localization/locales` there are different localization files. Using `en_#.yaml` as a base, you are free to contribute your own language to the bot.
> As of right now, only the `/shop`, `/interact` and `/nikogotchi` commands support localization.

### Pull Requests
As with any other repo, pull requests and bug reporting is always welcomed.

### Crediting
Contributing in any way to the discord bot will have your name be put in the website's credits and a role assigned on the discord.

---
## Running your own instance:
### Step 0: Install Python 3.11.5
For Windows you can get the installer [here](https://www.python.org/downloads/release/python-3115/#:~:text=Full%20Changelog-,files,-Version), for Linux you can search for your package manager's solution.<br>

You can check which version of python you're running with this command
```commandline
C:\> python --version
Python 3.11.5
```

### Step 1: Download Dependencies.
To download dependencies, run this in your console:
```commandline
pip install -r requirements.txt
```
This should install all dependencies needed to run the bot.

### Step 2: config.yaml
In `bot/data` there is file called `example_config.yaml` which has information for APIs and other sensitive information that should be included. You need to create a file in the same directory called `config.yaml` with the information filled.

### Step 3: Running the bot.
If everything is done right, the bot should run.
