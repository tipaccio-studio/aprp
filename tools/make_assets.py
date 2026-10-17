"""Generate UI assets: the aprp app icon (.ico/.png) and platform logo geometries for WPF.

    python tools/make_assets.py      (needs Pillow: pip install pillow)

Platform logos are from Simple Icons (CC0-1.0, https://simpleicons.org); Steam,
Epic Games and Xbox are trademarks of their owners, used only to label which
store a game belongs to.
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "src" / "Aprp.App" / "Assets"

# ── App icon ────────────────────────────────────────────────────────────────

S = 1024
ACCENT_A = (124, 92, 255)   # #7C5CFF  violet
ACCENT_B = (34, 211, 238)   # #22D3EE  cyan


def _gradient(size: int) -> Image.Image:
    vertical = Image.linear_gradient("L").resize((size, size))
    mask = ImageChops.add(vertical, vertical.rotate(90), scale=2.0)  # top-left 0 -> bottom-right 255
    return Image.composite(Image.new("RGB", (size, size), ACCENT_B),
                           Image.new("RGB", (size, size), ACCENT_A), mask)


def _rounded(size, box, radius, fill) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(box, radius=radius, fill=fill)
    return layer


def make_icon() -> Image.Image:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # Tile: rounded square with a diagonal violet -> cyan gradient.
    tile_mask = _rounded((S, S), (32, 32, S - 32, S - 32), 230, (255, 255, 255, 255)).getchannel("A")
    img.paste(_gradient(S), (0, 0), tile_mask)

    # Back card (the "library"), tilted and translucent.
    back = _rounded((S, S), (300, 250, 640, 730), 70, (255, 255, 255, 95)).rotate(14, resample=Image.BICUBIC, center=(470, 490))
    img.alpha_composite(back)

    # Front card with a soft shadow.
    front_box = (380, 280, 720, 760)
    shadow = _rounded((S, S), front_box, 70, (20, 10, 60, 120)).filter(ImageFilter.GaussianBlur(24))
    img.alpha_composite(shadow, (10, 18))
    img.alpha_composite(_rounded((S, S), front_box, 70, (255, 255, 255, 255)))

    # Play triangle punched into the front card, filled with the tile gradient.
    tri = Image.new("L", (S, S), 0)
    cx, cy = 560, 520
    ImageDraw.Draw(tri).polygon([(cx - 70, cy - 110), (cx - 70, cy + 110), (cx + 115, cy)], fill=255)
    tri = tri.filter(ImageFilter.GaussianBlur(6)).point(lambda v: 255 if v > 110 else 0)  # rounded corners
    tri_layer = _gradient(S).convert("RGBA")
    tri_layer.putalpha(ImageChops.multiply(tri, tile_mask))
    img.alpha_composite(tri_layer)
    return img


# ── Platform logos (SVG path -> WPF path markup) ────────────────────────────

SIMPLE_ICONS = {
    "Steam": "M11.979 0C5.678 0 .511 4.86.022 11.037l6.432 2.658c.545-.371 1.203-.59 1.912-.59.063 0 .125.004.188.006l2.861-4.142V8.91c0-2.495 2.028-4.524 4.524-4.524 2.494 0 4.524 2.031 4.524 4.527s-2.03 4.525-4.524 4.525h-.105l-4.076 2.911c0 .052.004.105.004.159 0 1.875-1.515 3.396-3.39 3.396-1.635 0-3.016-1.173-3.331-2.727L.436 15.27C1.862 20.307 6.486 24 11.979 24c6.627 0 11.999-5.373 11.999-12S18.605 0 11.979 0zM7.54 18.21l-1.473-.61c.262.543.714.999 1.314 1.25 1.297.539 2.793-.076 3.332-1.375.263-.63.264-1.319.005-1.949s-.75-1.121-1.377-1.383c-.624-.26-1.29-.249-1.878-.03l1.523.63c.956.4 1.409 1.5 1.009 2.455-.397.957-1.497 1.41-2.454 1.012H7.54zm11.415-9.303c0-1.662-1.353-3.015-3.015-3.015-1.665 0-3.015 1.353-3.015 3.015 0 1.665 1.35 3.015 3.015 3.015 1.663 0 3.015-1.35 3.015-3.015zm-5.273-.005c0-1.252 1.013-2.266 2.265-2.266 1.249 0 2.266 1.014 2.266 2.266 0 1.251-1.017 2.265-2.266 2.265-1.253 0-2.265-1.014-2.265-2.265z",
    "Epic": "M3.537 0C2.165 0 1.66.506 1.66 1.879V18.44a4.262 4.262 0 00.02.433c.031.3.037.59.316.92.027.033.311.245.311.245.153.075.258.13.43.2l8.335 3.491c.433.199.614.276.928.27h.002c.314.006.495-.071.928-.27l8.335-3.492c.172-.07.277-.124.43-.2 0 0 .284-.211.311-.243.28-.33.285-.621.316-.92a4.261 4.261 0 00.02-.434V1.879c0-1.373-.506-1.88-1.878-1.88zm13.366 3.11h.68c1.138 0 1.688.553 1.688 1.696v1.88h-1.374v-1.8c0-.369-.17-.54-.523-.54h-.235c-.367 0-.537.17-.537.539v5.81c0 .369.17.54.537.54h.262c.353 0 .523-.171.523-.54V8.619h1.373v2.143c0 1.144-.562 1.71-1.7 1.71h-.694c-1.138 0-1.7-.566-1.7-1.71V4.82c0-1.144.562-1.709 1.7-1.709zm-12.186.08h3.114v1.274H6.117v2.603h1.648v1.275H6.117v2.774h1.74v1.275h-3.14zm3.816 0h2.198c1.138 0 1.7.564 1.7 1.708v2.445c0 1.144-.562 1.71-1.7 1.71h-.799v3.338h-1.4zm4.53 0h1.4v9.201h-1.4zm-3.13 1.235v3.392h.575c.354 0 .523-.171.523-.54V4.965c0-.368-.17-.54-.523-.54zm-3.74 10.147a1.708 1.708 0 01.591.108 1.745 1.745 0 01.49.299l-.452.546a1.247 1.247 0 00-.308-.195.91.91 0 00-.363-.068.658.658 0 00-.28.06.703.703 0 00-.224.163.783.783 0 00-.151.243.799.799 0 00-.056.299v.008a.852.852 0 00.056.31.7.7 0 00.157.245.736.736 0 00.238.16.774.774 0 00.303.058.79.79 0 00.445-.116v-.339h-.548v-.565H7.37v1.255a2.019 2.019 0 01-.524.307 1.789 1.789 0 01-.683.123 1.642 1.642 0 01-.602-.107 1.46 1.46 0 01-.478-.3 1.371 1.371 0 01-.318-.455 1.438 1.438 0 01-.115-.58v-.008a1.426 1.426 0 01.113-.57 1.449 1.449 0 01.312-.46 1.418 1.418 0 01.474-.309 1.58 1.58 0 01.598-.111 1.708 1.708 0 01.045 0zm11.963.008a2.006 2.006 0 01.612.094 1.61 1.61 0 01.507.277l-.386.546a1.562 1.562 0 00-.39-.205 1.178 1.178 0 00-.388-.07.347.347 0 00-.208.052.154.154 0 00-.07.127v.008a.158.158 0 00.022.084.198.198 0 00.076.066.831.831 0 00.147.06c.062.02.14.04.236.061a3.389 3.389 0 01.43.122 1.292 1.292 0 01.328.17.678.678 0 01.207.24.739.739 0 01.071.337v.008a.865.865 0 01-.081.382.82.82 0 01-.229.285 1.032 1.032 0 01-.353.18 1.606 1.606 0 01-.46.061 2.16 2.16 0 01-.71-.116 1.718 1.718 0 01-.593-.346l.43-.514c.277.223.578.335.9.335a.457.457 0 00.236-.05.157.157 0 00.082-.142v-.008a.15.15 0 00-.02-.077.204.204 0 00-.073-.066.753.753 0 00-.143-.062 2.45 2.45 0 00-.233-.062 5.036 5.036 0 01-.413-.113 1.26 1.26 0 01-.331-.16.72.72 0 01-.222-.243.73.73 0 01-.082-.36v-.008a.863.863 0 01.074-.359.794.794 0 01.214-.283 1.007 1.007 0 01.34-.185 1.423 1.423 0 01.448-.066 2.006 2.006 0 01.025 0zm-9.358.025h.742l1.183 2.81h-.825l-.203-.499H8.623l-.198.498h-.81zm2.197.02h.814l.663 1.08.663-1.08h.814v2.79h-.766v-1.602l-.711 1.091h-.016l-.707-1.083v1.593h-.754zm3.469 0h2.235v.658h-1.473v.422h1.334v.61h-1.334v.442h1.493v.658h-2.255zm-5.3.897l-.315.793h.624zm-1.145 5.19h8.014l-4.09 1.348z",
    "Xbox": "M4.102 21.033C6.211 22.881 8.977 24 12 24c3.026 0 5.789-1.119 7.902-2.967 1.877-1.912-4.316-8.709-7.902-11.417-3.582 2.708-9.779 9.505-7.898 11.417zm11.16-14.406c2.5 2.961 7.484 10.313 6.076 12.912C23.002 17.48 24 14.861 24 12.004c0-3.34-1.365-6.362-3.57-8.536 0 0-.027-.022-.082-.042-.063-.022-.152-.045-.281-.045-.592 0-1.985.434-4.805 3.246zM3.654 3.426c-.057.02-.082.041-.086.042C1.365 5.642 0 8.664 0 12.004c0 2.854.998 5.473 2.661 7.533-1.401-2.605 3.579-9.951 6.08-12.91-2.82-2.813-4.216-3.245-4.806-3.245-.131 0-.223.021-.281.046v-.002zM12 3.551S9.055 1.828 6.755 1.746c-.903-.033-1.454.295-1.521.339C7.379.646 9.659 0 11.984 0H12c2.334 0 4.605.646 6.766 2.085-.068-.046-.615-.372-1.52-.339C14.946 1.828 12 3.545 12 3.545v.006z",
}

_ARGS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}
_NUM = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")


def svg_to_wpf(d: str) -> str:
    """Re-serialise SVG path data with explicit separators.

    SVG allows packed arc flags ("a4 4 0 00.02.4"), which WPF's parser can't read.
    """
    out, i, cmd = [], 0, None

    def skip():
        nonlocal i
        while i < len(d) and d[i] in " ,\t\n":
            i += 1

    def number():
        nonlocal i
        skip()
        m = _NUM.match(d, i)
        if not m:
            raise ValueError(f"number expected at {i}: {d[i:i + 12]!r}")
        i = m.end()
        return m.group(0)

    def flag():
        nonlocal i
        skip()
        f = d[i]
        i += 1
        return f

    while True:
        skip()
        if i >= len(d):
            break
        if d[i].isalpha():
            cmd = d[i]
            i += 1
        elif cmd is None:
            raise ValueError("path must start with a command")
        up = cmd.upper()
        if up == "Z":
            out.append(cmd)
            cmd = None
            continue
        if up == "A":
            args = [number(), number(), number(), flag(), flag(), number(), number()]
        else:
            args = [number() for _ in range(_ARGS[up])]
        out.append(cmd + " " + " ".join(args))
        if up == "M":  # implicit repeats after a moveto are linetos
            cmd = "l" if cmd == "m" else "L"
    return " ".join(out)


def write_geometries() -> None:
    lines = [
        '<!-- Generated by tools/make_assets.py. Logos: Simple Icons (CC0-1.0); trademarks of their owners. -->',
        '<ResourceDictionary xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"',
        '                    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">',
    ]
    for name, d in SIMPLE_ICONS.items():
        lines.append(f'  <Geometry x:Key="{name}Logo">F1 {svg_to_wpf(d)}</Geometry>')
    lines.append("</ResourceDictionary>")
    (ASSETS / "PlatformLogos.xaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _path_polygons(d: str, steps: int = 16) -> list[list[tuple[float, float]]]:
    """Flatten SVG path data (24x24 Simple Icons) into polygons. Arcs become straight segments,
    which is invisible at banner sizes (Simple Icons only uses tiny corner arcs)."""
    tokens = svg_to_wpf(d).split()
    polys: list[list[tuple[float, float]]] = []
    cur: list[tuple[float, float]] = []
    x = y = sx = sy = 0.0
    last_ctrl = None
    i = 0

    def bez(p0, p1, p2, p3):
        for k in range(1, steps + 1):
            t = k / steps
            mt = 1 - t
            cur.append((mt**3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t**3 * p3[0],
                        mt**3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t**3 * p3[1]))

    while i < len(tokens):
        cmd = tokens[i]
        i += 1
        n = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}[cmd.upper()]
        a = [float(v) for v in tokens[i:i + n]]
        i += n
        rel = cmd.islower()
        up = cmd.upper()
        ox, oy = (x, y) if rel else (0.0, 0.0)
        if up == "M":
            if len(cur) > 2:
                polys.append(cur)
            x, y = ox + a[0], oy + a[1]
            sx, sy = x, y
            cur = [(x, y)]
        elif up == "L":
            x, y = ox + a[0], oy + a[1]
            cur.append((x, y))
        elif up == "H":
            x = (x if rel else 0) + a[0]
            cur.append((x, y))
        elif up == "V":
            y = (y if rel else 0) + a[0]
            cur.append((x, y))
        elif up == "C":
            p1, p2, p3 = (ox + a[0], oy + a[1]), (ox + a[2], oy + a[3]), (ox + a[4], oy + a[5])
            bez((x, y), p1, p2, p3)
            last_ctrl, (x, y) = p2, p3
            continue
        elif up == "S":
            p1 = (2 * x - last_ctrl[0], 2 * y - last_ctrl[1]) if last_ctrl else (x, y)
            p2, p3 = (ox + a[0], oy + a[1]), (ox + a[2], oy + a[3])
            bez((x, y), p1, p2, p3)
            last_ctrl, (x, y) = p2, p3
            continue
        elif up == "Q":
            q, p3 = (ox + a[0], oy + a[1]), (ox + a[2], oy + a[3])
            bez((x, y), (x + 2 / 3 * (q[0] - x), y + 2 / 3 * (q[1] - y)),
                (p3[0] + 2 / 3 * (q[0] - p3[0]), p3[1] + 2 / 3 * (q[1] - p3[1])), p3)
            x, y = p3
        elif up in ("T", "A"):
            x, y = ox + a[-2], oy + a[-1]
            cur.append((x, y))
        elif up == "Z":
            x, y = sx, sy
            if len(cur) > 2:
                polys.append(cur)
            cur = [(x, y)]
        last_ctrl = None
    if len(cur) > 2:
        polys.append(cur)
    return polys


def render_logo(name: str, size: int, color=(255, 255, 255)) -> Image.Image:
    """Platform logo as an RGBA image (even-odd fill: subpaths XOR, which matches these icons)."""
    k = 4  # supersample
    scale = size * k / 24
    mask = Image.new("1", (size * k, size * k), 0)
    for poly in _path_polygons(SIMPLE_ICONS[name]):
        layer = Image.new("1", mask.size, 0)
        ImageDraw.Draw(layer).polygon([(px * scale, py * scale) for px, py in poly], fill=1)
        mask = ImageChops.logical_xor(mask, layer)
    alpha = mask.convert("L").resize((size, size), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), color + (0,))
    out.putalpha(alpha)
    return out


def _font(size: int, bold: bool = True):
    from PIL import ImageFont
    for name in (("seguisb.ttf", "segoeuib.ttf") if bold else ("segoeui.ttf",)):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _backdrop(w: int, h: int) -> Image.Image:
    """Dark app-coloured background with soft violet/cyan glows and a few tilted 'cards'."""
    bg = Image.new("RGBA", (w, h), (11, 14, 18, 255))
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    r = max(w, h)
    d.ellipse((-r * 0.35, -r * 0.35, r * 0.55, r * 0.55), fill=ACCENT_A + (150,))
    d.ellipse((w - r * 0.45, h - r * 0.45, w + r * 0.35, h + r * 0.35), fill=ACCENT_B + (110,))
    bg.alpha_composite(glow.filter(ImageFilter.GaussianBlur(r * 0.18)))
    for i, (fx, fy, rot) in enumerate([(0.78, 0.18, 14), (0.12, 0.78, -12), (0.9, 0.72, -20)]):
        cw, ch = int(min(w, h) * 0.32), int(min(w, h) * 0.46)
        card = _rounded((cw + 40, ch + 40), (20, 20, cw + 20, ch + 20), int(cw * 0.18), (255, 255, 255, 22 + 6 * i))
        card = card.rotate(rot, resample=Image.BICUBIC, expand=True)
        bg.alpha_composite(card, (int(w * fx - card.width / 2), int(h * fy - card.height / 2)))
    return bg


def _platform_row(height: int, gap: int) -> Image.Image:
    logos = [render_logo(n, height) for n in ("Steam", "Epic", "Xbox")]
    row = Image.new("RGBA", (sum(l.width for l in logos) + gap * 2, height), (0, 0, 0, 0))
    x = 0
    for l in logos:
        l.putalpha(l.getchannel("A").point(lambda v: v * 0.85))
        row.alpha_composite(l, (x, 0))
        x += l.width + gap
    return row


def make_wizard_image(icon: Image.Image, scale: float) -> Image.Image:
    """Inno Setup left-hand banner (164x314 at 100% DPI)."""
    w, h = int(164 * scale), int(314 * scale)
    img = _backdrop(w, h)
    logo = icon.resize((int(84 * scale), int(84 * scale)), Image.LANCZOS)
    img.alpha_composite(logo, ((w - logo.width) // 2, int(78 * scale)))
    d = ImageDraw.Draw(img)
    f = _font(int(34 * scale))
    tw = d.textlength("aprp", font=f)
    d.text(((w - tw) / 2, 176 * scale), "aprp", font=f, fill=(241, 243, 248))
    row = _platform_row(int(16 * scale), int(14 * scale))
    img.alpha_composite(row, ((w - row.width) // 2, int(238 * scale)))
    return img.convert("RGB")


def make_wizard_small(icon: Image.Image, scale: float) -> Image.Image:
    """Inno Setup top-right page icon (55x55 at 100% DPI) on the white header."""
    s = int(55 * scale)
    img = Image.new("RGBA", (s, s), (255, 255, 255, 255))
    logo = icon.resize((int(s * 0.9), int(s * 0.9)), Image.LANCZOS)
    img.alpha_composite(logo, ((s - logo.width) // 2, (s - logo.height) // 2))
    return img.convert("RGB")


def make_banner(icon: Image.Image) -> Image.Image:
    """Wide project banner (README, store pages)."""
    w, h = 1600, 520
    img = _backdrop(w, h)
    logo = icon.resize((200, 200), Image.LANCZOS)
    img.alpha_composite(logo, (150, (h - 200) // 2 - 10))
    d = ImageDraw.Draw(img)
    d.text((395, 150), "aprp", font=_font(130), fill=(241, 243, 248))
    d.text((402, 315), "Steam · Epic Games · Xbox", font=_font(38, bold=False), fill=(201, 207, 219))
    row = _platform_row(44, 30)
    img.alpha_composite(row, (404, 385))
    return img.convert("RGB")


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    icon = make_icon()
    icon.resize((256, 256), Image.LANCZOS).save(ASSETS / "aprp.png")
    icon.save(ASSETS / "aprp.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    icon.resize((512, 512), Image.LANCZOS).save(ROOT / "docs" / "logo.png")
    write_geometries()

    installer = ROOT / "installer" / "art"
    installer.mkdir(parents=True, exist_ok=True)
    for pct in (100, 150, 200):
        make_wizard_image(icon, pct / 100).save(installer / f"wizard-{pct}.bmp")
        make_wizard_small(icon, pct / 100).save(installer / f"small-{pct}.bmp")
    make_banner(icon).save(ROOT / "docs" / "banner.png")
    print("assets written to", ASSETS, "and", installer)


if __name__ == "__main__":
    main()
