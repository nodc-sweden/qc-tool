import argparse
import subprocess
from pathlib import Path


def main():
    _ = setup_arguments()
    start_server()


def setup_arguments():
    parser = argparse.ArgumentParser(description="Start QC Tool")
    return parser.parse_args()


def start_server():
    try:
        print("Stop server with Ctrl-C")
        server_root_directory = Path(__file__).parent.parent
        subprocess.run(
            ["bokeh", "serve", "--port", "5007", "--show", str(server_root_directory)]
        )
    except KeyboardInterrupt:
        print("Stopping server")


if __name__ == "__main__":
    main()
