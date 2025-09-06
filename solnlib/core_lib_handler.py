#
# Copyright 2025 Splunk Inc.
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

import os
import sys
import re
from types import ModuleType
import shutil
import importlib

def _is_module_from_splunk_core(lib_module: ModuleType) -> bool:
    """
    Check if the imported module is from the Splunk-provided libraries.
    """
    core_site_packages_regex = _get_core_site_packages_regex()

    splunk_site_packages_paths = [
        path for path in sys.path if core_site_packages_regex.search(path)
    ]

    return any(
        _is_core_site_package_path(
            splunk_site_packages_path, lib_module.__name__, lib_module.__file__
        )
        for splunk_site_packages_path in splunk_site_packages_paths
    )


def _is_core_site_package_path(
    core_site_packages_directory: str, module_name: str, module_path: str
) -> bool:
    """
    Check if the module path originates from a core site-packages directory.
    """
    return os.path.join(core_site_packages_directory, module_name) in module_path


def _get_core_site_packages_regex() -> re.Pattern:
    """
    Get the regex pattern for matching site-packages directories.
    """
    sep = os.path.sep
    sep_escaped = re.escape(sep)

    return (
        re.compile(
            r"Python(?:-\d+(?:\.\d+)?)?"
            + sep_escaped
            + r"lib"
            + sep_escaped
            + r"site-packages$",
            re.IGNORECASE,
        )
        if sys.platform.startswith("win32")
        else re.compile(
            r"lib"
            + r"("
            + sep_escaped
            + r"python\d+(\.\d+)?"
            + r")?"
            + sep_escaped
            + r"site-packages$"
        )
    )


def _cache_lib(lib_name: str):
    """
    Import the Splunk-shipped library first, before adding TA paths to sys.path, to ensure it is cached.
    This way, even if the TA path added to sys.path contains the specified library,
    Python will always reference the already cached library from the Splunk Python path.
    """
    lib_module = importlib.import_module(lib_name)
    assert _is_module_from_splunk_core(
        lib_module
    ), f"The module {lib_name} is not from Splunk core site-packages."

def _get_app_path(absolute_path: str, current_script_folder: str = "lib") -> str:
    """Returns app path."""
    marker = os.path.join(os.path.sep, "etc", "apps")
    start = absolute_path.rfind(marker)
    if start == -1:
        return None
    end = absolute_path.find(current_script_folder, start)
    if end == -1:
        return None
    end = end - 1
    path = absolute_path[:end]
    return path

def _remove_lib_folder(lib_name: str):
    """
    List and attempt to remove any folders directly under the 'lib' directory that contain lib_name in their name.
    Handles exceptions during removal, allowing the script to proceed even if errors occur.
    """

    try:
        app_dir = _get_app_path(os.path.abspath(__file__))
        lib_dir = os.path.join(app_dir, "lib")

        for entry in os.listdir(lib_dir):
            entry_path = os.path.join(lib_dir, entry)
            if os.path.isdir(entry_path) and lib_name in entry:
                try:
                    shutil.rmtree(entry_path)
                except Exception:
                    # Bypassing exceptions to ensure uninterrupted execution
                    pass
    except Exception:
        # Bypassing exceptions to ensure uninterrupted execution
        pass


def handle_splunk_provided_lib(lib_name: str):
    _cache_lib(lib_name)
    _remove_lib_folder(lib_name)
