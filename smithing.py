
from core.osrs_client import RuneLiteClient
from core import tools
import time

#not ready :(
rl_client = RuneLiteClient()

def main():
    #do_smith()
    sc = rl_client.get_screenshot()
    for x in range(10):
        sc = rl_client.get_screenshot()
        tile = tools.find_color_box(
            sc,
            (0,255,0),
            x*10
        )
        tile.debug_draw(sc).show()
        time.sleep(10)


    
def walk_to_box(color, tolerance=40):
    sc = rl_client.get_screenshot()
    tile = tools.find_color_box(
        sc,
        color,
        tolerance
    )
    rl_client.click(tile)
    tile.debug_draw(sc).show()
    

def do_smith():
    walk_to_box((255,0,255))
    time.sleep(4)
    walk_to_box((0,255,0))
    time.sleep(4)
    walk_to_box((147,26,112))
    time.sleep(4)
    walk_to_box((0,255,255))


    # furnace = tools.find_color_box(
    #     rl_client.get_screenshot(),
    #     (200,150,200),
    #     tol=20
    # )
    # bank = tools.find_color_box(
    #     rl_client.get_screenshot(),
    #     (0,255,0), tol=20
    # )
    # print(furnace)
    # m = furnace.debug_draw(rl_client.screenshot)
    # m = bank.debug_draw(m,color='blue')
    # #rl_client.click(furnace)
    # m.show()

main()