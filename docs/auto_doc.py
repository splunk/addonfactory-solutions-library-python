# Copyright 2016 Splunk, Inc.
# SPDX-FileCopyrightText: 2020 2020
#
# SPDX-License-Identifier: Apache-2.0

"""
This program is used to construct sphinx rst directory tree from source code.
"""

import importlib
import inspect
import os
import os.path as op
import re
import shutil
import sys
import time

cur_dir = op.dirname(op.abspath(__file__))


class AutoDoc(object):
    """
    Class for parsing module api and generating Sphinx format
    docs automatically.
    """

    def __init__(self, source_dir, dest_dir, lib_name, lib_welcome_msg):
        self._source_dir = source_dir[:-1] if source_dir.endswith("/") else source_dir
        self._dest_dir = dest_dir[:-1] if dest_dir.endswith("/") else dest_dir
        self._lib_name = lib_name
        self._lib_welcome_msg = lib_welcome_msg
        self._classNum = 0
        self._methodNum = 0
        self._funcNum = 0

    def _create_index(self):
        index_content = (
            ".. {lib_name} documentation master file, created by sphinx-quickstart\n"
            "   on {create_time}. You can adapt this file completely\n"
            "   to your liking, but it should at least contain the root `toctree`\n"
            "   directive.\n\n"
            "{lib_welcome_msg}\n"
            "==========================================================\n\n"
            ".. toctree::\n"
            "   :maxdepth: 2\n"
            "   :numbered:\n\n"
            "   {lib_name}/init.rst\n\n\n"
            "Indices and tables\n"
            "==================\n\n"
            "* :ref:`genindex`\n"
            "* :ref:`modindex`\n"
            "* :ref:`search`\n"
        ).format(
            create_time=time.asctime(),
            lib_name=self._lib_name,
            lib_welcome_msg=self._lib_welcome_msg,
        )

        with open(op.join(self._dest_dir, "index.rst"), "w") as fp:
            fp.write(index_content)

    def _valid_module(self, source_dir, file_name):
        if file_name.endswith(".py"):
            return True

        if op.isdir(op.join(source_dir, file_name)) and op.exists(
            op.join(source_dir, file_name, "__init__.py")
        ):
            return True

        return False

    def _package_content(self, package_names, sub_modules):
        package_name = package_names[len(package_names) - 1]
        package_import_path = ".".join(package_names)

        content = package_name + "\n"
        content += "=" * len(package_name) + "\n\n"
        content += (
            ".. automodule:: {package_import_path}".format(
                package_import_path=package_import_path
            )
            + "\n\n"
        )
        content += ".. toctree::" + "\n"
        content += "   :maxdepth: 2" + "\n\n"
        for sub_module in sub_modules:
            if sub_module.endswith(".py"):
                content += "   {sub_rst}\n".format(
                    sub_rst=sub_module.replace(".py", ".rst")
                )
            elif sub_module != "packages":
                content += "   {sub_rst}\n".format(
                    sub_rst=op.join(sub_module, "init.rst")
                )

        return content

    def _sub_module_content(self, package_names, sub_module):
        sub_module_name = sub_module.replace(".py", "")
        sub_module_import_path = ".".join(package_names + [sub_module_name])
        sub_module = importlib.import_module(sub_module_import_path)
        attrs = sub_module.__all__

        content = sub_module_name + "\n"
        content += "=" * len(sub_module_name) + "\n\n"
        content += (
            ".. automodule:: {sub_module_import_path}".format(
                sub_module_import_path=sub_module_import_path
            )
            + "\n\n"
        )
        content += "APIs" + "\n"
        content += "-" * len("APIs") + "\n\n"
        for attr in attrs:
            if inspect.isfunction(getattr(sub_module, attr)):
                content += (
                    ":func:`{sub_module_import_path}.{func_name}` function".format(
                        sub_module_import_path=sub_module_import_path, func_name=attr
                    )
                    + "\n\n"
                )
                self._funcNum += 1
            elif inspect.isclass(getattr(sub_module, attr)):
                content += (
                    ":class:`{sub_module_import_path}.{class_name}` class".format(
                        sub_module_import_path=sub_module_import_path, class_name=attr
                    )
                    + "\n\n"
                )
                self._classNum += 1
                for a in dir(getattr(sub_module, attr)):
                    if not a.startswith("_"):
                        self._methodNum += 1

            else:
                raise ValueError(
                    "Invalid attribute: %s of sub-module: %s.",
                    attr,
                    sub_module_import_path,
                )
        content += "Detail Info" + "\n"
        content += "-" * len("Detail Info") + "\n\n"
        for attr in attrs:
            if inspect.isfunction(getattr(sub_module, attr)):
                content += (
                    ".. autofunction:: {func_name}".format(func_name=attr) + "\n\n"
                )
            elif inspect.isclass(getattr(sub_module, attr)):
                content += ".. autoclass:: {class_name}".format(class_name=attr) + "\n"
                content += "   :members:" + "\n\n"
            else:
                raise ValueError(
                    "Invalid attribute: %s of sub-module: %s.",
                    attr,
                    sub_module_import_path,
                )

        return content

    def _recursive_create_docs(self, source_dir, dest_dir, package_names):
        if "packages" in package_names:
            return

        os.mkdir(dest_dir)

        sub_modules = os.listdir(source_dir)
        sub_modules = [
            module
            for module in sub_modules
            if self._valid_module(source_dir, module) and module != "__init__.py"
        ]

        with open(op.join(dest_dir, "init.rst"), "w") as fp:
            fp.write(self._package_content(package_names, sub_modules))

        for sub_module in sub_modules:
            if sub_module.endswith(".py"):
                sub_module_content = self._sub_module_content(package_names, sub_module)
                with open(
                    op.join(dest_dir, sub_module.replace(".py", ".rst")), "w"
                ) as fp:
                    fp.write(sub_module_content)
            else:
                self._recursive_create_docs(
                    op.join(source_dir, sub_module),
                    op.join(dest_dir, sub_module),
                    package_names + [sub_module],
                )

    def _create_docs(self):
        if op.exists(op.join(dest_dir, lib_name)):
            shutil.rmtree(op.join(dest_dir, lib_name))

        self._recursive_create_docs(
            self._source_dir, op.join(self._dest_dir, lib_name), [lib_name]
        )

    def auto_doc(self):
        sys.path.insert(0, op.dirname(self._source_dir))
        self._create_index()
        self._create_docs()

    def info(self):
        print "Total classes: ", self._classNum
        print "Total methods: ", self._methodNum
        print "Total funcs: ", self._funcNum


if __name__ == "__main__":
    lib_name = "solnlib"
    lib_welcome_msg = "Welcome to Splunk Solution Library (%s) API reference."

    source_dir = op.join(op.dirname(cur_dir), lib_name)
    dest_dir = cur_dir
    with open(op.join(source_dir, "__init__.py"), "r") as fd:
        version = re.search(
            r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', fd.read(), re.MULTILINE
        ).group(1)
    auto_doc = AutoDoc(source_dir, dest_dir, lib_name, lib_welcome_msg % version)
    auto_doc.auto_doc()
    auto_doc.info()
