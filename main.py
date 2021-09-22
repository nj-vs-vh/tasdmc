import argparse

import tasdmc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--config", help="config file to use. defaults to config.yaml", default="config.yaml"
    )
    args = parser.parse_args()

    cfg = tasdmc.read_config(args.config)

    tasdmc.generate_corsika_infiles(cfg)


if __name__ == "__main__":
    main()
