
from core.osrs_client import RuneLiteClient
from core import tools

#not ready :(
rl_client = RuneLiteClient()

def main():
    do_smith()
    


def do_smith():
    furnace = tools.find_color_box(
        rl_client.get_screenshot(),
        (200,150,200)
    )
    bank = tools.find_color_box(
        rl_client.get_screenshot(),
        (0,255,0)
    )
    print(furnace)
    m = furnace.debug_draw(rl_client.screenshot)
    m = bank.debug_draw(m,color='blue')
    #rl_client.click(furnace)
    m.show()

main()