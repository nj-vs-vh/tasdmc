import subprocess
from pathlib import Path
from tqdm import tqdm

CORSIKA_DIR = Path('../../../runs/test-run/corsika_output/')

ZENITH_FROM_CORSIKA = Path(__file__).parent / "zenithFromThinnedCorsika"

res = subprocess.run(["gcc", "zenithFromThinnedCorsika.c", "-o", str(ZENITH_FROM_CORSIKA)], check=True, capture_output=True)
print(res.stdout.decode("utf-8"))
print(res.stderr.decode("utf-8"))


with open("corsika_thetas.txt", "wb") as f:
    total_files = len(list(CORSIKA_DIR.iterdir()))
    for file in tqdm(CORSIKA_DIR.iterdir(), total=total_files):
        file: Path
        if file.suffix == '':  # assuming these are corsika files
            res = subprocess.run([ZENITH_FROM_CORSIKA, file], check=True, capture_output=True)
            f.write(res.stdout)
