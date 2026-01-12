# Old-school RuneScape Computer Vision Bot
A vibe coding experiment that has grown into a pretty impressive botting framework.

I wouldn't recommend using this if you aren't willing to get your hands dirty writing some python.

 > Offically support for **Windows** only, sorry


 ## Demos

 ### Item Combiner -  [item_combiner.py](./bots/item_combiner.py)

https://github.com/user-attachments/assets/8d7b6eb6-8b16-466c-b32c-9fde9a23fa37

 ### Rooftop Agility - [agility.py](./bots/agility.py)

https://github.com/user-attachments/assets/226daf47-361a-433d-89e3-dad1afb1c87a

### New UI
> Still a bit buggy
![Control UI](https://private-user-images.githubusercontent.com/16827865/534314440-f62f9af1-29c6-4eb1-bd5b-223546f0e120.png?jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NjgyMzk2OTMsIm5iZiI6MTc2ODIzOTM5MywicGF0aCI6Ii8xNjgyNzg2NS81MzQzMTQ0NDAtZjYyZjlhZjEtMjljNi00ZWIxLWJkNWItMjIzNTQ2ZjBlMTIwLnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNjAxMTIlMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjYwMTEyVDE3MzYzM1omWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTg2MmYxNDAxNGJjN2Y4Nzg0N2ZkOTBhOTQ4MGY2MTY1MzM0MzZiMjJjYWFmNjZjODBlYjAzM2MzYWI1MDc0NTMmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.Osj9hQSlyQuVI2242Xo1u3ARMYWYFnKCzQ4O7WrgVz0)
![Bots UI](https://private-user-images.githubusercontent.com/16827865/534703037-7b63ebcd-78e7-46f5-94d2-e013b652be67.png?jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NjgyMzk4NzMsIm5iZiI6MTc2ODIzOTU3MywicGF0aCI6Ii8xNjgyNzg2NS81MzQ3MDMwMzctN2I2M2ViY2QtNzhlNy00NmY1LTk0ZDItZTAxM2I2NTJiZTY3LnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNjAxMTIlMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjYwMTEyVDE3MzkzM1omWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTRhNjAyNDViN2ViY2U0NTJjYWMxZDAyYmVjZDk0YTY1N2YxNzQzNmZlZDg1ZmRiMzRkMjg2YjBkN2JiNzFiNzcmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.5XQiqDI0OTiLweigpAUtq_r0GvqlrJZURS_WLT2NFHA)
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

NOTE: the bot script architecture is migrating from legacy (scripts defined in base dir) to the new bot architecture defined in [./bots](bots/). Invocation of the new architecture can be seen in [main.py](./main.py).

The new architecture has a core bot class defined here [Bot()](core/bot.py). This Bot() class is used as a way to have all the core components (RuneLiteClient(), ScriptControl(), MovementOrchestrator(), BankInterface(), ItemLookup()) all in one class.

Noteworthy scripts:
- [High Alchemy](./bots/high_alch.py)
- [Motherload Miner](./bots/motherload_miner.py)
- [Mastering Mixology](./bots/master_mixer.py)
- [Nightmare Zone](./bots/nmz.py)
