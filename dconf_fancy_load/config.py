# Copyright 2025 David Mandelberg
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
"""Config file data structures and parsing functions."""

import collections
from collections.abc import Sequence
import configparser
import dataclasses
import os
import pathlib

import jinja2


@dataclasses.dataclass(kw_only=True)
class Key:
    """Dconf key.

    Attributes:
        reset: Whether to reset the key to its default value, or None to inherit
            from the parent. This is ignored if value is non-None.
        value: Value to set the key to, or None to not set the key.
    """

    reset: bool | None = None
    value: str | None = None


@dataclasses.dataclass(kw_only=True)
class Dir:
    """Dconf directory.

    Attributes:
        reset: Whether to recursively reset the directory, or None to inherit
            from the parent. Child directories and keys may override this.
        subdirs: Child directories.
        keys: Child keys.
    """

    reset: bool | None = None
    subdirs: dict[str, "Dir"] = dataclasses.field(
        default_factory=lambda: collections.defaultdict(Dir)
    )
    keys: dict[str, Key] = dataclasses.field(
        default_factory=lambda: collections.defaultdict(Key)
    )

    def get_subdir(self, path: Sequence[str]) -> "Dir":
        """Returns a subdir specified as relative path components."""
        if not path:
            return self
        return self.subdirs[path[0]].get_subdir(path[1:])


def _parse_bool(value: str, *, context: str) -> bool:
    # https://docs.gtk.org/glib/gvariant-text-format.html#booleans
    match value:
        case "true":
            return True
        case "false":
            return False
        case _:
            raise ValueError(f"{context}: {value!r} is not a boolean")


def get(config_dir: pathlib.Path) -> Dir:
    """Returns the root dir config from merging all config files."""
    root = Dir()
    jinja_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(config_dir), autoescape=False
    )
    for path in sorted(config_dir.iterdir()):
        if not path.name.endswith(".ini.jinja"):
            continue
        config = configparser.ConfigParser(
            delimiters=("=",),
            comment_prefixes=("#",),
            interpolation=None,
        )
        config.optionxform = lambda optionstr: optionstr  # type: ignore[method-assign]
        config.read_string(
            jinja_env.get_template(path.name).render(env=os.environ),
            source=str(path),
        )
        for section in config.sections():
            if section == "/":
                dir_ = root
            else:
                dir_ = root.get_subdir(section.split("/"))
            for raw_key, value in config[section].items():
                context = f"Section {section!r} key {raw_key!r}"
                key_name, _, subkey = raw_key.partition("/")
                if key_name:
                    key = dir_.keys[key_name]
                    if not subkey:
                        key.value = value.replace("\n", " ")
                    elif subkey == "reset":
                        key.reset = _parse_bool(value, context=context)
                    else:
                        raise ValueError(f"{context}: unsupported option")
                else:  # option applies to directory
                    if subkey == "reset":
                        dir_.reset = _parse_bool(value, context=context)
                    else:
                        raise ValueError(f"{context}: unsupported option")
    return root
