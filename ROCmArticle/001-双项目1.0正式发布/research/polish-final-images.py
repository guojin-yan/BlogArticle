"""Small typography repairs; generated scene and visual composition are preserved."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / 'assets'
ORIGINALS = A / 'originals-v3'
ORIGINALS.mkdir(exist_ok=True)
FONT = 'C:/Windows/Fonts/msyhbd.ttc'


def label(draw, xy, text, size, color='white'):
    draw.text(xy, text, font=ImageFont.truetype(FONT, size), fill=color, anchor='mm')


def original(name):
    source = A / name
    saved = ORIGINALS / name
    if not saved.exists():
        shutil.copy2(source, saved)
    return Image.open(saved).convert('RGB')


im = original('02-api-architecture-v3.png')
d = ImageDraw.Draw(im)
# Replace a minor generated Chinese glyph error inside the existing information plaque.
d.rounded_rectangle((60, 691, 302, 786), radius=10, fill='#26285d', outline='#a294ff', width=2)
label(d, (181, 720), 'C# 接口', 24)
label(d, (181, 760), '原生运行库 · GPU', 22)
im.save(A / '02-api-architecture-v3.png')

im = original('04-signal-diagnostics-v3.png')
d = ImageDraw.Draw(im)
# Retain the colorful file objects while removing malformed/repeated generated letters.
for bounds, text, fill in [((1344, 504, 1424, 537), 'HTML', '#db714c')]:
    d.rounded_rectangle(bounds, radius=5, fill=fill)
    label(d, ((bounds[0]+bounds[2])/2, (bounds[1]+bounds[3])/2), text, 16)
for x0, x1, text, fill, edge in [
    (1356, 1423, 'JSON', '#7546bb', '#bd9aff'),
    (1414, 1500, 'CSV', '#12858c', '#65e4d3')]:
    d.polygon([(x0,591),(x1-17,591),(x1,608),(x1,679),(x0,679)], fill=fill, outline=edge)
    d.line([(x1-17,592),(x1-17,608),(x1,608)], fill=edge, width=2)
    label(d, ((x0+x1)/2, 639), text, 21)
# Fix the English axis name without changing the illustrative trace.
d.rectangle((646, 477, 670, 569), fill='#123665')
axis = Image.new('RGBA', (100, 23), (0,0,0,0))
ImageDraw.Draw(axis).text((50, 11), 'Amplitude', font=ImageFont.truetype(FONT, 16), fill='white', anchor='mm')
axis = axis.rotate(90, expand=True)
im.paste(axis, (646, 475), axis)
im.save(A / '04-signal-diagnostics-v3.png')

im = original('06-video-event-search-v3.png')
d = ImageDraw.Draw(im)
for bounds, text, fill, border in [
    ((793, 713, 972, 744), '目标框 / 跟踪轨迹', '#124d83', '#62dbff'),
    ((1041, 713, 1210, 744), '区域 · 越线 · 停留', '#342775', '#ab8cff'),
    ((1080, 676, 1208, 705), '候选规则结果', '#102b54', '#3160a4'),
    ((1390, 511, 1516, 542), '回看证据', '#7d332c', '#ffba72')]:
    d.rounded_rectangle(bounds, radius=7, fill=fill, outline=border, width=1)
    label(d, ((bounds[0]+bounds[2])/2, (bounds[1]+bounds[3])/2), text, 18)
im.save(A / '06-video-event-search-v3.png')

cover_source = ORIGINALS / '01-cover-v2-full.png'
cover_file = '01-cover.png'
if cover_source.exists():
    cover = Image.open(cover_source).convert('RGB')
    # Keep the complete 3:2 composition: generated title and badges extend
    # beyond the requested crop-safe bands, so a 16:9 crop would cut them.
    cd = ImageDraw.Draw(cover)
    cd.rounded_rectangle((282, 639, 386, 670), radius=5, fill='#592331', outline='#ec8c88', width=1)
    label(cd, (334, 654), '并行线程', 20)
    cover.save(A / '01-cover-v2.png')
    cover_file = '01-cover-v2.png'

files = [cover_file] + [f'{s}-v3.png' for s in [
    '02-api-architecture', '03-surfacelab', '04-signal-diagnostics',
    '05-document-evidence', '06-video-event-search']]
if all((A/f).exists() for f in files):
    manifest = dict(model='gpt-image-2.6', quality='high', sourceSize='1536x1024',
                    revision='v3: rich original scenes, concrete workflows and Chinese labels',
                    method='Bundled imagegen CLI edit of original artwork; minor local typography repairs',
                    prompts='research/image-prompts-v4/',
                    purpose='Conceptual editorial illustrations, not software screenshots or measured results', images=[])
    for f in files:
        p=A/f
        manifest['images'].append(dict(file=f'assets/{f}', dimensions=list(Image.open(p).size),
                                      sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    (A/'image-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('Repaired small typography details; preserved generated originals.')
