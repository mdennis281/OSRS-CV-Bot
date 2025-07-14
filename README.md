# auto_rs
 osrs automation using screenshots, template matching & OCR

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