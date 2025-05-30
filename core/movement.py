from core.osrs_client import RuneLiteClient, PlayerPosition
from bots.core.cfg_types import WaypointParam, RouteParam
from core.region_match import MatchResult, MatchShape
import random
import pyautogui
import time

class MovementOrchestrator:
    def __init__(self, client: RuneLiteClient):
        self.client = client
        self.route:RouteParam = None
        self.current_route = None
        self.minimap: MatchResult = client.minimap.map
        self.north: MatchResult = None
        self.east: MatchResult = None
        self.south: MatchResult = None
        self.west: MatchResult = None
        self.get_minimap_sectors()
        self._zoom_level = 0

    def get_minimap_sectors(self):
        m = self.minimap
        self.north = MatchResult(
            int(m.start_x + m.width / 2 - 10),
            int(m.start_y),
            int(m.start_x + m.width / 2 + 10),
            int(m.start_y + 20),
            shape=MatchShape.ELIPSE
        )
        self.south = MatchResult(
            int(m.start_x + m.width / 2 - 10),
            int(m.start_y + m.height - 20),
            int(m.start_x + m.width / 2 + 10),
            int(m.start_y + m.height),
            shape=MatchShape.ELIPSE
        )
        self.east = MatchResult(
            int(m.start_x + m.width - 20),
            int(m.start_y + m.height / 2 - 10),
            int(m.start_x + m.width),
            int(m.start_y + m.height / 2 + 10),
            shape=MatchShape.ELIPSE
        )
        self.west = MatchResult(
            int(m.start_x),
            int(m.start_y + m.height / 2 - 10),
            int(m.start_x + 20),
            int(m.start_y + m.height / 2 + 10),
            shape=MatchShape.ELIPSE
        )

    def set_minimap_zoom(self, zoom_level: int = 2):
        x,y = self.minimap.get_point_within()
        self.client.move_to((x,y))
        def do_zoom(i):
            amount = -(i * 600)
            
            pyautogui.scroll(amount, x,y)

        if not self._zoom_level:
            do_zoom(-5) # reset zoom to minimum

        amount = zoom_level - self._zoom_level
        do_zoom(amount)
        self._zoom_level = zoom_level


    def go_to_waypoint(self, waypoint: WaypointParam):
        position = self.client.get_position()

    
        
