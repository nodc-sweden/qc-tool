import argparse
import subprocess


def main():
    arguments = setup_arguments()
    start_server()


def setup_arguments():
    parser = argparse.ArgumentParser(description="Start QC Tool")
    return parser.parse_args()


def start_server():
    try:
        print("Stop server with Ctrl-C")
        subprocess.run(["bokeh", "serve", "--show", "src/qc_tool"])
    except KeyboardInterrupt:
        print("Stopping server")


if __name__ == "__main__":
    main()
