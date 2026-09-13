"""Bootstrap entrypoint for the ChainSignal data pipeline."""

from chainsignal_pipeline import __version__


def main() -> None:
    print(f"ChainSignal data pipeline skeleton ready (v{__version__}).")


if __name__ == "__main__":
    main()