from bots.core import BotConfigMixin
from bots.core.cfg_types import RangeParam, BreakCfgParam, ItemParam, BooleanParam, RGBParam
from core.bot import Bot
from core.osrs_client import ToolplaneTab
from PIL import Image
import random
import time

class BotConfig(BotConfigMixin):
    # Configuration parameters
    planks_noted: ItemParam = ItemParam(8783) # mahogany plank (noted)
    planks_unnoted: ItemParam = ItemParam(8782) # mahogany plank
    phials_tile_color: RGBParam = RGBParam(0, 255, 255)
    portal_tile_color: RGBParam = RGBParam(255, 55, 255)
    table_tile_color: RGBParam = RGBParam(255, 55, 100)
    
    max_runtime_minutes: int = 180
    build_table_image_path: str = 'data/ui/mahogany-table-build.png'
    
    break_cfg: BreakCfgParam = BreakCfgParam(
        RangeParam(25, 122),  # break duration range
        0.01  # break chance
    )

class BotExecutor(Bot):
    name: str = "Mahogany Table Builder"
    tier: str = "B"
    description: str = "Builds and removes mahogany tables in POH for Construction XP."
    instructions: str = """
    Several people have verifiably gotten 99 construction with this bot. Going pretty heavy, no bans.
    That being said, the framework has changed a lot since this was achieved, may need tuning.
    
    Plugins required: 
    - 'Better NPC Highlight'
    - 'Tile Indicators'
    
    Setup:
    - Mark Tiles:
      [
        {"regionId":7513,"regionX":3,"regionY":11,"z":0,"color":"#FFFF37FF"},
        {"regionId":11826,"regionX":8,"regionY":24,"z":0,"color":"#FFFF37FF"},
        {"regionId":7513,"regionX":36,"regionY":60,"z":0,"color":"#FFFF3764"}
      ]
    - NPC highlight: 'Phials'
    - Swap left click build/remove on home portal and table tiles
    - Start outside house portal with bank pin entered
    - Inventory: Noted mahogany planks, money, saw, hammer
    - Camera: Max view distance, zoomed out, fit Phials and Portal on screen facing West.
    """
    
    def __init__(self, config: BotConfig, user=''):
        super().__init__(user, break_cfg=config.break_cfg)
        self.cfg: BotConfig = config
        self.start_time = time.time()
        self.table_img = Image.open(self.cfg.build_table_image_path)
        
    def start(self):
        self.log.info("Starting Mahogany Table Bot")
        self.init_bot()
        self.loop()
        
    def loop(self):
        while not self.terminate:
            self.timeout_check()
            
            if not self.planks_in_inventory():
                self.unnote_planks()
                
            # Enter house (Build mode)
            self.client.smart_click_tile(
                self.cfg.portal_tile_color.value,
                'Build'
            )
            
            self.control.propose_break()
            self.wait_while_moving()
            
            # Inside house loop - build tables until out of planks
            for _ in range(4):
                if not self.planks_in_inventory():
                    break
                
                self.control.propose_break()
                if self.terminate: break
                
                self.remove_table()
                time.sleep(1)
                self.build_table()
                
                # Check for termination after build cycle
                if self.terminate: break
            
            # Leave house
            self.control.propose_break()
            time.sleep(2)
            try:
                self.client.smart_click_tile(
                    self.cfg.portal_tile_color.value,
                    'Enter'
                )
            except Exception as e:
                self.log.error(f"Failed to leave house: {e}")
                
            self.wait_while_moving()

    def remove_table(self):
        try:
            self.client.smart_click_tile(
                self.cfg.table_tile_color.value,
                'Remove'
            )
            if self.terminate: return
            
            self.wait_while_moving()
            self.chat_text_clicker('Yes', 'Waiting for table removal dialog')
        except Exception as e:
            self.log.warning(f'table already missing? aight: {e}')

    def build_table(self):
        try:
            self.client.smart_click_tile(
                self.cfg.table_tile_color.value,
                'Build'
            )
            self.wait_while_moving()
        except Exception as e:
            self.log.error(f'couldnt find build button, lets assume it got pressed: {e}')
            
        time.sleep(1)
        self.select_mahogany_table()

    def select_mahogany_table(self):
        match = None
        for _ in range(3):
            if self.terminate: break
            try:
                match = self.client.find_in_window(
                    self.table_img,
                    min_confidence=.98
                )
                if match: break
            except Exception:
                self.log.warning('missed mahogany table build btn')
            
        if match:
            self.client.click(match)
        
        time.sleep(0.4)

    def unnote_planks(self, recurse=0):
        if recurse >= 3:
            raise ValueError('WTF Phails??')
            
        self.log.info(f"Unnoting planks at Phials (Attempt {recurse + 1})")
        done = False
        
        for _ in range(4):
            if self.planks_in_inventory():
                return
            if self.terminate: break
            
            # 1. Select noted planks
            try:
                # Use item on Phials
                # crop=(0,13,0,0) removes the top count number from the noted item to improve matching
                self.client.click_item(
                    self.cfg.planks_noted.id,
                    crop=(0,13,0,0), 
                    min_confidence=.87
                )
            except Exception as e:
                self.log.warning(f"wheres the noted planks: {e}")
                self.client.click_toolplane(ToolplaneTab.SKILLS) # Deselect/Reset
                self.client.move_off_window()
                time.sleep(random.randint(1, 6))
                continue
                
            if self.terminate: break
            
            # 2. Click Phials
            try:
                self.client.smart_click_tile(
                    self.cfg.phials_tile_color.value,
                    'Phials',
                    retry_hover=2,
                    retry_match=10
                )
            except Exception as e:
                self.log.warning(f"phials match miss: {e}")
                self.client.click_toolplane(ToolplaneTab.SKILLS) # Deselect
                self.client.move_off_window()
                time.sleep(random.randint(1, 6))
                continue

            self.wait_while_moving()
            
            # 3. Handle Dialog
            try:
                if self.terminate: break
                self.chat_text_clicker("Exchange All:", "Waiting for Phials", tries=4)
                done = True
                break
            except Exception as e:
                self.log.warning(f"Phials is an elusive boi: {e}")
        
        if not done:
            raise RuntimeError('Phials evaded us :(')
        
        time.sleep(1)
        if not self.planks_in_inventory():
            self.log.warning('Apparently i didnt get planks :(')
            self.unnote_planks(recurse + 1)

    def planks_in_inventory(self) -> bool:
        # Check for unnoted planks.
        try:
            self.client.find_item(self.cfg.planks_unnoted.id, min_confidence=0.95)
            return True
        except:
            return False

    def chat_text_clicker(self, text, log_msg, wait=0.5, tries=8):
        done = False
        for _ in range(tries):
            if self.terminate: break
            try:
                time.sleep(wait)
                self.client.click_chat_text(text)
                done = True
                break
            except Exception:
                self.log.info(log_msg)
        
        if not done:
            raise RuntimeError(f'Could not find chat text {text}')

    def timeout_check(self):
        if (time.time() - self.start_time) / 60 > self.cfg.max_runtime_minutes:
            self.log.info("Max runtime reached. Terminating.")
            self.control.terminate = True

    def init_bot(self):
        # Initial housekeeping
        pass

    def wait_while_moving(self):
        while self.client.is_moving():
            if self.terminate: return
            time.sleep(0.1)
