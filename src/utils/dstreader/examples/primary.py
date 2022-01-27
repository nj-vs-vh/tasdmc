from pathlib import Path
from dstreader import DstFile


example_dst_file = Path(__file__).parent / 'example.dst.gz'

with DstFile(example_dst_file) as dst:
    for banks in dst.events():
        if 'rusdmc' not in banks:
            print("rusdmc bank not found!")
        rusdmc = dst.get_bank('rusdmc')
        print(f"Primary id = {rusdmc.parttype}, E = {(1000 * rusdmc.energy):.3f} PeV")
