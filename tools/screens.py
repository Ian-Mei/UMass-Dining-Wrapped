"""Every results screen's color and art, in story order. Edit this, then run:  python -m tools.cut_sprites

Each piece of art is (sprite, where):
  "TL" "TR" "BL" "BR"  a corner, for sprites cut by two edges
  "T", x  or  "B", x   the top or bottom edge, x% across, for sprites cut by the top or bottom
  "L", y  or  "R", y   the left or right edge, y% down, for sprites cut by the left or right
  "F", x, y            anywhere, only for sprites with no cut side
Sprites are mirrored automatically so their cut sides stay against the window's edge.
"""

CREAM, INK = "#fff6e9", "#1c0d0a"

SCREENS = {
    "home": {"color": "#862632", "art": [("maroon-00", "TL"), ("maroon-01", "T", 24), ("maroon-02", "TR"), ("maroon-04", "BL"), ("maroon-05", "B", 51), ("maroon-03", "BR")]},
    "favIntro": {"color": "#6f2dff", "art": [("teal-03", "TR"), ("plum-00", "BL"), ("black-01", "B", 42), ("black-03", "TL")]},
    "favDC": {"color": "#ff5b49", "art": [("coral-00", "TL"), ("coral-02", "TR"), ("coral-03", "BL"), ("coral-04", "B", 27), ("coral-05", "BR")]},
    "routine": {"color": "#ff8a3d", "art": [("plum-04", "TL"), ("teal-01", "R", 22), ("maroon-03", "BL"), ("plum-02", "B", 55)]},
    "bluewall": {"color": "#2f5bea", "art": [("periwinkle-03", "BR"), ("periwinkle-02", "L", 31), ("black-01", "T", 56), ("maroon-00", "TR")]},
    "bluewallchart": {"color": "#afb1ff", "art": [("teal-00", "TL"), ("black-02", "F", 2, 68), ("coral-02", "BR")]},
    "harvest": {"color": "#2f7d4f", "art": [("teal-02", "TR"), ("teal-03", "BL"), ("plum-03", "BR"), ("periwinkle-00", "T", 22)]},
    "topups": {"color": "#7be0c3", "art": [("black-03", "TL"), ("coral-05", "BL"), ("coral-03", "BR")]},
    "top3vendors": {"color": "#ff7bb0", "art": [("maroon-02", "BL"), ("plum-04", "TR"), ("teal-01", "L", 18), ("maroon-05", "B", 58)]},
    "clock": {"color": "#722d65", "art": [("plum-01", "TR"), ("coral-03", "BL"), ("plum-03", "TL")]},
    "calendar": {"color": "#4a3fa8", "art": [("maroon-00", "BR"), ("teal-00", "TL"), ("periwinkle-00", "B", 8)]},
    "funfacts": {"color": "#5cc8ff", "art": [("plum-03", "TL"), ("black-01", "B", 42), ("maroon-03", "TR"), ("coral-00", "BR")]},
    "laundry": {"color": "#d7b8ff", "art": [("teal-02", "TL"), ("periwinkle-01", "T", 62), ("black-03", "BR")]},
    "plans": {"color": "#0f6b5c", "art": [("coral-00", "BL"), ("periwinkle-00", "T", 24), ("periwinkle-03", "TR")]},
    "personality": {"color": "#000000", "art": [("black-00", "TL"), ("black-03", "BR"), ("black-02", "F", 1, 72), ("plum-03", "TR")]},
    "card": {"color": "#16d0a6", "art": [("teal-00", "TR"), ("teal-01", "L", 22), ("teal-03", "BL"), ("teal-02", "BR")]},
    "tables": {"color": "#33415c", "art": [("maroon-04", "TR"), ("maroon-05", "B", 8), ("coral-02", "TL")]},
    "days": {"color": "#b5179e", "art": [("black-03", "TL"), ("periwinkle-02", "R", 26), ("teal-03", "BR")]},
    "places": {"color": "#b8431f", "art": [("plum-00", "BR"), ("periwinkle-00", "T", 30), ("black-02", "F", 2, 70)]},
    "end": {"color": "#1b1236", "art": [("black-01", "T", 50), ("maroon-03", "BL"), ("plum-04", "TR"), ("maroon-02", "BR")]},
}


def luminance(color):
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    channels = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(a, b):
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def text_color(background):
    """Cream or ink, whichever reads better on this background."""
    return max((CREAM, INK), key=lambda color: contrast(color, background))


def placement(cuts, spec):
    """(CSS, x flip, y flip, kind) for a sprite with these cut sides at this spot."""
    across_cut, down_cut = cuts["L"] or cuts["R"], cuts["T"] or cuts["B"]
    target = spec[0]
    if target == "F":
        if across_cut or down_cut:
            raise ValueError("a sprite with a cut side has to sit against an edge")
        return f"left:{spec[1]}%;top:{spec[2]}%;--ox:50%;--oy:50%", 1, 1, "mid"
    if len(target) == 2:
        if not (across_cut and down_cut):
            raise ValueError("only a sprite cut by two edges fits a corner")
        down, across = target
        flip_x = -1 if cuts["L"] != (across == "L") else 1
        flip_y = -1 if cuts["T"] != (down == "T") else 1
        side_x, side_y = ("left", "0%") if across == "L" else ("right", "100%")
        side_d, side_o = ("top", "0%") if down == "T" else ("bottom", "100%")
        return f"{side_x}:0;{side_d}:0;--ox:{side_y};--oy:{side_o}", flip_x, flip_y, "corner"
    if target in ("T", "B"):
        if not down_cut or across_cut:
            raise ValueError("only a sprite cut by just the top or bottom fits there")
        flip_y = -1 if cuts["T"] != (target == "T") else 1
        side, origin = ("top", "0%") if target == "T" else ("bottom", "100%")
        return f"left:{spec[1]}%;{side}:0;--ox:50%;--oy:{origin}", 1, flip_y, "mid"
    if not across_cut or down_cut:
        raise ValueError("only a sprite cut by just the left or right fits there")
    flip_x = -1 if cuts["L"] != (target == "L") else 1
    side, origin = ("left", "0%") if target == "L" else ("right", "100%")
    return f"{side}:0;top:{spec[1]}%;--ox:{origin};--oy:50%", flip_x, 1, "mid"
