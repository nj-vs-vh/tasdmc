from pathlib import Path
from dstreader import DstFile
from dstreader.dstreader_core import get_rusdraw_xxyy, get_rusdraw_fadc


# example_dst_file = Path(__file__).parent / 'example.dst.gz'
example_dst_file = Path(__file__).parent.parent / '../../../../takeishi/example/DAT009512_0_gea.dst.gz'

with DstFile(example_dst_file) as dst:
    for banks in dst.events():
        if 'rusdraw' not in banks:
            print("rusdmc bank not found!")
        rusdraw = dst.get_bank('rusdraw')
        if rusdraw.nofwf == 0:
            continue
        xxyy = get_rusdraw_xxyy()
        print(xxyy)  # regular numpy array
        fadc = get_rusdraw_fadc()
        print(fadc[:, 0, :])  # printing waveforms for top counter
        break
