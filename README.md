# Old-school RuneScape Computer Vision Bot
A vibe coding experiment that has grown into a pretty impressive botting framework.

I wouldn't recommend using this if you aren't willing to get your hands dirty writing some python.

 > Official support for **Windows** only, sorry

 ## Setup

 - Play using the runelite client, on windows OS
 - Install python >=3.10
 - Clone repo
 - Open powershell, cd into cloned directory
 - Run:
 ```bash
python -m pip install virtualenv
python -m venv venv
./venv/Scripts/Activate.ps1
pip install -r requirements.txt

python main.py
 ```


 ## Demos

 ### Item Combiner -  [item_combiner.py](./bots/item_combiner.py)

https://github.com/user-attachments/assets/8d7b6eb6-8b16-466c-b32c-9fde9a23fa37

 ### Rooftop Agility - [agility.py](./bots/agility.py)

https://github.com/user-attachments/assets/226daf47-361a-433d-89e3-dad1afb1c87a

### New UI

> Still a bit buggy

![Control UI](https://private-user-images.githubusercontent.com/16827865/534314440-f62f9af1-29c6-4eb1-bd5b-223546f0e120.png?jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NjkwMDcwMjMsIm5iZiI6MTc2OTAwNjcyMywicGF0aCI6Ii8xNjgyNzg2NS81MzQzMTQ0NDAtZjYyZjlhZjEtMjljNi00ZWIxLWJkNWItMjIzNTQ2ZjBlMTIwLnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNjAxMjElMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjYwMTIxVDE0NDUyM1omWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTk5N2RhOGUzNDY4ZWNkNDU3NGZlMmI4NzM1OGQyMDFiNTU5MDgxMDU5YTE5NDI1ZWIzNjAzMmIzYzA2MTQwNzEmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.wIgqzZiaVITqVKw2RnDnz3e12eeRMDzWSfCGm6A1AaI)
![Config UI](https://private-user-images.githubusercontent.com/16827865/534314697-991f52c1-dbc1-442d-8e56-b370007e7bce.png?jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NjgyMzk2OTMsIm5iZiI6MTc2ODIzOTM5MywicGF0aCI6Ii8xNjgyNzg2NS81MzQzMTQ2OTctOTkxZjUyYzEtZGJjMS00NDJkLThlNTYtYjM3MDAwN2U3YmNlLnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNjAxMTIlMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjYwMTEyVDE3MzYzM1omWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTgxOTk2OTZmNmIxYTRjMmFlZDI0ZTJkMTY5MTU1ZTZlOTNkMTU1ZjczNGJkNTZiZjI0ZjA5ZTljZGViOWE1ZjMmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.cGCKS0qKy619h5zWg36ZOHkA1hi5zovOX0mfkWYFGOk)


### Computer Vision Debugger


![CV Debug](https://github.com/user-attachments/assets/c22cecd6-4a13-41e0-af44-196d6348a6df)

 ## Install
Full UI experience
```bash
python -m pip install -r requirements.txt
python main.py
```



Direct bot invocation (need this for bots with complex params ie. list of items):
Create new file
```python
# update bot script here
from bots.master_mixer import BotConfig, BotExecutor


def main():
    config = BotConfig()
    bot = BotExecutor(config)
    
    bot.start()
    
main()
```

### Bot Hotkeys 
- **Page Up**: Terminate the bot immediately
- **Page Down**: Pause/Resume the bot

NOTE: the bot script architecture is migrating from legacy (scripts defined in base dir) to the new bot architecture defined in [./bots](bots/). Invocation of the new architecture can be seen above.

The new architecture has a core bot class defined here [Bot()](core/bot.py). This Bot() class is used as a way to have all the core components (RuneLiteClient(), ScriptControl(), MovementOrchestrator(), BankInterface(), ItemLookup()) all in one class.

Noteworthy scripts:
- [High Alchemy](./bots/high_alch.py)
- [Motherload Miner](./bots/motherload_miner.py)
- [Mastering Mixology](./bots/master_mixer.py)
- [Nightmare Zone](./bots/nmz.py)
