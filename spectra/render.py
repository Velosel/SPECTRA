"""SPECTRA v0.6 reversible dense image renderer.

Every packet region contains the actual serialized SPECTRA packet as 4-bit
color symbols. No camera processing is needed for image_decode.py; decoding is
performed directly from the PNG's canonical geometry.

The remaining micro-cells are deterministic visual filler and are ignored by
the decoder. Packet regions remain disjoint.
"""
from __future__ import annotations
import hashlib, random, struct
from pathlib import Path
from typing import Iterable
from PIL import Image, ImageDraw, ImageFont

PALETTE = [
    "#FF3B30", "#FF6B35", "#FF9F1C", "#FFD23F",
    "#8BE28B", "#39D98A", "#00D1B2", "#35C7FF",
    "#1E90FF", "#4E6BFF", "#875CFF", "#B84DFF",
    "#E83EAF", "#FF4FA3", "#FF75C8", "#F2F4F8",
]
ANCHOR_COLORS = {"tl":"#21B8FF","tr":"#FF7542","bl":"#58D95D","br":"#D63CDA"}

BG = "#02040A"
WHITE = "#F4F6FA"
HEADER_CAPACITY_BYTES = 50  # 100 nibbles per packet region

def _font(size):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()

def _bytes(v):
    return v if isinstance(v, bytes) else repr(v).encode("utf-8","replace")

def _draw_anchor(draw,cx,cy,r,color):
    draw.ellipse([cx-r,cy-r,cx+r,cy+r],fill=color)
    r2=r*0.47
    draw.ellipse([cx-r2,cy-r2,cx+r2,cy+r2],fill=BG)
    r3=r*0.17
    draw.ellipse([cx-r3,cy-r3,cx+r3,cy+r3],fill=color)

def _rect_intersects(a,b,gap=0):
    ax0,ay0,ax1,ay1=a; bx0,by0,bx1,by1=b
    return not (ax1+gap<=bx0 or bx1+gap<=ax0 or ay1+gap<=by0 or by1+gap<=ay0)

def _safe_regions(size,border,grid,panel,anchors):
    inner0=border+12
    inner1=size-border-12
    step=(inner1-inner0)/grid
    regions=[]
    for row in range(grid):
        for col in range(grid):
            x0=inner0+col*step; y0=inner0+row*step
            x1=inner0+(col+1)*step; y1=inner0+(row+1)*step
            rect=(x0,y0,x1,y1)
            if _rect_intersects(rect,panel,gap=step*0.12):
                continue
            if any(_rect_intersects(rect,a,gap=step*0.08) for a in anchors):
                continue
            regions.append((row,col,x0,y0,x1,y1))
    return regions

def _color_index_from_rgb(hex_color):
    return PALETTE.index(hex_color)

def _nibbles_to_bytes(data):
    out=bytearray()
    for i in range(0,len(data),2):
        hi=data[i]&0x0F
        lo=data[i+1]&0x0F if i+1<len(data) else 0
        out.append((hi<<4)|lo)
    return bytes(out)

def _packet_to_nibbles(packet: bytes):
    nibbles=[]
    for b in packet:
        nibbles.append((b>>4)&0x0F)
        nibbles.append(b&0x0F)
    if len(packet) > HEADER_CAPACITY_BYTES:
        raise ValueError(
            f"Packet is {len(packet)} bytes; image region supports "
            f"{HEADER_CAPACITY_BYTES} bytes."
        )
    nibbles.extend([0]*(HEADER_CAPACITY_BYTES*2-len(nibbles)))
    return nibbles

def _draw_packet_region(draw, region, packet, packet_index, module_grid=10):
    _,_,x0,y0,x1,y1=region
    width=x1-x0; height=y1-y0
    gap=max(1,min(width,height)*0.045)
    cw=(width-gap*(module_grid+1))/module_grid
    ch=(height-gap*(module_grid+1))/module_grid

    nibbles=_packet_to_nibbles(packet)
    digest=hashlib.sha256(packet+packet_index.to_bytes(4,"big")).digest()
    filler_rng=random.Random(int.from_bytes(digest[:8],"big"))

    for i in range(module_grid*module_grid):
        row,col=divmod(i,module_grid)
        sx0=x0+gap+col*(cw+gap)
        sy0=y0+gap+row*(ch+gap)
        sx1=sx0+cw
        sy1=sy0+ch

        if i < len(nibbles):
            value=nibbles[i]
            color=PALETTE[value]
        else:
            color=PALETTE[filler_rng.randrange(16)]

        # Keep actual data cells bright and clearly separated.
        shrink=min(cw,ch)*0.08
        sx0+=shrink; sx1-=shrink; sy0+=shrink; sy1-=shrink

        # Hard invariant: microcell remains inside packet region.
        assert x0 < sx0 < sx1 < x1
        assert y0 < sy0 < sy1 < y1

        draw.rounded_rectangle(
            [int(sx0),int(sy0),int(sx1),int(sy1)],
            radius=max(1,int(min(sx1-sx0,sy1-sy0)*0.10)),
            fill=color
        )

def render_symbol(
    packets: Iterable,
    symbol_id: int,
    meta_lines=None,
    size: int=720,
    out_path: str|None=None,
    center_title: str="SPECTRA",
    center_lines: Iterable[str]|None=None,
):
    packets=list(packets)
    lines=list(center_lines if center_lines is not None else (meta_lines or []))
    img=Image.new("RGB",(size,size),BG)
    draw=ImageDraw.Draw(img)

    border=max(12,int(size*0.028))
    draw.rectangle([border,border,size-border-1,size-border-1],
                   outline=WHITE,width=max(2,int(size*0.004)))
    draw.rectangle([border+7,border+7,size-border-8,size-border-8],
                   outline="#202632",width=max(1,int(size*0.002)))

    radius=size*0.065
    inset=border+size*0.078
    anchors=[
        (inset,inset,radius,ANCHOR_COLORS["tl"]),
        (size-inset,inset,radius,ANCHOR_COLORS["tr"]),
        (inset,size-inset,radius,ANCHOR_COLORS["bl"]),
        (size-inset,size-inset,radius,ANCHOR_COLORS["br"])
    ]
    anchor_rects=[]
    for cx,cy,r,c in anchors:
        _draw_anchor(draw,cx,cy,r,c)
        anchor_rects.append((cx-r,cy-r,cx+r,cy+r))

    panel_w=size*0.29
    panel_h=size*0.235
    px0=size/2-panel_w/2; py0=size/2-panel_h/2
    px1=size/2+panel_w/2; py1=size/2+panel_h/2
    panel=(px0,py0,px1,py1)
    draw.rectangle(panel,fill=BG,outline=WHITE,width=max(2,int(size*0.003)))

    title=str(center_title)[:24]
    font=_font(max(18,int(panel_h*0.19)))
    box=draw.textbbox((0,0),title,font=font)
    draw.text(((size-(box[2]-box[0]))/2,py0+panel_h*0.10),title,font=font,fill=WHITE)

    small=_font(max(8,int(panel_h*0.055)))
    y=py0+panel_h*0.42
    for line in lines[:6]:
        line=str(line)[:40]
        box=draw.textbbox((0,0),line,font=small)
        draw.text(((size-(box[2]-box[0]))/2,y),line,font=small,fill="#D7DCE5")
        y+=max(12,panel_h*0.078)

    regions=_safe_regions(size,border,18,panel,anchor_rects)
    if len(packets)>len(regions):
        raise ValueError(f"{len(packets)} packets but only {len(regions)} safe regions")

    indexed=list(enumerate(packets))
    rng=random.Random((symbol_id&0xFFFFFFFF)^0x53504543545241)
    rng.shuffle(indexed)

    region_rng=random.Random((symbol_id&0xFFFFFFFF)^0x1CEB00DA)
    region_rng.shuffle(regions)

    used=[]
    for place,(original_index,packet) in enumerate(indexed):
        region=regions[place]
        rect=region[2:6]
        assert not _rect_intersects(rect,panel)
        assert not any(_rect_intersects(rect,a) for a in anchor_rects)
        assert not any(_rect_intersects(rect,u) for u in used)
        used.append(rect)
        _draw_packet_region(draw,region,packet,original_index,module_grid=10)

    if out_path:
        target=Path(out_path)
        target.parent.mkdir(parents=True,exist_ok=True)
        img.save(target)
    return img
