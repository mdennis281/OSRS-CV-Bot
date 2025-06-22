"""
region.py  – generic “selection” helpers             v2.0
───────────────────────────────────────────────────────────
* MatchResult : axis‑aligned rectangle / ellipse (your   old class)
* ShapeResult : arbitrary closed polygon (new)

Both inherit RegionMixin so all helpers (point‐inside, draw,
OCR, crop, transform, scale, …) live in one place.
Only the geometry‑specific primitives – `bounding_box()`,
`contains()`, and `outline()` – are implemented per subclass.
"""
from __future__ import annotations

import math, random, numpy as np, cv2
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable, List, Sequence, Tuple, Optional
from PIL import Image, ImageDraw

from core import ocr

# ────────────────────────────────
# 0.   shared mixin / base class
# ────────────────────────────────
class RegionMixin(ABC):
    # ---- geometry hooks (must be supplied by concrete class)
    @property 
    @abstractmethod
    def bounding_box(self) -> Tuple[int, int, int, int]:
        """(start_x, start_y, end_x, end_y) – inclusive RHS/open top‑left."""
    @abstractmethod
    def contains(self, x: int, y: int) -> bool:                          ...
    @abstractmethod
    def outline(self, pad_x: int = 0, pad_y: int = 0) -> Sequence[Tuple[int,int,int,int]]: ...

    # ---- helpers reused by *all* regions ----------------------------
    def get_point_within(self) -> Tuple[int, int]:
        """Uniform random integer pixel strictly inside region."""
        sx, sy, ex, ey = self.bounding_box
        if ex <= sx or ey <= sy:            # degenerate → top‑left
            return sx, sy
        while True:                         # rejection sample
            x, y = random.randint(sx, ex-1), random.randint(sy, ey-1)
            if self.contains(x, y):
                return x, y
            
    def get_center(self) -> Tuple[int, int]:
        """Get the center of the region (as a pixel coordinate)."""
        sx, sy, ex, ey = self.bounding_box
        if ex <= sx or ey <= sy:            # degenerate → top‑left
            return sx, sy
        return (sx + ex) // 2, (sy + ey) // 2

    def debug_draw(self, img: Image.Image, color="red",
                   padding_x: int = 0, padding_y: int = 0) -> Image.Image:
        """Visualise region on a PIL image."""
        draw = ImageDraw.Draw(img)
        for seg in self.outline(padding_x, padding_y):
            draw.line(seg, fill=color, width=2)
        return img

    def extract_number(self, img: Image.Image,
                       font=ocr.FontChoice.AUTO) -> str:
        """OCR of whatever is inside the region (same pipeline as before)."""
        sx, sy, ex, ey = self.bounding_box
        rgba = np.array(img.crop((sx, sy, ex, ey)))

        # 1. colour mask (yellow text in your RuneScape HUD)
        bgr = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv,
                           np.array([ 0,250,250], np.uint8),
                           np.array([65,255,255], np.uint8))
        isolated = cv2.bitwise_and(rgba, rgba, mask=mask)

        # 2. binarise → OCR
        gray     = cv2.cvtColor(isolated, cv2.COLOR_RGBA2GRAY)
        _, thr   = cv2.threshold(gray,0,255,cv2.THRESH_BINARY|cv2.THRESH_OTSU)
        return ocr.get_number(Image.fromarray(thr), font=font, preprocess=False)

    # simple affine helpers --------------------------------------------------
    @abstractmethod
    def _shallow_copy(self, **kw): ...

    def transform(self, dx: int, dy: int) -> MatchResult:
        return self._shallow_copy(offset=(dx, dy))
    
    def copy(self) -> MatchResult:
        """Shallow copy of the region (no offset, no grow)."""
        return self._shallow_copy()

    def scale_px(self, pixels: int) -> MatchResult:
        return self._shallow_copy(grow=pixels)

    # convenience
    def crop_in(self, img: Image.Image) -> Image.Image:
        sx, sy, ex, ey = self.bounding_box
        return img.crop((sx, sy, ex, ey))


# ────────────────────────────────
# 1.   your original rectangle / ellipse
# ────────────────────────────────
class MatchShape:
    RECT  = 0
    ELIPSE  = 1        # “ellipse” really – axis‑aligned

@dataclass
class MatchResult(RegionMixin):
    start_x: int
    start_y: int
    end_x  : int
    end_y  : int
    confidence: float = -1.0
    scale     : float =  1.0
    shape     : MatchShape = MatchShape.RECT

    # ---- geometry primitives ----------------------------------------
    @property
    def bounding_box(self):                     # *already* axis aligned
        return self.start_x, self.start_y, self.end_x, self.end_y
    @property
    def width(self) -> int:
        return self.end_x - self.start_x
    @width.setter
    def width(self, new_width: int) -> None:
        center_x = (self.start_x + self.end_x) // 2
        half_width = new_width // 2
        self.start_x = center_x - half_width
        self.end_x = center_x + half_width


    @property
    def height(self) -> int:
        return self.end_y - self.start_y
    @height.setter
    def height(self, new_height: int) -> None:
        center_y = (self.start_y + self.end_y) // 2
        half_height = new_height // 2
        self.start_y = center_y - half_height
        self.end_y = center_y + half_height

    def contains(self, x: int, y: int) -> bool:
        if self.shape is MatchShape.RECT:
            return self.start_x <= x < self.end_x and self.start_y <= y < self.end_y
        # ellipse test
        cx, cy = (self.start_x + self.end_x)/2, (self.start_y + self.end_y)/2
        rx, ry = (self.end_x - self.start_x)/2, (self.end_y - self.start_y)/2
        if rx <= 0 or ry <= 0:                 # degenerate
            return False
        return ((x+0.5)-cx)**2 / rx**2 + ((y+0.5)-cy)**2 / ry**2 <= 1
    
    def remove_from(self, img: Image.Image) -> Image.Image:
        """Remove the region from a PIL image (fill with black)."""
        sx, sy, ex, ey = self.bounding_box
        if ex <= sx or ey <= sy:                # degenerate → no change
            return img
        draw = ImageDraw.Draw(img)
        # Choose appropriate fill color based on image mode
        if img.mode == 'RGBA':
            fill = (0, 0, 0, 0)  # Transparent black for RGBA
        elif img.mode == 'RGB':
            fill = (0, 0, 0)     # Black for RGB
        elif img.mode == 'L':
            fill = 0             # Black for grayscale
        else:
            # Default to black (adjust for other modes as needed)
            fill = 0
        draw.rectangle((sx, sy, ex, ey), fill=fill)
        return img

    def outline(self, pad_x=0, pad_y=0):
        if self.shape is MatchShape.RECT:
            sx, sy, ex, ey = self.start_x-pad_x, self.start_y-pad_y, self.end_x+pad_x, self.end_y+pad_y
            return [(sx, sy, ex, sy), (ex, sy, ex, ey),
                    (ex, ey, sx, ey), (sx, ey, sx, sy)]
        # ellipse outline: sample N points then connect
        cx, cy = (self.start_x + self.end_x)/2, (self.start_y + self.end_y)/2
        rx, ry = (self.end_x - self.start_x)/2 + pad_x, (self.end_y - self.start_y)/2 + pad_y
        pts = [(cx + rx*math.cos(t), cy + ry*math.sin(t)) for t in np.linspace(0, 2*math.pi, 32)]
        return [(int(pts[i][0]), int(pts[i][1]), int(pts[i+1][0]), int(pts[i+1][1])) for i in range(len(pts)-1)]
    def find_overlap(self, other: "MatchResult") -> Optional["MatchResult"]:
        """
        Axis‑aligned rectangle intersection.
        Returns a *new* MatchResult or None if they don’t overlap.
        """
        if not isinstance(other, MatchResult):
            raise TypeError("other must be MatchResult")

        sx = max(self.start_x,  other.start_x)
        sy = max(self.start_y,  other.start_y)
        ex = min(self.end_x,    other.end_x)
        ey = min(self.end_y,    other.end_y)

        if ex <= sx or ey <= sy:                 # empty
            return None

        # confidence: proportion of one rectangle covered by overlap
        area_self  = (self.end_x  - self.start_x) * (self.end_y  - self.start_y)
        area_ovlap = (ex - sx) * (ey - sy)
        conf       = area_ovlap / max(area_self, 1)

        return MatchResult(sx, sy, ex, ey,
                           confidence=conf,
                           scale=min(self.scale, other.scale),
                           shape=MatchShape.RECT)

    # ---- affine helpers ---------------------------------------------
    def _shallow_copy(self, *, offset=(0,0), grow=0):
        dx, dy = offset
        return MatchResult(self.start_x+dx-grow, self.start_y+dy-grow,
                           self.end_x+dx+grow,   self.end_y+dy+grow,
                           confidence=self.confidence, scale=self.scale,
                           shape=self.shape)


# ────────────────────────────────
# 2.   NEW arbitrary polygon region
# ────────────────────────────────
@dataclass
class ShapeResult(RegionMixin):
    points: List[Tuple[int, int]] = field(default_factory=list)
    confidence: float = -1.0
    scale     : float =  1.0

    # normalise so polygon is implicitly closed
    def __post_init__(self):
        if self.points and self.points[0] != self.points[-1]:
            self.points.append(self.points[0])

    # ---- geometry primitives ----------------------------------------
    @property
    def bounding_box(self):
        xs, ys = zip(*self.points)
        return min(xs), min(ys), max(xs), max(ys)
    
    @property
    def size_px(self) -> int:
        """
        Calculate the area of the polygon in pixels using the Shoelace formula.
        Returns the absolute value as int.
        """
        # Handle edge cases
        if len(self.points) <= 2:  # Not enough points for a polygon
            return 0
        
        # Shoelace formula
        area = 0
        for i in range(len(self.points) - 1):  # Last point is same as first for closed polygons
            x1, y1 = self.points[i]
            x2, y2 = self.points[i+1]
            area += x1 * y2 - x2 * y1
        
        return abs(area) // 2  # Integer division to return an int

    def contains(self, x: int, y: int) -> bool:
        """Ray‑casting point‑in‑polygon (odd‑even rule)."""
        inside = False
        epsilon = 1e-9  # Small value to prevent division by zero
        for (x0, y0), (x1, y1) in zip(self.points, self.points[1:]):
            if ((y0 > y) != (y1 > y)) and \
               (x < (x1 - x0) * (y - y0) / (max(y1 - y0, epsilon)) + x0):
                inside = not inside
        return inside

    def outline(self, pad_x=0, pad_y=0):
        """Return iterable of (x0,y0,x1,y1) segments (with optional padding)."""
        # simple per‑vertex offset away from centroid for visual padding
        if pad_x or pad_y:
            cx = sum(x for x, _ in self.points[:-1]) / (len(self.points)-1)
            cy = sum(y for _, y in self.points[:-1]) / (len(self.points)-1)
            def _pad(pt):
                vx, vy = pt[0]-cx, pt[1]-cy
                if vx == vy == 0:              # centroid corner case
                    return pt
                norm = math.hypot(vx, vy)
                return (pt[0] + pad_x*vx/norm, pt[1] + pad_y*vy/norm)
            pts = list(map(_pad, self.points))
        else:
            pts = self.points
        return [(int(pts[i][0]), int(pts[i][1]),
                 int(pts[i+1][0]), int(pts[i+1][1])) for i in range(len(pts)-1)]
    def find_overlap(self, other: "ShapeResult") -> Optional["ShapeResult"]:
        """
        Polygon intersection via raster mask.
        Finds the **largest** overlapping blob and converts it back
        to a polygon (≤ 8 vertices).  Returns None if there is no
        common area.
        """
        if not isinstance(other, ShapeResult):
            raise TypeError("other must be ShapeResult")

        # 1. clip to shared bounding‑box window  ───────────────────
        sx0, sy0, ex0, ey0 = self.bounding_box
        sx1, sy1, ex1, ey1 = other.bounding_box
        left,  top    = max(sx0, sx1), max(sy0, sy1)
        right, bottom = min(ex0, ex1), min(ey0, ey1)
        if right <= left or bottom <= top:
            return None

        H, W = bottom - top, right - left
        ys, xs = np.mgrid[top:bottom, left:right]
        xs, ys = xs.ravel(), ys.ravel()

        # 2. vectorised “contains” check on both shapes ────────────
        mask_a = np.fromiter((self.contains(x, y)  for x, y in zip(xs, ys)),
                             dtype=np.uint8, count=xs.size).reshape(H, W)
        mask_b = np.fromiter((other.contains(x, y) for x, y in zip(xs, ys)),
                             dtype=np.uint8, count=xs.size).reshape(H, W)

        overlap = np.bitwise_and(mask_a, mask_b).astype(np.uint8)
        if not overlap.any():
            return None

        # 3. pick the largest overlap blob  ────────────────────────
        cnts, _ = cv2.findContours(overlap, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
        cnt     = max(cnts, key=cv2.contourArea)
        if cv2.contourArea(cnt) == 0:
            return None

        # 4. simplify contour (≤8 verts) & convert back to img space
        epsilon = 0.5
        approx  = cv2.approxPolyDP(cnt, epsilon, True)[:, 0, :]
        approx += [left, top]                   # offset back

        pts = approx.tolist()
        if pts[0] != pts[-1]:
            pts.append(pts[0])                  # close loop

        return ShapeResult(points=pts,
                           confidence=cv2.contourArea(cnt))

    # ---- affine helpers ---------------------------------------------
    def _shallow_copy(self, *, offset=(0,0), grow=0):
        dx, dy = offset
        if grow:                           # grow uniformly from centroid
            cx = sum(x for x, _ in self.points[:-1]) / (len(self.points)-1)
            cy = sum(y for _, y in self.points[:-1]) / (len(self.points)-1)
            def _scale(pt):
                vx, vy = pt[0]-cx, pt[1]-cy
                if vx == vy == 0:
                    return pt
                norm = math.hypot(vx, vy)
                return (pt[0] + grow*vx/norm, pt[1] + grow*vy/norm)
            new_pts = [_scale((x+dx, y+dy)) for x, y in self.points]
        else:
            new_pts = [(x+dx, y+dy) for x, y in self.points]
        return ShapeResult(new_pts, confidence=self.confidence, scale=self.scale)
