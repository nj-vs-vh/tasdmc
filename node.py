import sys
import time


def long_opeartion(name: str):
    with open(name + ".txt", "w") as f:
        for _ in range(5):
            time.sleep(5)
            f.write(f"hello {name}\n")


if __name__ == "__main__":
    time.sleep(1)
    long_opeartion(sys.argv[1])
