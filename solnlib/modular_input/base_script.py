#
# Copyright 2024 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import importlib
import json
import os.path
from abc import ABC

from splunklib import modularinput as smi


class BaseScript(smi.Script, ABC):
    """A class that by default takes scheme parameters from (...).args.json
    files.

    For example, if the subclass is located in example.py, it will take parameters from example.args.json.

    Example content of (...).args.json:
        {
            "name": "...",
            "description": "...",
            "entity": [
                {
                    "field": "some_field"
                }
            ]
        ]
    """

    def get_scheme(self):
        scheme = smi.Scheme(self.args.get("name"))
        scheme.description = self.args.get("description")
        scheme.use_external_validation = self.args.get("use_external_validation", True)
        scheme.streaming_mode_xml = self.args.get("streaming_mode_xml", True)
        scheme.use_single_instance = self.args.get("use_single_instance", False)

        scheme.add_argument(
            smi.Argument(
                "name", title="Name", description="Name", required_on_create=True
            )
        )

        for entity in self._args.get("entity", []):
            scheme.add_argument(
                smi.Argument(
                    entity["field"],
                    required_on_create=entity.get("required", False),
                )
            )

        return scheme

    @property
    def args(self):
        if not hasattr(self, "_args"):
            self._args = self._load_args()

        return self._args

    def _load_args(self):
        subcls_module = importlib.import_module(self.__module__)
        path_split = os.path.splitext(subcls_module.__file__)[0]
        args_file = "%s.args.json" % path_split

        if not os.path.isfile(args_file):
            return {}

        with open(args_file) as fp:
            return json.load(fp)
