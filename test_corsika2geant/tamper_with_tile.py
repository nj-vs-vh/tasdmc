import random

NWORD = 273

blocks = []

with open("./tile_old.dat", 'rb') as f:
    header = f.read(NWORD * 4)
    while True:
        block = f.read(6 * 2)
        if not block:
            break
        blocks.append(block)


random.shuffle(blocks)
# blocks[0], blocks[100] = blocks[100], blocks[0]


with open("./tile_tampered.dat", "wb") as f:
    f.write(header)
    for b in blocks:
        f.write(b)
