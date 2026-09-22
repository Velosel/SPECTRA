from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from PIL import Image

from spectra.codec import SpectraDecoder
from spectra.packet import unpack_packet
from spectra.render import (
    PALETTE, HEADER_CAPACITY_BYTES, _safe_regions
)

BG = (2,4,10)

def _nearest(rgb):
    best=0
    bestd=None
    for i,c in enumerate(PALETTE):
        h=c.lstrip("#")
        target=tuple(int(h[j:j+2],16) for j in (0,2,4))
        d=sum((int(rgb[k])-target[k])**2 for k in range(3))
        if bestd is None or d<bestd:
            best,bestd=i,d
    return best

def _read_packet_region(img, region, module_grid=10):
    _,_,x0,y0,x1,y1=region
    width=x1-x0; height=y1-y0
    gap=max(1,min(width,height)*0.045)
    cw=(width-gap*(module_grid+1))/module_grid
    ch=(height-gap*(module_grid+1))/module_grid

    nibbles=[]
    for i in range(module_grid*module_grid):
        row,col=divmod(i,module_grid)
        sx0=x0+gap+col*(cw+gap)
        sy0=y0+gap+row*(ch+gap)
        sx1=sx0+cw; sy1=sy0+ch
        cx=int((sx0+sx1)/2)
        cy=int((sy0+sy1)/2)
        rgb=img.getpixel((cx,cy))
        nibbles.append(_nearest(rgb))

    raw=bytearray()
    for i in range(0,len(nibbles),2):
        raw.append((nibbles[i]<<4)|nibbles[i+1])
    return bytes(raw)

def decode_image(path: str, size: int=720):
    img=Image.open(path).convert("RGB")
    if img.size != (size,size):
        img=img.resize((size,size), Image.Resampling.NEAREST)

    border=max(12,int(size*0.028))
    panel_w=size*0.29
    panel_h=size*0.235
    panel=(size/2-panel_w/2,size/2-panel_h/2,
           size/2+panel_w/2,size/2+panel_h/2)

    radius=size*0.065
    inset=border+size*0.078
    anchors=[
        (inset-radius,inset-radius,inset+radius,inset+radius),
        (size-inset-radius,inset-radius,size-inset+radius,inset+radius),
        (inset-radius,size-inset-radius,inset+radius,size-inset+radius),
        (size-inset-radius,size-inset-radius,size-inset+radius,size-inset+radius),
    ]

    regions=_safe_regions(size,border,18,panel,anchors)
    valid=0
    decoder=SpectraDecoder()
    packets=[]

    for region in regions:
        raw=_read_packet_region(img,region,10)
        # The actual packet is 20 bytes for the current image profile
        # (4-byte payload + header + CRC), while the region is 50 bytes.
        packet=raw[:20]
        parsed=unpack_packet(packet)
        if parsed is None:
            continue
        valid += 1
        packets.append(packet)
        decoder.feed(packet)

    layer,data=decoder.result()

    result={
        "regions":len(regions),
        "crc_valid_packets":valid,
        "layer":layer,
    }

    if layer=="L2":
        result["payload_bytes"]=len(data)
        result["payload"]=data.decode("utf-8","replace")
        result["sha256"]=hashlib.sha256(data).hexdigest()
        result["verified"]=True
    elif layer=="L1":
        result["payload_bytes"]=len(data)
        result["payload_preview"]=data[:64].hex()
        result["verified"]=False
    elif layer=="L0":
        result["metadata"]=data
        result["verified"]=False
    else:
        result["verified"]=False

    return result

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--size",type=int,default=720)
    args=ap.parse_args()
    print(decode_image(args.image,args.size))
