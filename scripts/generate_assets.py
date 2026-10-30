from pathlib import Path

from PIL import Image, ImageDraw

destination = Path(__file__).resolve().parents[1] / "apps" / "web" / "public"
destination.mkdir(parents=True, exist_ok=True)
canvas = Image.new("RGB", (1200, 480), "#d9e3df")
draw = ImageDraw.Draw(canvas)
draw.rectangle((0, 0, 1200, 300), fill="#d9e3df")
draw.polygon([(200, 0), (600, 0), (910, 330), (490, 330)], fill="#eef1e8")
draw.rectangle((0, 300, 1200, 480), fill="#c4cfcc")
draw.rectangle((0, 300, 1200, 310), fill="#b7c4c0")
draw.rectangle((70, 0, 95, 300), fill="#b8c9c5")
draw.rectangle((325, 0, 345, 300), fill="#b8c9c5")
draw.rectangle((70, 170, 345, 186), fill="#b8c9c5")
draw.polygon([(340, 361), (690, 361), (748, 429), (368, 429)], fill="#adbdb7")
draw.rounded_rectangle((350, 325, 705, 413), radius=8, fill="#f2f3ed")
draw.rounded_rectangle((350, 316, 705, 398), radius=8, fill="#fbfcf6")
draw.line((520, 318, 520, 394), fill="#dde3d8", width=3)
for position in range(337, 382, 12):
    draw.line((375, position, 491, position), fill="#dce4d9", width=2)
    draw.line((548, position, 672, position), fill="#dce4d9", width=2)
draw.line((680, 319, 735, 391), fill="#626f6e", width=7)
draw.line((735, 391, 739, 399), fill="#d9be89", width=5)
draw.ellipse((775, 338, 872, 367), fill="#a9bcb4")
draw.rounded_rectangle((792, 290, 854, 351), radius=15, fill="#f2efe7")
draw.ellipse((792, 282, 854, 302), fill="#fbf9f2")
draw.ellipse((800, 286, 846, 298), fill="#af8f72")
draw.arc((836, 300, 882, 338), 260, 100, fill="#f2efe7", width=10)
draw.polygon([(931, 278), (1040, 278), (1024, 366), (947, 366)], fill="#cb8e79")
draw.ellipse((931, 266, 1040, 287), fill="#dca18c")
draw.ellipse((943, 270, 1028, 280), fill="#7d8b72")
draw.line((987, 276, 991, 126), fill="#577c63", width=7)
draw.ellipse((982, 118, 1023, 184), fill="#5a8668")
draw.ellipse((947, 153, 993, 217), fill="#729579")
draw.ellipse((988, 185, 1048, 232), fill="#658b70")
draw.ellipse((940, 219, 990, 254), fill="#8ca88b")
canvas.save(destination / "workspace.png", optimize=True)

for size in (192, 512):
    icon = Image.new("RGB", (size, size), "#316650")
    pen = ImageDraw.Draw(icon)
    scale = size / 512
    for rectangle in [(110, 110, 280, 280), (232, 110, 402, 280), (110, 232, 280, 402), (232, 232, 402, 402)]:
        pen.rounded_rectangle(tuple(int(value * scale) for value in rectangle), radius=int(40 * scale), outline="#f3f5e9", width=max(2, int(13 * scale)))
    icon.save(destination / f"icon-{size}.png", optimize=True)