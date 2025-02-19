# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Main entrypoint."""

import argparse
from collections.abc import Sequence
import pathlib
import subprocess
import sys
from typing import Any

from dconf_fancy_load import config
from dconf_fancy_load import load


def main(
    *,
    args: Sequence[str] = sys.argv[1:],
    subprocess_run: Any = subprocess.run,
) -> None:
    """Main.

    Args:
        args: Command line arguments.
        subprocess_run: Normally subprocess.run, but can be overriden in tests.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config-dir",
        default=pathlib.Path.home().joinpath(".config", "dconf-fancy-load"),
        type=pathlib.Path,
    )
    parser.add_argument("--dry-run", action="store_true")
    parsed_args = parser.parse_args(args)
    root = config.get(parsed_args.config_dir)
    load.load(root, dry_run=parsed_args.dry_run, subprocess_run=subprocess_run)


if __name__ == "__main__":
    main()
