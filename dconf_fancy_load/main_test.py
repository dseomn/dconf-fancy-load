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

from collections.abc import Collection, Mapping, Sequence
import subprocess
import textwrap
from typing import Any
import unittest
from unittest import mock

from dconf_fancy_load import config
from dconf_fancy_load import main


class LoadTest(unittest.TestCase):

    def setUp(self) -> None:
        super().setUp()
        self._run = mock.create_autospec(subprocess.run, spec_set=True)

    def _load(self, *args: Any, **kwargs: Any) -> Collection[str]:
        """Calls load with appropriate mocks.

        Args:
            *args: Args to load.
            **kwargs: Ditto.

        Returns:
            Whatever load returns.
        """
        return main.load(*args, **kwargs, subprocess_run=self._run)

    def _mock_dconf_list(self, paths: Mapping[str, Sequence[str]]) -> None:
        """Mocks `dconf list`.

        Args:
            paths: Map from path passed to `donf list` to list of paths printed
                by `dconf list`.
        """

        def side_effect(
            args: Any,
            **kwargs: Any,
        ) -> subprocess.CompletedProcess[str]:
            completed_process = mock.create_autospec(
                subprocess.CompletedProcess, instance=True
            )
            if args[:2] != ["dconf", "list"]:
                return completed_process
            items = paths[args[2]]
            completed_process.stdout = "".join((item + "\n" for item in items))
            return completed_process

        self._run.side_effect = side_effect

    def test_set(self) -> None:
        preserved = self._load(
            config.Dir(
                subdirs={
                    "some-dir": config.Dir(
                        subdirs={
                            "other-dir": config.Dir(
                                keys={
                                    "kumquat": config.Key(value="17"),
                                    "apple": config.Key(value="'orange'"),
                                },
                            ),
                        },
                    ),
                },
                keys={"foo": config.Key(value="'bar'")},
            )
        )
        self.assertEqual(
            {
                "/some-dir/other-dir/kumquat",
                "/some-dir/other-dir/apple",
                "/foo",
            },
            set(preserved),
        )
        expected_calls = []
        for path, keyfile in (
            (
                "/",
                textwrap.dedent(
                    """\
                        [/]
                        foo='bar'
                    """
                ),
            ),
            (
                "/some-dir/other-dir/",
                textwrap.dedent(
                    """\
                        [/]
                        apple='orange'
                        kumquat=17
                    """
                ),
            ),
        ):
            expected_calls.append(
                mock.call(
                    ["dconf", "load", path],
                    input=keyfile,
                    text=True,
                    check=True,
                )
            )
        self.assertSequenceEqual(
            sorted(expected_calls), sorted(self._run.mock_calls)
        )

    def test_reset(self) -> None:
        self._mock_dconf_list(
            {
                "/": ["foo", "bar", "some-dir/"],
                "/some-dir/": ["other-dir/", "apple", "kumquat"],
                "/some-dir/other-dir/": ["apple", "kumquat"],
            }
        )
        preserved = self._load(
            config.Dir(
                subdirs={
                    "quux": config.Dir(reset=False),
                    "some-dir": config.Dir(
                        reset=True,
                        subdirs={
                            "other-dir": config.Dir(
                                reset=False,
                                keys={"kumquat": config.Key(reset=True)},
                            ),
                        },
                        keys={"apple": config.Key(reset=False)},
                    ),
                },
                keys={"foo": config.Key(reset=True)},
            )
        )
        self.assertEqual({"/quux/", "/some-dir/"}, preserved)
        expected_reset_paths = (
            "/foo",  # key has reset=True
            "/some-dir/other-dir/kumquat",  # key has reset=True
            "/some-dir/kumquat",  # /some-dir/ has reset=True
        )
        expected_reset_calls = [
            mock.call(["dconf", "reset", "-f", path], check=True)
            for path in expected_reset_paths
        ]
        actual_reset_calls = [
            call for call in self._run.mock_calls if call[1][0][1] == "reset"
        ]
        self.assertSequenceEqual(
            sorted(expected_reset_calls), sorted(actual_reset_calls)
        )

    def test_dry_run_does_not_write_to_dconf(self) -> None:
        self._mock_dconf_list(
            {
                "/": ["foo", "bar", "some-dir/"],
                "/some-dir/": ["foo"],
            }
        )
        self._load(
            config.Dir(
                subdirs={
                    "some-dir": config.Dir(
                        keys={"foo": config.Key(reset=True)},
                    ),
                },
                keys={
                    "foo": config.Key(reset=True),
                    "bar": config.Key(value="42"),
                },
            ),
            dry_run=True,
        )
        actual_write_calls = [
            call for call in self._run.mock_calls if call[1][0][1] != "list"
        ]
        self.assertSequenceEqual((), actual_write_calls)


if __name__ == "__main__":
    unittest.main()
