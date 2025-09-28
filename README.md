# Old-school RuneScape Computer Vision Bot
A vibe coding experiment that has grown into a pretty impressive botting framework.


 ## Demos

 ### Item Combiner -  [item_combiner.py](./bots/item_combiner.py)

https://github.com/user-attachments/assets/8d7b6eb6-8b16-466c-b32c-9fde9a23fa37

 ### Rooftop Agility - [agility.py](./bots/agility.py)

https://github.com/user-attachments/assets/226daf47-361a-433d-89e3-dad1afb1c87a

### Websocket controller
![Control UI](https://github.com/user-attachments/assets/380ee7a5-6360-4994-a758-f2374041b562)
![Log UI](https://github.com/user-attachments/assets/a3856f32-1587-4916-b95e-d03f7991546c)


### Computer Vision Debugger


![CV Debug](https://github.com/user-attachments/assets/c22cecd6-4a13-41e0-af44-196d6348a6df)

 ## Why arent the docs better?

I open sourced this for portfolio building, not script kiddies.

A competent dev should be able to get this working in a jiffy if theyre that interested.

NOTE: the bot script architecture is migrating from legacy (scripts defined in base dir) to the new bot architecture defined in [./bots](bots/). Invocation of the new architecture can be seen in [main.py](./main.py).

The new architecture has a core bot class defined here [Bot()](core/bot.py). This Bot() class is used as a way to have all the core components (RuneLiteClient(), ScriptControl(), MovementOrchestrator(), BankInterface(), ItemLookup()) all in one class.

Noteworthy scripts:
- [High Alchemy](./bots/high_alch.py)
- [Motherload Miner](./bots/motherload_miner.py)
- [Mastering Mixology](./bots/master_mixer.py)
- [Nightmare Zone](./bots/nmz.py)