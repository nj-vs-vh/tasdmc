import subprocess
from pathlib import Path

CORSIKA_DIR = Path('../runs/test-run/corsika_output/')

ZENITH_FROM_CORSIKA = Path(__file__).parent / "zenithFromCorsika"

res = subprocess.run(["gcc", "zenithFromCorsika.c", "-o", str(ZENITH_FROM_CORSIKA)], check=True, capture_output=True)
print(res.stdout.decode("utf-8"))
print(res.stderr.decode("utf-8"))


with open("corsika_thetas.txt", "wb") as f:
    for file in CORSIKA_DIR.iterdir():
        if file.suffix == '':  # assuming these are corsika files
            res = subprocess.run([ZENITH_FROM_CORSIKA, file], check=True, capture_output=True)
            f.write(res.stdout)
