# Copyright 2016 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the 'License'): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

'''
This program is used to construct sphinx rst directory tree from source code.
'''

import sys
import os
import time
import shutil
import inspect
import importlib
import os.path as op

cur_dir = op.dirname(op.abspath(__file__))


class AutoDoc(object):
    '''
    Class for parsing module api and generating Sphinx format
    docs automatically.
    '''

    def __init__(self, source_dir, dest_dir, lib_name, lib_welcome_msg):
        self._source_dir = \
            source_dir[:-1] if source_dir.endswith('/') else source_dir
        self._dest_dir = \
            dest_dir[:-1] if dest_dir.endswith('/') else dest_dir
        self._lib_name = lib_name
        self._lib_welcome_msg = lib_welcome_msg

    def _create_index(self):
        index_content = (
            '.. {lib_name} documentation master file, created by sphinx-quickstart\n'
            '   on {create_time}. You can adapt this file completely\n'
            '   to your liking, but it should at least contain the root `toctree`\n'
            '   directive.\n\n'
            '{lib_welcome_msg}\n'
            '=================================================\n\n'
            '.. toctree::\n'
            '   :maxdepth: 2\n'
            '   :numbered:\n\n'
            '   {lib_name}/init.rst\n\n\n'
            'Indices and tables\n'
            '==================\n\n'
            '* :ref:`genindex`\n'
            '* :ref:`modindex`\n'
            '* :ref:`search`\n').format(
                create_time=time.asctime(),
                lib_name=self._lib_name,
                lib_welcome_msg=self._lib_welcome_msg)

        with open(op.join(self._dest_dir, 'index.rst'), 'w') as fp:
            fp.write(index_content)

    def _valid_module(self, source_dir, file_name):
        if file_name.endswith('.py'):
            return True

        if op.isdir(op.join(source_dir, file_name)) and \
           op.exists(op.join(source_dir, file_name, '__init__.py')):
            return True

        return False

    def _package_content(self, package_names, sub_modules):
        package_name = package_names[len(package_names) - 1]
        package_import_path = '.'.join(package_names)

        content = package_name + '\n'
        content += '=' * len(package_name) + '\n\n'
        content += '.. automodule:: {package_import_path}'.format(
            package_import_path=package_import_path) + '\n\n'
        content += '.. toctree::' + '\n'
        content += '   :maxdepth: 2' + '\n\n'
        for sub_module in sub_modules:
            if sub_module.endswith('.py'):
                content += '   {sub_rst}\n'.format(
                    sub_rst=sub_module.replace('.py', '.rst'))
            else:
                content += '   {sub_rst}\n'.format(
                    sub_rst=op.join(sub_module, 'init.rst'))

        return content

    def _sub_module_content(self, package_names, sub_module):
        sub_module_name = sub_module.replace('.py', '')
        sub_module_import_path = '.'.join(
            package_names + [sub_module_name])
        sub_module = importlib.import_module(sub_module_import_path)
        attrs = sub_module.__all__

        content = sub_module_name + '\n'
        content += '=' * len(sub_module_name) + '\n\n'
        content += '.. automodule:: {sub_module_import_path}'.format(
            sub_module_import_path=sub_module_import_path) + '\n\n'
        content += 'APIs' + '\n'
        content += '-' * len('APIs') + '\n\n'
        for attr in attrs:
            if inspect.isfunction(getattr(sub_module, attr)):
                content += ':func:`{sub_module_import_path}.{func_name}` function'.format(
                    sub_module_import_path=sub_module_import_path,
                    func_name=attr) + '\n\n'
            elif inspect.isclass(getattr(sub_module, attr)):
                content += ':class:`{sub_module_import_path}.{class_name}` class'.format(
                    sub_module_import_path=sub_module_import_path,
                    class_name=attr) + '\n\n'
            else:
                raise ValueError('Invalid attribute: %s of sub-module: %s.',
                                 attr, sub_module_import_path)
        content += 'Detail Info' + '\n'
        content += '-' * len('Detail Info') + '\n\n'
        for attr in attrs:
            if inspect.isfunction(getattr(sub_module, attr)):
                content += '.. autofunction:: {func_name}'.format(func_name=attr) + '\n\n'
            elif inspect.isclass(getattr(sub_module, attr)):
                content += '.. autoclass:: {class_name}'.format(class_name=attr) + '\n'
                content += '   :members:' + '\n\n'
            else:
                raise ValueError('Invalid attribute: %s of sub-module: %s.',
                                 attr, sub_module_import_path)

        return content

    def _recursive_create_docs(self, source_dir, dest_dir, package_names):
        os.mkdir(dest_dir)

        sub_modules = os.listdir(source_dir)
        sub_modules = [module for module in sub_modules
                       if self._valid_module(source_dir, module) and
                       module != '__init__.py']

        with open(op.join(dest_dir, 'init.rst'), 'w') as fp:
            fp.write(self._package_content(package_names, sub_modules))

        for sub_module in sub_modules:
            if sub_module.endswith('.py'):
                sub_module_content = self._sub_module_content(package_names,
                                                              sub_module)
                with open(op.join(dest_dir, sub_module.replace('.py', '.rst')), 'w') as fp:
                    fp.write(sub_module_content)
            else:
                self._recursive_create_docs(
                    op.join(source_dir, sub_module),
                    op.join(dest_dir, sub_module),
                    package_names + [sub_module])

    def _create_docs(self):
        if op.exists(op.join(dest_dir, lib_name)):
            shutil.rmtree(op.join(dest_dir, lib_name))

        self._recursive_create_docs(self._source_dir,
                                    op.join(self._dest_dir, lib_name),
                                    [lib_name])

    def auto_doc(self):
        sys.path.insert(0, op.dirname(self._source_dir))
        self._create_index()
        self._create_docs()


if __name__ == '__main__':
    lib_name = 'solnlib'
    lib_welcome_msg = 'Welcome to Splunk Solution Library API reference.'

    source_dir = op.join(op.dirname(cur_dir), lib_name)
    dest_dir = cur_dir
    auto_doc = AutoDoc(source_dir, dest_dir,
                       lib_name, lib_welcome_msg)
    auto_doc.auto_doc()
