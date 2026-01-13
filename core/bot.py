from core.osrs_client import RuneLiteClient
from core.item_db import ItemLookup
from core.bank import BankInterface
from core.control import ScriptControl
from bots.core.cfg_types import BreakCfgParam
from core.movement import MovementOrchestrator
from core.api import BotAPI
from core.logger import get_logger
from core import cv_debug

class Bot:
    def __init__(self, user='', break_cfg: BreakCfgParam = None):
        self.log = get_logger(getattr(self, 'name', 'Bot'))
        self.control = ScriptControl()
        # Clear script control state on start
        self.control.reset()
        self.client = RuneLiteClient(user)
        self.itemdb = ItemLookup()
        self.bank = BankInterface(self.client, self.itemdb)
        self.mover = MovementOrchestrator(self.client)
        

        if break_cfg:
            self.control.break_config = break_cfg
        
        self.api = BotAPI(self.client)
        # Always enable CV debug for bot monitoring
        debug_port = 5555  # Fixed port for CV debug
        if not cv_debug._enabled:
            cv_debug.enable(port=debug_port)
            self.log.info(f"CV Debug enabled on port {debug_port}")
        
        # Store debug port in API for endpoint use
        self.api._debug_port = debug_port
        
        self.api.start(port=5432)
        
        
    @property
    def terminate(self) -> bool:
        return self.control.terminate

    @terminate.setter
    def terminate(self, value: bool):
        self.control.terminate = value