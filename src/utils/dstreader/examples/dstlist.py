from pathlib import Path
from dstreader import DstFile


example_dst_file = Path(__file__).parent / 'example.dst.gz'

with DstFile(example_dst_file) as dst:
    for banks in dst.events():
        print(' '.join(banks))
