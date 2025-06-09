from core.osrs_client import RuneLiteClient
from core.item_db import ItemLookup
from core.bank import BankInterface
from core.control import ScriptControl
from bots.core.cfg_types import BreakCfgParam
from core.movement import MovementOrchestrator
from core.api import BotAPI
from core.logger import get_logger

class Bot:
    def __init__(self, user='', break_cfg: BreakCfgParam = None):
        self.log = get_logger("Bot")
        self.client = RuneLiteClient(user)
        self.itemdb = ItemLookup()
        self.bank = BankInterface(self.client, self.itemdb)
        self.mover = MovementOrchestrator(self.client)
        self.control = ScriptControl(break_cfg)
        
        self.api = BotAPI(self.client)
        self.api.start(port=5432)