# Copyright 2016 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os


class AutoDocWriter(object):
    """
    Class for parsing module api and generating Sphinx format docs automatically.
    """

    def __init__(self, module_path, save_to_dir=None, module_api_pattern="__all__",
                 doc_extension=".rst", doc_dir="docs", sort_item=False):
        """
        :param module_path: Path of module to generate docs.
        :param save_to_dir: None or the path to save generated documents.
        :param module_api_pattern: Pattern for paring api of module, default is
         '__all__'.
        :param doc_extension: Suffix of document file, default is '.rst'
        :param doc_dir: Name of document folder, default is 'docs'
        :param sort_item: Determine if sort items before generate docs, default
         is False.
        """
        self._module_path = module_path
        self._save_to_dir = "." if save_to_dir is None else save_to_dir
        self._module_api_pattern = module_api_pattern
        self._doc_extension = doc_extension
        self._doc_dir = doc_dir
        self._sort_item = sort_item

    @staticmethod
    def _make_directory_path(path_array, save_to):
        return os.path.join(save_to, '/'.join(path_array))

    @staticmethod
    def _makedir_if_not_exists(dir_name):
        # Create a directory with name `dir_name` if not exist
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

    def _make_doc_file_path(self, simple_name, dir_name):
        """
        :param simple_name: File name without suffix
        :param dir_name: Directory to place doc files
        :return: Full path to save generated doc files
        """
        return os.path.join(dir_name, simple_name + self._doc_extension)

    @staticmethod
    def _is_class(name):
        # Determine if a api is a class
        return name and name[0].isupper()

    @staticmethod
    def _is_function(name):
        # Determine if a api is a function
        return name and name[0].islower()

    @staticmethod
    def _is_python_init_file(file_name):
        # Determine if a file is __init__.py
        return file_name == "__init__.py"

    @staticmethod
    def _is_python_file(file_name):
        # Determine if a file is a python file
        return file_name and file_name.endswith(".py")

    @staticmethod
    def _split_path_to_array(full_path, start_dir):
        """
        Split a absolute path to array and get all dirs start from one dir'.
        :param full_path: Absolute path to split
        :param start_dir: Name of start dir
        :return: All dirs start from `start_dir`
        """
        paths = full_path.split('/')
        for i, item in enumerate(paths):
            if item == start_dir:
                return paths[i:]
        raise ValueError("Cannot find dir {0} in {1}".format(start_dir,
                                                             full_path))

    @staticmethod
    def _save_to_file(file_name, content):
        """
        :param file_name: Name of file to write into
        :param content: Content to be written into file
        """
        with open(file_name, "wb") as file_point:
            file_point.write(content)

    @staticmethod
    def _read_from_file(file_path):
        """
        :param file_path: Path of file to read
        :return: Content of file
        """
        with open(file_path, "r") as file_point:
            return file_point.read()

    @staticmethod
    def _remove_quote(text):
        if text.startswith("'") or text.startswith('"'):
            text = text[1:]
        if text.endswith("'") or text.endswith('"'):
            text = text[:-1]
        return text

    def _parse_module(self, file_path):
        """
        Read a file and get content of module api. For example, a file
        which content is:
            xxx __all__ = ['abc', 'abc'] xxx and pattern is _all_
        Then '[abc, abc]' is final result to be returned.
        :param file_path: Location of file to be read
        :return: A array contained in `module_api_pattern`
        """
        file_content = self._read_from_file(file_path)
        api_pos = file_content.find(self._module_api_pattern)
        if api_pos == -1:
            raise ValueError("Cannot find {0} in '{1}'".format(self._module_api_pattern,
                                                               os.path.basename(file_path)))

        start_pos = file_content.find("[", api_pos + 1)
        end_pos = file_content.find("]", start_pos + 1)
        api_list = file_content[start_pos + 1:end_pos]
        return [self._remove_quote(item.strip()) for item in api_list.split(",")]

    def _get_module_api(self, file_absolute_path):
        """
        Extract class names and function names from a file.
        :param file_absolute_path: Absolute path of file to parse
        :return: Class names and function names
        """
        classes, functions = [], []
        try:
            for name in self._parse_module(file_absolute_path):
                if self._is_class(name):
                    classes.append(name)
                elif self._is_function(name):
                    functions.append(name)
        except Exception as e:
            print "Error {0} ".format(str(e))
        return classes, functions

    @staticmethod
    def _make_index_content(max_depth, root_dir_name):
        return (".. solnlib documentation master file, created by\n"
                "   sphinx-quickstart on Sat Feb 27 15:17:42 2016.\n"
                "   You can adapt this file completely to your liking, \
                but it should at least\n"
                "   contain the root `toctree` directive.\n\n"
                "Welcome to Splunk Solution Library API reference.\n"
                "=================================================\n\n"
                ".. toctree::\n"
                "   :maxdepth: {0}\n"
                "   :numbered:\n\n"
                "   {1}/init.rst\n\n\n"
                "Indices and tables\n"
                "==================\n\n"
                "* :ref:`genindex`\n"
                "* :ref:`modindex`\n"
                "* :ref:`search`\n").format(max_depth, root_dir_name)

    def _is_module(self, file_name):
        """
        Determine if a file is a module which is a python file, but not __init__.py
        """
        return self._is_python_file(file_name) and not self._is_python_init_file(file_name)

    def _py_to_doc(self, name):
        # Make doc file name from file name. such as `abc.py` will
        # get (`abc`+doc_extension)
        return "%s%s" % (name.split('.')[0], self._doc_extension)

    def _get_max_depth_and_file_items(self, root, start_dir):
        """
        Find max depth for a folder 'root' started from dir 'start_dir'. Examples
        root: a/b/c/d
        start_dir: b
        Get subdir b/c/d which depth is 3 so 3 is returned. And also all python
        files under b are returned too.
        :param root: dir path
        :param start_dir: start dir name
        :return: Max depth from `start_dir` and all python files under `start_dir`
        """
        max_depth, file_items = 0, []
        for sub_root, _, sub_files in os.walk(root):
            sub_path_array = self._split_path_to_array(sub_root, start_dir)
            max_depth = max(max_depth, len(sub_path_array))

            if sub_root == root:
                file_items.extend(
                    [self._py_to_doc(item) for item in sub_files if self._is_module(item)])
            else:
                if os.path.exists(os.path.join(sub_root, "__init__.py")):
                    file_items.append(os.path.join(os.path.basename(sub_root),
                                                   "init{0}".format(self._doc_extension)))
        return max_depth, file_items

    def auto_doc(self):
        docs = os.path.join(self._save_to_dir, self._doc_dir)
        self._makedir_if_not_exists(docs)

        module_root = os.path.basename(self._module_path)
        save_to_dir = os.path.join(docs, module_root)
        self._makedir_if_not_exists(save_to_dir)

        root_max_depth = 0  # max depth from root dir

        for root, _, files in os.walk(self._module_path):
            print "Got a folder {0} ".format(root)

            current_dir_paths = self._split_path_to_array(root, module_root)
            current_dir_name = self._make_directory_path(current_dir_paths, docs)
            folder_name = current_dir_paths[-1]

            print "Current file path is {0}".format(current_dir_name)
            self._makedir_if_not_exists(current_dir_name)

            python_files = [item for item in files if self._is_python_file(item)]

            for single_file in python_files:
                simple_name = single_file.split('.')[0]
                file_absolute_path = os.path.join(root, single_file)

                if self._is_python_init_file(single_file):
                    auto_module = '.'.join(current_dir_paths)
                    doc_file_path = self._make_doc_file_path("init", current_dir_name)
                    content = folder_name + "\n" + len(folder_name) * "=" + "\n\n"

                    max_depth, file_items = self._get_max_depth_and_file_items(root,
                                                                               module_root)
                    print "Got max depth %s" % max_depth

                    content += ".. automodule:: {0}\n" \
                               "\n.. toctree::\n" \
                               "   :maxdepth: {1}\n\n".format(auto_module, max_depth)
                    if self._sort_item:
                        file_items = sorted(file_items)
                    for item in file_items:
                        content += "   %s\n" % item

                    root_max_depth = max(root_max_depth, max_depth)

                elif self._is_python_file(single_file):

                    auto_module = "{0}.{1}".format('.'.join(current_dir_paths), simple_name)
                    doc_file_path = self._make_doc_file_path(simple_name,
                                                             current_dir_name)

                    content = simple_name + "\n" + len(simple_name) * "=" + "\n"
                    content += "\n.. automodule:: {0}\n\nAPIs\n----\n".format(auto_module)

                    classes, functions = self._get_module_api(file_absolute_path)
                    if self._sort_item:
                        classes, functions = sorted(classes), sorted(functions)

                    package_name = '.'.join(current_dir_paths)

                    def get_definition(name):
                        # Get a function or class definition with module path
                        return "{0}.{1}.{2}".format(package_name, simple_name, name)

                    for cs in classes:
                        content += "\n:class:`~{0}` class\n".format(get_definition(cs))
                    for func in functions:
                        content += "\n:func:`~{0}` function\n".format(get_definition(func))
                    # detail info part
                    content += "\nDetail Info\n-----------\n"

                    for cs in classes:
                        content += "\n.. autoclass:: {0}\n   :members:\n".format(cs)
                    for func in functions:
                        content += "\n.. autofunction:: {0}\n".format(func)
                else:
                    continue

                # save to doc file
                self._save_to_file(doc_file_path, content)

                # save index doc
                index_doc = os.path.join(docs, "index{0}".format(self._doc_extension))
                self._save_to_file(index_doc,
                                   self._make_index_content(root_max_depth, module_root))


if __name__ == "__main__":
    # auto generate rst documents
    doc_writer = AutoDocWriter("../solnlib", save_to_dir="../", sort_item=True)
    doc_writer.auto_doc()
