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
"""Module to load DConf settings from jinja-templated files.

The ini-like format supported by dconf doesn't appear to have any way to use
environment variables in values, or to selectively reset keys. This does.
"""

import argparse
from collections.abc import Collection, Mapping, Sequence
import pathlib
import subprocess
import sys
import textwrap
from typing import Any

from dconf_fancy_load import config


def _set_keys_in_dir(
    path: str,
    values: Mapping[str, str],
    *,
    subprocess_run: Any,
    dry_run: bool = False,
) -> None:
    """Sets DConf keys in a directory.

    Args:
        path: Directory.
        values: Map from relative key to value to set in the directory.
        subprocess_run: Normally subprocess.run, but can be overriden in tests.
        dry_run: If true, just print actions.
    """
    keyfile_lines = ["[/]\n"]
    # Sort keys to make unit testing easier. (It doesn't matter to dconf load.)
    for key, value in sorted(values.items(), key=lambda kv: kv[0]):
        keyfile_lines.append(f"{key}={value}\n")
    keyfile = "".join(keyfile_lines)
    if dry_run:
        print(f"Load: {path}\n{textwrap.indent(keyfile, '  ')}")
    else:
        subprocess_run(
            ["dconf", "load", path], input=keyfile, text=True, check=True
        )


def _reset_path(
    path: str,
    *,
    preserve: Collection[str] = (),
    subprocess_run: Any,
    dry_run: bool = False,
) -> None:
    """Selectively resets a key or directory.

    Args:
        path: Absolute path to selectively reset, e.g., '/', '/foo/', or
            '/foo/bar'.
        preserve: Collection of absolute child paths to not reset. Dirs end in
            '/', keys don't. This is ignored if path is a key.
        subprocess_run: Normally subprocess.run, but can be overriden in tests.
        dry_run: If true, just print actions.
    """
    if not preserve or not path.endswith("/"):
        if dry_run:
            print(f"Reset: {path}")
        else:
            subprocess_run(["dconf", "reset", "-f", path], check=True)
        return
    dconf_list = subprocess_run(
        ["dconf", "list", path], stdout=subprocess.PIPE, text=True, check=True
    )
    for child in dconf_list.stdout.splitlines():
        child_path = path + child
        if child_path in preserve:
            continue
        _reset_path(
            child_path,
            preserve={x for x in preserve if x.startswith(child_path)},
            subprocess_run=subprocess_run,
            dry_run=dry_run,
        )


def load(
    dir_: config.Dir,
    *,
    path: str = "/",
    dry_run: bool = False,
    subprocess_run: Any = subprocess.run,
) -> Collection[str]:
    """Loads DConf values from the config.

    Args:
        dir_: Configured directory to load.
        path: DConf path of the directory, e.g., '/' or '/foo/'.
        dry_run: If true, just print actions.
        subprocess_run: Normally subprocess.run, but can be overriden in tests.

    Returns:
        Collection of paths to not reset, suitable for passing as the preserve
        argument to _reset_path.
    """
    preserve = set()
    values = {}  # Map from key to value to set in the current directory.
    for key_name, key in dir_.keys.items():
        key_path = path + key_name
        if key.value is not None:
            values[key_name] = key.value
            preserve.add(key_path)
        if key.reset is not None:
            if key.reset:
                _reset_path(
                    key_path,
                    subprocess_run=subprocess_run,
                    dry_run=dry_run,
                )
            else:
                preserve.add(key_path)
    for subdir_name, subdir in dir_.subdirs.items():
        subdir_path = path + subdir_name + "/"
        subdir_preserve = load(
            subdir,
            path=subdir_path,
            dry_run=dry_run,
            subprocess_run=subprocess_run,
        )
        if subdir.reset is not None:
            if subdir.reset:
                _reset_path(
                    subdir_path,
                    subprocess_run=subprocess_run,
                    preserve=subdir_preserve,
                    dry_run=dry_run,
                )
            # Preserve the directory either way. Either it was already reset, so
            # preserving it is an optimization, or the entire directory needs to
            # be preserved.
            preserve.add(subdir_path)
        else:
            # No explicit reset parameter, so preserve the preserved paths
            # from the children.
            preserve.update(subdir_preserve)
    if values:
        _set_keys_in_dir(
            path, values, subprocess_run=subprocess_run, dry_run=dry_run
        )
    return preserve


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
    load(root, dry_run=parsed_args.dry_run, subprocess_run=subprocess_run)


if __name__ == "__main__":
    main()
