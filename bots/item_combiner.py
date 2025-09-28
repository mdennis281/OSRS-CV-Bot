from bots.core import BotConfigMixin
from bots.core.cfg_types import BooleanParam, StringParam, IntParam, FloatParam, RGBParam, RangeParam, BreakCfgParam
from core.bot import Bot
from core.logger import get_logger
from core.bank import BankInterface
from core.item_db import ItemLookup
from core import tools
from core.control import ScriptControl

import time
import random

control = ScriptControl()


class BotConfig(BotConfigMixin):
    name: str = "Item Combiner"
    description: str = "Combines two items (e.g., Battlestaff + Water orb)."

    base_item_name: StringParam = StringParam("Battlestaff")
    second_item_name: StringParam = StringParam("Water orb")
    result_item_name: StringParam = StringParam("Water battlestaff")

    combine_stack_size: IntParam = IntParam(14)
    bank_tile: RGBParam = RGBParam(0, 255, 0)
    randomize_withdraw_order: BooleanParam = BooleanParam(True)
    combine_confirm_key: StringParam = StringParam("space")

    break_cfg: BreakCfgParam = BreakCfgParam(
        RangeParam(15, 45),  # break duration range in seconds
        FloatParam(0.01)     # break chance
    )


class BotExecutor(Bot):
    def __init__(self, config: BotConfig, user: str = ""):
        super().__init__(user, break_cfg=config.break_cfg)
        self.cfg: BotConfig = config
        self.log = get_logger("ItemCombiner")

        self.itemdb = ItemLookup()
        self.bank = BankInterface(self.client, self.itemdb)

    def start(self):
        self.loop()

    def loop(self):
        while True:
            total = self._init_counts()
            if total <= 0:
                self.log.info("No items left to combine. Exiting.")
                return
            self.log.info(f"Preparing to combine up to {total} items")

            while total > 0:
                if not self._routine():
                    self.log.warning("Routine failed; retrying...")
                    continue
                total -= self.cfg.combine_stack_size.value
                self.log.info(f"{total} items remaining")

    # --- Internals ---
    def _open_bank(self):
        self.client.smart_click_tile(self.cfg.bank_tile.value, ["bank"])
        start = time.time()
        while not self.bank.is_open:
            if time.time() - start > 8:
                self.log.warning("Still waiting for bank to open...")
                start = time.time()
            time.sleep(0.25)

    def _init_counts(self) -> int:
        if not self.bank.is_open:
            self._open_bank()
        a = self.bank.get_item_count(self.cfg.base_item_name.value)
        b = self.bank.get_item_count(self.cfg.second_item_name.value)
        self.log.info(f"{self.cfg.base_item_name.value}: {a} | {self.cfg.second_item_name.value}: {b}")
        return min(a, b)

    def _get_items(self) -> str:
        """Deposits inventory and withdraws a stack of each item. Returns the item withdrawn first."""
        self.bank.deposit_inv()
        items = [self.cfg.base_item_name.value, self.cfg.second_item_name.value]
        if self.cfg.randomize_withdraw_order.value:
            random.shuffle(items)
        for item in items:
            self.bank.withdraw(item, self.cfg.combine_stack_size.value)
        return items[0]
    
    @control.guard
    def _routine(self) -> bool:
        try:
            if not self.bank.is_open:
                self._open_bank()
            first_item = self._get_items()
            self.bank.close()
            self.client.move_off_window()

            # Find the inventory items and decide click order similar to legacy logic
            base_items = self.client.get_inv_items([self.cfg.base_item_name.value], x_sort=True, y_sort=True)
            second_items = self.client.get_inv_items([self.cfg.second_item_name.value], x_sort=True, y_sort=True)

            if not base_items or not second_items:
                self.log.error("Missing items in inventory after withdrawal.")
                return False

            base = base_items[0 if first_item == self.cfg.base_item_name.value else -1]
            second = second_items[0 if first_item == self.cfg.second_item_name.value else -1]

            to_click = [base, second]
            random.shuffle(to_click)

            self.client.click(to_click[0])
            self.client.click(to_click[1])

            time.sleep(random.uniform(0.5, 1.0))

            # Confirm the combination (default: press space)
            try:
                import keyboard
                keyboard.press_and_release(self.cfg.combine_confirm_key.value)
            except Exception as e:
                self.log.warning(f"Unable to send keypress '{self.cfg.combine_confirm_key.value}': {e}")

            self.client.move_off_window()

            # Wait until the result stack is crafted
            target = self.cfg.combine_stack_size.value
            tot = len(self.client.get_inv_items([self.cfg.result_item_name.value]))
            while tot < target:
                self.log.info(f"Crafted {tot} so far")
                time.sleep(3)
                tot = len(self.client.get_inv_items([self.cfg.result_item_name.value]))

            return True
        except Exception as e:
            self.log.error(f"Routine error: {e}")
            return False
