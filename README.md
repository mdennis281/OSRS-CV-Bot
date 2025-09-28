# auto_rs
 osrs automation using screenshots, template matching & OCR


 ## Demos

 ### Item Combiner
 [item_combiner.py](./bots/item_combiner.py)
 ![Image](https://github.com/user-attachments/assets/fc156ceb-8d87-4191-bf97-85e884b86972)

 ### Rooftop Agility
 [agility.py](./bots/agility.py)
 ![Image](https://github.com/user-attachments/assets/226daf47-361a-433d-89e3-dad1afb1c87a)

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