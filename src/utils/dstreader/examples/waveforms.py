from pathlib import Path
from dstreader import DstFile
from dstreader.dstreader_core import get_rusdraw_xxyy


# example_dst_file = Path(__file__).parent / 'example.dst.gz'
example_dst_file = Path(__file__).parent.parent / '../../../../takeishi/example/DAT009512_0_gea.dst.gz'
print(example_dst_file)

with DstFile(example_dst_file) as dst:
    for banks in dst.events():
        if 'rusdraw' not in banks:
            print("rusdmc bank not found!")
        rusdraw = dst.get_bank('rusdraw')
        if rusdraw.nofwf == 0:
            continue
        arr = get_rusdraw_xxyy()
        print(arr)
        break
