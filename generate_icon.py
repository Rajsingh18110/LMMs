from PIL import Image, ImageDraw, ImageFont
import math

size = 512
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Draw hexagon
center = size / 2
radius = size * 0.45
points = []
for i in range(6):
    angle_deg = 60 * i - 30
    angle_rad = math.pi / 180 * angle_deg
    x = center + radius * math.cos(angle_rad)
    y = center + radius * math.sin(angle_rad)
    points.append((x, y))

# Background hexagon (dark fill with green glow)
draw.polygon(points, fill=(15, 20, 25, 255), outline=(0, 255, 128, 255), width=15)

# Try to load a font, fallback to default
try:
    font = ImageFont.truetype("DejaVuSans-Bold.ttf", int(size * 0.4))
except IOError:
    font = ImageFont.load_default()

text = "</>"
# Measure text roughly to center it
try:
    bbox = draw.textbbox((0,0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
except Exception:
    tw, th = int(size * 0.6), int(size * 0.2)
    
draw.text((center - tw/2, center - th/2 - size*0.05), text, fill=(0, 255, 128, 255), font=font)

img.save('/home/kali/Projects/LMMs/lmms/gui/assets/icon.png')
print("Icon generated successfully.")
