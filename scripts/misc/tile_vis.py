# a set of functions and classes to read and visualize contents of tile (*_gea.dat) files

from __future__ import annotations

from dataclasses import dataclass
import struct
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib import animation
from operator import attrgetter
from tqdm import tqdm

from typing import List, Literal, Optional


# from constants.h
NSENTENCE = 39
NPART = 7
NWORD = NPART * NSENTENCE
N_TILE = int(16800 / 6)
N_X = N_TILE
N_Y = N_TILE
TMAX = 1280


@dataclass
class TileBlock:
    m: int
    n: int
    t: int
    vem_top: int
    vem_bot: int
    pz: int

    @classmethod
    def parse(cls, buf: bytes) -> TileBlock:
        data = struct.unpack("HHHHHH", buf)
        t = data[4]
        if t > 32768:
            t -= 65537
        return TileBlock(m=data[0], n=data[1], vem_top=data[2], vem_bot=data[3], t=t, pz=data[5])


@dataclass
class TileFile:
    header: List[float]
    blocks: List[TileBlock]

    @classmethod
    def load(cls, filename: str) -> TileFile:
        blocks = []
        with open(filename, 'rb') as f:
            header = f.read(NWORD * 4)  # NWORD floats (4 bytes each)
            header = struct.unpack("f" * NWORD, header)
            while True:
                block_buf = f.read(6 * 2)  # 6 shorts (2 bytes each)
                if not block_buf:
                    break
                blocks.append(TileBlock.parse(block_buf))
        return TileFile(header, blocks)


def animate_tile(
    tile: TileFile,
    output_file_name: str,
    param: Literal["vem_top", "vem_bot", "pz"] = "vem_top",
    center_width: Optional[int] = None,
):
    if center_width is not None:
        start = int(N_TILE / 2 - center_width / 2)
        end = int(N_TILE / 2 + center_width / 2)
    else:
        start = 0
        end = N_TILE

    get_param_to_plot = attrgetter(param)
    max_param_value = max(get_param_to_plot(b) for b in tile.blocks)

    def frame_generator():
        blocks_to_plot: List[TileBlock] = []
        for block in tile.blocks:
            if start <= block.m < end and start <= block.n < end:
                blocks_to_plot.append(block)

        concurrent_empty_frames = 0

        t_curr = min(b.t for b in blocks_to_plot)
        frame = np.zeros((N_X, N_Y), dtype=int)
        while True:
            frame[:] = 0

            blocks_plotted_curr = 0
            for block in (b for b in blocks_to_plot if b.t == t_curr):
                frame[block.m, block.n] = get_param_to_plot(block)
                blocks_plotted_curr += 1
            
            t_curr += 1

            if blocks_plotted_curr == 0:
                concurrent_empty_frames +=1
                if concurrent_empty_frames > 6:
                    return
                else:
                    continue
            else:
                concurrent_empty_frames = 0
            yield frame[start:end, start:end]

    fig, ax = plt.subplots(figsize=(10, 10))

    print("Generating frames...")
    ims = []
    for frame in tqdm(frame_generator()):
        im = ax.imshow(frame, interpolation='nearest', norm=LogNorm(vmin=1, vmax=max_param_value), animated=True)
        ims.append([im])
    
    print(f"Writing frames to {output_file_name}")
    ani = animation.ArtistAnimation(fig, ims, interval=50, blit=True, repeat_delay=1000)
    # writer = animation.FFMpegWriter(fps=15, metadata=dict(artist='Me'), bitrate=1800)
    # ani.save(output_file_name, writer=writer)
    ani.save(output_file_name)


if __name__ == "__main__":
    tile = TileFile.load("runs/test-run/corsika2geant_output/DAT000026_gea.dat")
    # for param in ("vem_top", "vem_bot", "pz"):
    param = "vem_bot"
    animate_tile(tile, f"{param}.mp4", param=param, center_width=300)
