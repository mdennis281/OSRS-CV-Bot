from core.osrs_client import RuneLiteClient
from core import tools
from PIL import Image

# load into memory now for faster loads
BANK_BR = Image.open('data/ui/bank-bottom-right.png')
BANK_TL = Image.open('data/ui/bank-top-left.png')

class BankInterface:
    def __init__(self,client:RuneLiteClient):
        self.client = client
        self.bank_match: tools.MatchResult = None

    @property
    def is_open(self):
        try:
            self.get_match()
            return True
        except:
            return False
        
    def deposit_inv():
        pass # IMPLEMENT DUMMY


    def get_match(self) -> tools.MatchResult:
        sc = self.client.get_screenshot()
        tl = self.client.find_in_window(BANK_TL, sc, min_scale=1,max_scale=1)
        br = self.client.find_in_window(BANK_BR, sc, min_scale=1,max_scale=1)

        for m in [tl,br]:
            if m.confidence < .96:
                raise ValueError('Bank is probably not open')
            
        self.bank_match = tools.MatchResult(
            start_x=tl.start_x,
            start_y=tl.start_y,
            end_x=br.end_x,
            end_y=br.end_y
        )
        return self.bank_match

