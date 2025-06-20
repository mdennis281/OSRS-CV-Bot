from core.osrs_client import RuneLiteClient, PlayerPosition, ClickType
from bots.core.cfg_types import WaypointParam, RouteParam, RGBParam
from core.region_match import MatchResult, MatchShape
from core.logger import get_logger
import random
import pyautogui
import time
from core import tools
import math
import json
import pyperclip
from typing import List, Dict, Set
import itertools

GOOD_TILE_COLORS = [
    RGBParam(200, 67, 0),
    RGBParam(180, 0, 0),
    RGBParam(130, 75, 170),
    RGBParam(200, 40, 70),
    RGBParam(100, 90, 240),

]

class MovementOrchestrator:
    def __init__(self, client: RuneLiteClient):
        self.log = get_logger('MovementOrchestrator')
        self.client = client
        self.route:RouteParam = None
        self.current_route = None
        self.minimap: MatchResult = client.minimap.map
        self.north: MatchResult = None
        self.east: MatchResult = None
        self.south: MatchResult = None
        self.west: MatchResult = None
        self.north_east: MatchResult = None
        self.north_west: MatchResult = None
        self.south_east: MatchResult = None
        self.south_west: MatchResult = None
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
        self.north_east = MatchResult(
            int(m.start_x + m.width * 0.725),
            int(m.start_y + m.height * 0.125),
            int(m.start_x + m.width * 0.875),
            int(m.start_y + m.height * 0.275),
            shape=MatchShape.ELIPSE
        )
        self.north_west = MatchResult(
            int(m.start_x + m.width * 0.125),
            int(m.start_y + m.height * 0.125),
            int(m.start_x + m.width * 0.275),
            int(m.start_y + m.height * 0.275),
            shape=MatchShape.ELIPSE
        )
        self.south_east = MatchResult(
            int(m.start_x + m.width * 0.725),
            int(m.start_y + m.height * 0.725),
            int(m.start_x + m.width * 0.875),
            int(m.start_y + m.height * 0.875),
            shape=MatchShape.ELIPSE
        )
        self.south_west = MatchResult(
            int(m.start_x + m.width * 0.125),
            int(m.start_y + m.height * 0.725),
            int(m.start_x + m.width * 0.275),
            int(m.start_y + m.height * 0.875),
            shape=MatchShape.ELIPSE
        )

    def get_position(self, verify=False) -> PlayerPosition:
        """
        Returns the current player position.
        """
        if verify: # TODO: articulate what you wanna do here
            while self.client.is_moving():
                continue
            p1 = self.client.get_position()
            p2 = self.client.get_position()
            if p1 != p2:
                raise ValueError("Player position is not stable, retrying...")
            return p1
            

        return self.client.get_position()

    def debug_minimap_sectors(self):
        """
        Debug function to visualize the minimap sectors.
        """
        sc = self.client.get_screenshot()
        for sector in [
            self.north, self.south, self.east, self.west,
            self.north_east, self.north_west, self.south_east, self.south_west
        ]:
            sc = sector.debug_draw(sc, color='red')
        sc.show()
        

    def set_minimap_zoom(self, zoom_level: int = 2):
        self.log.debug(f"Setting minimap zoom level to {zoom_level} was {self._zoom_level}")
        x,y = self.minimap.get_center()
        x += random.randint(-10, 10)
        y += random.randint(-10, 10)
        self.client.move_to((x,y))
        time.sleep(random.uniform(0.1, 0.3))
        def do_zoom(i):
            amount = -(i * 600)
            
            pyautogui.scroll(amount, x,y)

        if not self._zoom_level:
            do_zoom(-5) # reset zoom to minimum

        amount = zoom_level - self._zoom_level
        do_zoom(amount)
        self._zoom_level = zoom_level

    def get_tile_diff(self, waypoint: WaypointParam) -> tuple[int, int]:
        """
        Returns the difference in x and y coordinates between the current position and the waypoint.
        """
        x, y, _ = self.get_position().tile
        dx = waypoint.x - x
        dy = waypoint.y - y
        return dx, dy
    
    def push_to_clipboard(self, tiles: List['TileValue']):
        """
        Pushes a list of tiles to the clipboard as JSON in the format:
        [{"regionId":11826,"regionX":8,"regionY":24,"z":0,"color":"#FFFF37FF"}]
        """
        return 
        ground_markers = []
        for tile in tiles:
            ground_markers.append(tile.get_json())
        
        clipboard_data = json.dumps(ground_markers)
        pyperclip.copy(clipboard_data)
        self.log.info(f"Pushed {len(ground_markers)} ground markers to clipboard")
        return clipboard_data
    
    def pull_from_clipboard(self) -> List['TileValue']:
        """
        Pulls ground marker data from clipboard in the format:
        [{"regionId":11826,"regionX":8,"regionY":24,"z":0,"color":"#FFFF37FF"}]
        and returns as list of TileValue objects.
        """
        return
        def hex_to_rgb(hex_color):
            """Convert hex color string to RGB tuple."""
            # Remove the # prefix if present
            hex_color = hex_color.lstrip('#')
            
            # Extract RGB values
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
            elif len(hex_color) == 8:  # With alpha channel (RGBA)
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                # Alpha is ignored
            else:
                raise ValueError(f"Invalid hex color: {hex_color}")
                
            return r, g, b
            
        try:
            clipboard_data = pyperclip.paste()
            ground_markers = json.loads(clipboard_data)
            
            tiles = []
            for marker in ground_markers:
                # Extract values from the ground marker
                region_id = marker.get('regionId')
                region_x = marker.get('regionX')
                region_y = marker.get('regionY')
                z = marker.get('z', 0)
                hex_color = marker.get('color', '#FF4300')
                
                # Create RGB from hex color
                r, g, b = hex_to_rgb(hex_color)
                color = RGBParam(r, g, b)
                
                # Create waypoint
                waypoint = WaypointParam(
                    region_x, 
                    region_y,
                    z,
                    region_id,
                    tolerance=3
                )
                
                tiles.append(TileValue(waypoint, color))
            
            self.log.info(f"Pulled {len(tiles)} ground markers from clipboard")
            return tiles
        except (json.JSONDecodeError, ValueError) as e:
            self.log.error(f"Error parsing clipboard data: {str(e)}")
            return []
    
    def tile_import(self, tiles: List['TileValue']):
        
        self.push_to_clipboard(tiles)
        
        # self.client.smart_click_match(
        #     self.client.minimap.globe,
        #     ['floating','world', 'map'],
        #     retry_hover=6,
        #     click_type=ClickType.RIGHT
        # )
        # self.client.choose_right_click_opt('Import Ground Markers')



    def determine_direction(self, waypoint: WaypointParam) -> MatchResult:
        """
        Determines the direction to the waypoint based on the current position.
        Returns a MatchResult indicating the direction to click on the minimap.
        
        Note: In RuneScape's coordinate system:
        - X increases as you go east (higher X = further east)
        - Y increases as you go south (higher Y = further south)
        - So positive dx means move east, positive dy means move south
        """
        dx, dy = self.get_tile_diff(waypoint)

        scale = math.ceil(max(abs(dx), abs(dy)) / 8)
        scale = min(scale, 5)  # Limit zoom level to a maximum of 5
        self.set_minimap_zoom(scale)

        if abs(dx) < waypoint.tolerance and abs(dy) < waypoint.tolerance:
            return None

        # Prioritize the axis with the larger difference
        if abs(dx) > abs(dy):
            if dx > 0:  # Need to move east
                if dy > waypoint.tolerance:  # Need to move south too
                    self.log.debug(f"Moving south-east towards waypoint {waypoint}")
                    return self.north_east
                elif dy < -waypoint.tolerance:  # Need to move north too
                    self.log.debug(f"Moving north-east towards waypoint {waypoint}")
                    return self.south_east
                else:  # Only need to move east
                    self.log.debug(f"Moving east towards waypoint {waypoint}")
                    return self.east
            else:  # Need to move west
                if dy > waypoint.tolerance:
                    self.log.debug(f"Moving south-west towards waypoint {waypoint}")
                    return self.south_west
                elif dy < -waypoint.tolerance:
                    self.log.debug(f"Moving north-west towards waypoint {waypoint}")
                    return self.north_west
                else:
                    self.log.debug(f"Moving west towards waypoint {waypoint}")
                    return self.west
        else:
            if dy < 0:  # Need to move south (higher Y value)
                if dx > waypoint.tolerance:
                    self.log.debug(f"Moving south-east towards waypoint {waypoint}")
                    return self.south_east
                elif dx < -waypoint.tolerance:
                    self.log.debug(f"Moving south-west towards waypoint {waypoint}")
                    return self.south_west
                else:
                    self.log.debug(f"Moving south towards waypoint {waypoint}")
                    return self.south
            else:  # Need to move north (lower Y value)
                if dx > waypoint.tolerance:
                    self.log.debug(f"Moving north-east towards waypoint {waypoint}")
                    return self.north_east
                elif dx < -waypoint.tolerance:
                    self.log.debug(f"Moving north-west towards waypoint {waypoint}")
                    return self.north_west
                else:
                    self.log.debug(f"Moving north towards waypoint {waypoint}")
                    return self.north


    def execute_route(self, route: RouteParam):
        """
        Executes a route by moving to each waypoint in the route.
        """
        self.log.info(f"Executing route with {len(route.waypoints)} waypoints")
        self.route = route
        
        
        # Convert waypoints to TileValue objects with cycling colors
        route_tiles = []
        for i, waypoint in enumerate(route.waypoints):
            color_index = i % len(GOOD_TILE_COLORS)
            color = GOOD_TILE_COLORS[color_index]
            route_tiles.append(TileValue(waypoint, color))
        
        self.current_route = route_tiles
        
        # Import tiles for the route
        self.tile_import(route_tiles)
        
        # Execute the route
        self._do_route(route_tiles)

    
    def _get_tile_key(self, tile: 'TileValue') -> str:
        """Generate a unique key for a tile based on its position"""
        wp = tile.waypoint
        return f"{wp.chunk}:{wp.x}:{wp.y}:{wp.z}"
        
    def _do_route(self, tiles: List['TileValue']):
        """
        Execute a route by visiting each tile in sequence.
        """
        self.log.info(f"Executing route with {len(tiles)} tiles")
        
        for i, tile in enumerate(tiles):
            self.log.info(f"Moving to waypoint {i+1}/{len(tiles)}")
            self.go_to_waypoint(tile)
            
        self.log.info("Route execution completed")

    def go_to_waypoint(self, tile_value: 'TileValue') -> bool:
        """
        Move to a specific waypoint on the map.
        
        Args:
            tile_value (TileValue): The target waypoint and its color.
            
        Returns:
            bool: True if the waypoint was reached, False otherwise.
        """
        waypoint = tile_value.waypoint
        color = tile_value.color
        
        self.log.info(f"Moving to waypoint at ({waypoint.x}, {waypoint.y}) in chunk {waypoint.chunk}")
        
        max_attempts = 15  # Prevent infinite loops
        attempts = 0
        
        while attempts < max_attempts:
            # Check if we're already at the destination
            dx, dy = self.get_tile_diff(waypoint)
            if abs(dx) <= waypoint.tolerance and abs(dy) <= waypoint.tolerance:
                self.log.info(f"Reached waypoint ({waypoint.x}, {waypoint.y})")
                if self.client.is_moving():
                    # STOP moving
                    self.client.click(
                        self.client.minimap.map.get_center(),
                        rand_move_chance=0
                    )

                while self.client.is_moving():
                    time.sleep(0.1)
                dx, dy = self.get_tile_diff(waypoint)
                if abs(dx) >= waypoint.tolerance and abs(dy) >= waypoint.tolerance:
                    return self.go_to_waypoint(tile_value)  # Retry if still not at waypoint
                return True
            
            # If waypoint is very far, log a warning
            if max(abs(dx), abs(dy)) > 150:
                self.log.warning(f"Waypoint is very far away: dx={dx}, dy={dy}")
            
            try:
                # Determine direction to move
                direction_match = self.determine_direction(waypoint)
                
                if direction_match is None:
                    self.log.info(f"Already at destination or very close")
                    return True
                    
                self.log.debug(f"Moving in direction: dx={dx}, dy={dy}")
                self.client.click(direction_match)
                
                # Wait for player to start moving
                time.sleep(random.uniform(0.2, 0.5))
                
                # Wait for player to stop moving
                start_time = time.time()
                timeout = random.uniform(7,13)  # seconds
                while self.client.is_moving():
                    if time.time() - start_time > timeout:
                        self.log.warning("Timeout waiting for player to stop moving")
                        break
                
                
            except Exception as e:
                self.log.error(f"Error while navigating: {str(e)}")
                attempts += 1
                time.sleep(random.uniform(1.0, 2.0))
                continue
                
            attempts += 1
        
        self.log.warning(f"Failed to reach waypoint after {max_attempts} attempts")
        return False

class TileValue:
    def __init__(self, waypoint: WaypointParam, color: RGBParam):
        self.waypoint = waypoint
        self.color = color

    def get_json(self) -> dict:
        return self.waypoint.gen_tile(self.color)



