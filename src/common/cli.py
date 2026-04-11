from __future__ import annotations

import argparse


def build_worker_arg_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--env-file",
        dest="env_file",
        default=None,
        help="Path to env file. If omitted, APP_ENV_FILE or local .env is used.",
    )
    return parser
