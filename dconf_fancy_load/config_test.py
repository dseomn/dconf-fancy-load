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

from collections.abc import Mapping
import pathlib
import textwrap

import pytest

from dconf_fancy_load import config


def _write_files(path: pathlib.Path, files: Mapping[str, str]) -> None:
    for name, contents in files.items():
        (path / name).write_text(contents)


def test_dir_get_subdir() -> None:
    root = config.Dir()
    assert root.get_subdir(("foo", "bar")) is root.subdirs["foo"].subdirs["bar"]


@pytest.mark.parametrize(
    ("files", "error_regex"),
    (
        ({"foo.ini.jinja": "[/]\n/reset=kumquat"}, "not a boolean"),
        ({"foo.ini.jinja": "[/]\n/kumquat=true"}, "unsupported option"),
        ({"foo.ini.jinja": "[/]\nfoo/kumquat=true"}, "unsupported option"),
    ),
)
def test_get_error(
    files: Mapping[str, str],
    error_regex: str,
    tmp_path: pathlib.Path,
) -> None:
    _write_files(tmp_path, files)
    with pytest.raises(ValueError, match=error_regex):
        config.get(tmp_path)


@pytest.mark.parametrize(
    ("files", "expected"),
    (
        ({}, config.Dir()),
        ({"ignored-file": "foo"}, config.Dir()),
        (
            # Test that keys are case sensitive.
            {
                "foo.ini.jinja": textwrap.dedent(
                    """
                    [/]
                    FOO=1
                    foo=2
                    """
                ),
            },
            config.Dir(
                keys={
                    "FOO": config.Key(value="1"),
                    "foo": config.Key(value="2"),
                },
            ),
        ),
        (
            # Test jinja.
            {
                "foo.ini.jinja": textwrap.dedent(
                    """
                    [/]
                    foo={{ 1 + 2 }}
                    """
                ),
            },
            config.Dir(
                keys={
                    "foo": config.Key(value="3"),
                },
            ),
        ),
        (
            # Test subdirectories, directory reset, key set, and key reset.
            {
                "foo.ini.jinja": textwrap.dedent(
                    """
                    [foo/bar]
                    /reset=true
                    baz=1
                    quux/reset=false
                    """
                ),
            },
            config.Dir(
                subdirs={
                    "foo": config.Dir(
                        subdirs={
                            "bar": config.Dir(
                                reset=True,
                                keys={
                                    "baz": config.Key(value="1"),
                                    "quux": config.Key(reset=False),
                                },
                            ),
                        },
                    ),
                },
            ),
        ),
        (
            # Test multi-line values.
            {
                "foo.ini.jinja": textwrap.dedent(
                    """
                    [/]
                    foo=
                        [
                            1,
                            2
                        ]
                    """
                ),
            },
            config.Dir(
                keys={
                    "foo": config.Key(value=" [ 1, 2 ]"),
                },
            ),
        ),
        (
            # Test file merging.
            {
                "0.ini.jinja": textwrap.dedent(
                    """
                    [/]
                    /reset=false
                    value-overridden='old'
                    reset-overridden/reset=true
                    foo=1
                    """
                ),
                "1.ini.jinja": textwrap.dedent(
                    """
                    [/]
                    /reset=true
                    value-overridden='new'
                    reset-overridden/reset=false
                    bar=2
                    """
                ),
            },
            config.Dir(
                reset=True,
                keys={
                    "value-overridden": config.Key(value="'new'"),
                    "reset-overridden": config.Key(reset=False),
                    "foo": config.Key(value="1"),
                    "bar": config.Key(value="2"),
                },
            ),
        ),
    ),
)
def test_get(
    files: Mapping[str, str],
    expected: config.Dir,
    tmp_path: pathlib.Path,
) -> None:
    _write_files(tmp_path, files)
    assert config.get(tmp_path) == expected
