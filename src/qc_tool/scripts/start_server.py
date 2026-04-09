import argparse
import subprocess
from pathlib import Path


def main():
    args = setup_arguments()
    start_server(args)


def setup_arguments():
    parser = argparse.ArgumentParser(description="Start QC Tool")
    parser.add_argument("--file", type=Path, help="Dataset to open on startup")
    return parser.parse_args()


def start_server(args):
    try:
        print("Stop server with Ctrl-C")
        server_root_directory = Path(__file__).parent.parent
        cmd = [
            "bokeh",
            "serve",
            "--port",
            "5007",
            "--show",
            str(server_root_directory),
            "--websocket-max-message-size",
            "1000000000",
        ]
        if args.file:
            cmd += ["--args", "--file", str(args.file)]
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("Stopping server")


if __name__ == "__main__":
    main()
