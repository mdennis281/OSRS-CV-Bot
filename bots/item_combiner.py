# ruff: noqa: BLE001
from bots.core import BotConfigMixin
from bots.core.cfg_types import RangeParam, BreakCfgParam, RGBParam, ItemParam
from core.bot import Bot
from core.logger import get_logger
from core.bank import BankInterface
from core.item_db import ItemLookup
from core.control import ScriptControl

import time
import random

control = ScriptControl()


class BotConfig(BotConfigMixin):
    base_item: ItemParam = ItemParam("Battlestaff")
    second_item: ItemParam = ItemParam("Water orb")
    result_item: ItemParam = ItemParam("Water battlestaff")

    combine_stack_size: int = 14
    bank_tile: RGBParam = RGBParam.from_tuple((0, 255, 0))
    randomize_withdraw_order: bool = True
    combine_confirm_key: str = "space"

    break_cfg: BreakCfgParam = BreakCfgParam(
        RangeParam(15, 45),  # break duration range in seconds
        0.01     # break chance
    )


class BotExecutor(Bot):
    name: str = "Item Combiner"
    description: str = "Combines two items (e.g., Battlestaff + Water orb)."
    tier: str = "A"
    instructions: str = """
    This bot combines two specified items from the bank into a resulting item by clicking them in the inventory.
    It needs the bank tile set and the bank pin entered.
    It also needs both items to be visible when the bank is opened.
    
    Theres issues with the architecture of this bot, making it a bit dumb (AI generated).
    
    Known bugs:
        - On occasion, i see it randomly start walking around, clicking randomly.
        This issue exclusively happens on startup, just restart the script and it should be fine.
    """
    
    def __init__(self, config: BotConfig, user: str = ""):
        super().__init__(user, break_cfg=config.break_cfg)
        self.cfg: BotConfig = config
        self.log = get_logger("ItemCombiner")

        self.itemdb = ItemLookup()
        self.bank = BankInterface(self.client, self.itemdb)
        
        # Prepared-inventory state
        self.first_item: str | None = None
        self.base_items: list = []
        self.second_items: list = []
        self.result_before: int = 0

    def start(self):
        self.loop()

    def loop(self):
        max_failures = 5
        backoff_base = 1.0
        while True:
            total = self._init_counts()
            if total <= 0:
                self.log.info("No items left to combine. Exiting.")
                return
            self.log.info("Preparing to combine up to %s items", total)

            consecutive_failures = 0
            while total > 0:
                if not self._routine():
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        self.log.error("Too many routine failures; re-checking bank and counts.")
                        break
                    delay = min(8.0, backoff_base * (2 ** (consecutive_failures - 1))) + random.uniform(0, 0.5)
                    self.log.warning("Routine failed; retrying in %.1fs... (%s/%s)", delay, consecutive_failures, max_failures)
                    time.sleep(delay)
                    continue
                consecutive_failures = 0
                total = max(0, total - self.cfg.combine_stack_size)
                self.log.info("%s items remaining", total)

    # --- Internals ---
    def _open_bank(self, max_attempts: int = 3, timeout: float = 10.0) -> bool:
        attempts = 0
        while attempts < max_attempts:
            self.client.smart_click_tile(self.cfg.bank_tile, ["bank"])
            start = time.time()
            while not self.bank.is_open and (time.time() - start) < timeout:
                time.sleep(0.25)
            if self.bank.is_open:
                return True
            attempts += 1
            self.log.warning("Bank failed to open (attempt %s/%s); retrying...", attempts, max_attempts)
        self.log.error("Unable to open bank after multiple attempts.")
        return False

    def _init_counts(self) -> int:
        if not self.bank.is_open:
            if not self._open_bank():
                self.log.error("Cannot open bank to initialize counts.")
                return 0
        a = self.bank.get_item_count(self.cfg.base_item.name)
        b = self.bank.get_item_count(self.cfg.second_item.name)
        self.log.info("%s: %s | %s: %s", self.cfg.base_item.name, a, self.cfg.second_item.name, b)
        self.bank.set_default_quantity(14)
        self.bank.set_withdraw_setting('item')
        self.bank.close()
        return min(a, b)

    # ---------- Inventory helpers ----------
    def _inv_count(self, name: str) -> int:
        return len(self.client.get_inv_items([name]))

    def _has_both_in_inv(self) -> bool:
        return (
            self._inv_count(self.cfg.base_item.name) > 0 and
            self._inv_count(self.cfg.second_item.name) > 0
        )

    def _choose_first_item(self) -> str:
        items = [self.cfg.base_item.name, self.cfg.second_item.name]
        if self.cfg.randomize_withdraw_order:
            random.shuffle(items)
        return items[0]

    def _prepare_inventory(self) -> None:
        """Prepare inventory with both required items.
        Updates:
            self.first_item, self.base_items, self.second_items, self.result_before
        """
        base_name = self.cfg.base_item.name
        second_name = self.cfg.second_item.name
        result_name = self.cfg.result_item.name

        # If both items already present, skip banking/deposit entirely
        if self._has_both_in_inv():
            self.first_item = self._choose_first_item()
            self.base_items = self.client.get_inv_items([base_name], x_sort=True, y_sort=True)
            self.second_items = self.client.get_inv_items([second_name], x_sort=True, y_sort=True)
            self.result_before = self._inv_count(result_name)
            return

        # Otherwise use bank flow
        if not self.bank.is_open and not self._open_bank():
            raise RuntimeError("Unable to open bank to prepare items")

        # Deposit then withdraw required stacks (only when both aren't already in inv)
        self.bank.deposit_inv()
        order = [base_name, second_name]
        if self.cfg.randomize_withdraw_order:
            random.shuffle(order)
        for item in order:
            self.bank.withdraw(item, self.cfg.combine_stack_size)

        # Close bank to proceed
        if self.bank.is_open:
            self.bank.close()

        # Re-scan inventory and set state
        self.base_items = self.client.get_inv_items([base_name], x_sort=True, y_sort=True)
        self.second_items = self.client.get_inv_items([second_name], x_sort=True, y_sort=True)
        self.result_before = self._inv_count(result_name)
        self.first_item = order[0]

    def _click_pair(self, base_items, second_items, first_item: str):
        base_name = self.cfg.base_item.name
        second_name = self.cfg.second_item.name
        if not base_items or not second_items:
            raise RuntimeError("Missing items in inventory after preparation")
        base = base_items[0 if first_item == base_name else -1]
        second = second_items[0 if first_item == second_name else -1]
        to_click = [base, second]
        #random.shuffle(to_click)
        self.client.click(to_click[1])
        self.client.click(to_click[0])
        return base, second

    def _confirm_action(self):
        time.sleep(random.uniform(0.5, 1.0))
        try:
            import keyboard
            keyboard.press_and_release(self.cfg.combine_confirm_key)
        except (RuntimeError, ValueError, OSError) as e:
            self.log.warning("Unable to send keypress '%s': %s", self.cfg.combine_confirm_key, e)

    def _wait_for_crafting(self, base_before: int, second_before: int, result_before: int) -> bool:
        target_pairs = min(base_before, second_before, self.cfg.combine_stack_size)
        start_time = time.time()
        last_progress = start_time
        max_wait = 120.0
        stall_timeout = 6.0
    # retriggered flag not needed; retry handled inline

        def crafted_so_far() -> int:
            return max(0, self._inv_count(self.cfg.result_item.name) - result_before)

        crafted = crafted_so_far()
        while crafted < target_pairs:
            if time.time() - start_time > max_wait:
                self.log.error("Crafting timed out.")
                return False
            self.log.info("Crafted %s/%s so far", crafted, target_pairs)
            time.sleep(3)
            new_crafted = crafted_so_far()
            if new_crafted > crafted:
                crafted = new_crafted
                last_progress = time.time()
                continue
            if time.time() - last_progress > stall_timeout:
                return False
        return True

    @control.guard
    def _routine(self) -> bool:
        try:
            # Prepare inventory and pick click order
            self._prepare_inventory()
            self.client.move_off_window()

            # Click the pair and confirm
            self._click_pair(self.base_items, self.second_items, self.first_item)
            self._confirm_action()
            self.client.move_off_window()

            # Wait with retry-on-stall once if no progress
            base_before = len(self.base_items)
            second_before = len(self.second_items)
            ok = self._wait_for_crafting(base_before, second_before, self.result_before)
            if not ok:
                self.log.warning("No crafting progress detected; attempting one re-trigger.")
                self._prepare_inventory()
                self._click_pair(self.base_items, self.second_items, self.first_item)
                time.sleep(random.uniform(0.3, 0.7))
                self._confirm_action()
                self.client.move_off_window()
                ok = self._wait_for_crafting(base_before, second_before, self.result_before)
                if not ok:
                    self.log.warning("No crafting progress after retry; aborting this stack.")
                    return False

            self.control.propose_break()
            return True
        except (RuntimeError, ValueError, OSError) as e:
            self.log.error("Routine error: %s", e)
            return False
