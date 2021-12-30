import struct


NWORD = 273


with open("./tile_old.dat", 'rb') as f:
    header = f.read(NWORD * 4)
    while True:
        block = f.read(6 * 2)
        if not block:
            break
        block = struct.unpack("HHHHHH", block)
        print(",".join([str(n) for n in block]))
