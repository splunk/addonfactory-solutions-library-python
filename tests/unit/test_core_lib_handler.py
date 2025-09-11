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
import tempfile
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from solnlib import core_lib_handler


class TestHandleSplunkProvidedLib:
    """Test cases for handle_splunk_provided_lib function."""

    @patch('solnlib.core_lib_handler._cache_lib')
    @patch('solnlib.core_lib_handler._remove_lib_folder')
    def test_handle_splunk_provided_lib_calls_both_functions(
        self, mock_remove_lib_folder, mock_cache_lib
    ):
        """Test that handle_splunk_provided_lib calls both _cache_lib and _remove_lib_folder."""
        lib_name = "test_library"
        
        core_lib_handler.handle_splunk_provided_lib(lib_name)
        
        mock_cache_lib.assert_called_once_with(lib_name)
        mock_remove_lib_folder.assert_called_once_with(lib_name)

    @patch('solnlib.core_lib_handler._cache_lib')
    @patch('solnlib.core_lib_handler._remove_lib_folder')
    def test_handle_splunk_provided_lib_execution_order(
        self, mock_remove_lib_folder, mock_cache_lib
    ):
        """Test that _cache_lib is called before _remove_lib_folder."""
        lib_name = "test_library"
        
        # Użyjemy side_effect aby sprawdzić kolejność wywołań
        call_order = []
        mock_cache_lib.side_effect = lambda x: call_order.append('cache')
        mock_remove_lib_folder.side_effect = lambda x: call_order.append('remove')
        
        core_lib_handler.handle_splunk_provided_lib(lib_name)
        
        assert call_order == ['cache', 'remove']


class TestCacheLib:
    """Test cases for _cache_lib function."""

    @patch('solnlib.core_lib_handler.importlib.import_module')
    @patch('solnlib.core_lib_handler._is_module_from_splunk_core')
    def test_cache_lib_success(self, mock_is_splunk_core, mock_import_module):
        """Test successful caching of a Splunk core library."""
        lib_name = "splunk_library"
        mock_module = MagicMock(spec=ModuleType)
        mock_import_module.return_value = mock_module
        mock_is_splunk_core.return_value = True
        
        core_lib_handler._cache_lib(lib_name)
        
        mock_import_module.assert_called_once_with(lib_name)
        mock_is_splunk_core.assert_called_once_with(mock_module)

    @patch('solnlib.core_lib_handler.importlib.import_module')
    @patch('solnlib.core_lib_handler._is_module_from_splunk_core')
    def test_cache_lib_not_from_splunk_core(self, mock_is_splunk_core, mock_import_module):
        """Test that _cache_lib raises AssertionError when module is not from Splunk core."""
        lib_name = "external_library"
        mock_module = MagicMock(spec=ModuleType)
        mock_import_module.return_value = mock_module
        mock_is_splunk_core.return_value = False
        
        with pytest.raises(AssertionError) as exc_info:
            core_lib_handler._cache_lib(lib_name)
        
        assert f"The module {lib_name} is not from Splunk core site-packages." in str(exc_info.value)
        mock_import_module.assert_called_once_with(lib_name)
        mock_is_splunk_core.assert_called_once_with(mock_module)

    @patch('solnlib.core_lib_handler.importlib.import_module')
    def test_cache_lib_import_error(self, mock_import_module):
        """Test that _cache_lib propagates ImportError when module cannot be imported."""
        lib_name = "nonexistent_library"
        mock_import_module.side_effect = ImportError(f"No module named '{lib_name}'")
        
        with pytest.raises(ImportError):
            core_lib_handler._cache_lib(lib_name)
        
        mock_import_module.assert_called_once_with(lib_name)


class TestRemoveLibFolder:
    """Test cases for _remove_lib_folder function."""

    def test_remove_lib_folder_success(self):
        """Test successful removal of library folders."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock app structure
            app_dir = os.path.join(temp_dir, "test_app")
            lib_dir = os.path.join(app_dir, "lib")
            os.makedirs(lib_dir)
            
            # Create test folders
            lib_name = "urllib3"
            test_folders = [
                "urllib3-2.0.7",
                "urllib3_secure_extra",
                "other_library",
                "urllib3.dist-info"
            ]
            
            for folder in test_folders:
                folder_path = os.path.join(lib_dir, folder)
                os.makedirs(folder_path)
                # Add a test file to make sure the folder is not empty
                with open(os.path.join(folder_path, "test.py"), "w") as f:
                    f.write("# test file")
            
            # Mock _get_app_path to return our test app directory
            with patch('solnlib.core_lib_handler._get_app_path', return_value=app_dir):
                core_lib_handler._remove_lib_folder(lib_name)
            
            # Verify that folders containing lib_name were removed
            remaining_folders = os.listdir(lib_dir)
            assert "other_library" in remaining_folders
            assert "urllib3-2.0.7" not in remaining_folders
            assert "urllib3_secure_extra" not in remaining_folders
            assert "urllib3.dist-info" not in remaining_folders

    def test_remove_lib_folder_no_lib_dir(self):
        """Test _remove_lib_folder when lib directory doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = os.path.join(temp_dir, "test_app")
            os.makedirs(app_dir)
            # Don't create lib directory
            
            with patch('solnlib.core_lib_handler._get_app_path', return_value=app_dir):
                # Should not raise an exception
                core_lib_handler._remove_lib_folder("urllib3")

    def test_remove_lib_folder_app_path_none(self):
        """Test _remove_lib_folder when _get_app_path returns None."""
        with patch('solnlib.core_lib_handler._get_app_path', return_value=None):
            # Should not raise an exception
            core_lib_handler._remove_lib_folder("urllib3")

    def test_remove_lib_folder_permission_error(self):
        """Test _remove_lib_folder handles permission errors gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = os.path.join(temp_dir, "test_app")
            lib_dir = os.path.join(app_dir, "lib")
            os.makedirs(lib_dir)
            
            lib_name = "urllib3"
            folder_to_remove = os.path.join(lib_dir, "urllib3-2.0.7")
            os.makedirs(folder_to_remove)
            
            with patch('solnlib.core_lib_handler._get_app_path', return_value=app_dir), \
                 patch('shutil.rmtree', side_effect=PermissionError("Access denied")):
                
                # Should not raise an exception
                core_lib_handler._remove_lib_folder(lib_name)

    def test_remove_lib_folder_empty_lib_dir(self):
        """Test _remove_lib_folder when lib directory is empty."""
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = os.path.join(temp_dir, "test_app")
            lib_dir = os.path.join(app_dir, "lib")
            os.makedirs(lib_dir)
            
            with patch('solnlib.core_lib_handler._get_app_path', return_value=app_dir):
                # Should not raise an exception
                core_lib_handler._remove_lib_folder("urllib3")

    def test_remove_lib_folder_with_files_not_directories(self):
        """Test _remove_lib_folder ignores files and only processes directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = os.path.join(temp_dir, "test_app")
            lib_dir = os.path.join(app_dir, "lib")
            os.makedirs(lib_dir)
            
            lib_name = "urllib3"
            
            # Create a file with lib_name in its name (should be ignored)
            file_path = os.path.join(lib_dir, "urllib3_config.py")
            with open(file_path, "w") as f:
                f.write("# config file")
            
            # Create a directory with lib_name in its name (should be removed)
            dir_path = os.path.join(lib_dir, "urllib3-2.0.7")
            os.makedirs(dir_path)
            
            with patch('solnlib.core_lib_handler._get_app_path', return_value=app_dir):
                core_lib_handler._remove_lib_folder(lib_name)
            
            # File should remain, directory should be removed
            assert os.path.exists(file_path)
            assert not os.path.exists(dir_path)


class TestIsModuleFromSplunkCore:
    """Test cases for _is_module_from_splunk_core function."""

    @patch('solnlib.core_lib_handler._get_core_site_packages_regex')
    @patch('solnlib.core_lib_handler._is_core_site_package_path')
    def test_is_module_from_splunk_core_true(self, mock_is_core_path, mock_get_regex):
        """Test when module is from Splunk core."""
        mock_module = MagicMock(spec=ModuleType)
        mock_module.__name__ = "splunklib"
        mock_module.__file__ = "/opt/splunk/lib/python3.9/site-packages/splunklib/__init__.py"
        
        mock_regex = MagicMock()
        mock_regex.search.return_value = True
        mock_get_regex.return_value = mock_regex
        mock_is_core_path.return_value = True
        
        with patch('sys.path', ["/opt/splunk/lib/python3.9/site-packages"]):
            result = core_lib_handler._is_module_from_splunk_core(mock_module)
        
        assert result is True

    @patch('solnlib.core_lib_handler._get_core_site_packages_regex')
    def test_is_module_from_splunk_core_false_no_matching_paths(self, mock_get_regex):
        """Test when no sys.path entries match the regex."""
        mock_module = MagicMock(spec=ModuleType)
        mock_module.__name__ = "external_lib"
        mock_module.__file__ = "/home/user/external_lib/__init__.py"
        
        mock_regex = MagicMock()
        mock_regex.search.return_value = False
        mock_get_regex.return_value = mock_regex
        
        with patch('sys.path', ["/home/user", "/usr/local/lib"]):
            result = core_lib_handler._is_module_from_splunk_core(mock_module)
        
        assert result is False

    @patch('solnlib.core_lib_handler._get_core_site_packages_regex')
    @patch('solnlib.core_lib_handler._is_core_site_package_path')
    def test_is_module_from_splunk_core_false_no_match_in_paths(self, mock_is_core_path, mock_get_regex):
        """Test when paths match regex but module is not from core."""
        mock_module = MagicMock(spec=ModuleType)
        mock_module.__name__ = "external_lib"
        mock_module.__file__ = "/home/user/external_lib/__init__.py"
        
        mock_regex = MagicMock()
        mock_regex.search.return_value = True
        mock_get_regex.return_value = mock_regex
        mock_is_core_path.return_value = False
        
        with patch('sys.path', ["/opt/splunk/lib/python3.9/site-packages"]):
            result = core_lib_handler._is_module_from_splunk_core(mock_module)
        
        assert result is False


class TestIsCoreSitePackagePath:
    """Test cases for _is_core_site_package_path function."""

    def test_is_core_site_package_path_true(self):
        """Test when module path is from core site-packages."""
        core_dir = "/opt/splunk/lib/python3.9/site-packages"
        module_name = "splunklib"
        module_path = "/opt/splunk/lib/python3.9/site-packages/splunklib/__init__.py"
        
        result = core_lib_handler._is_core_site_package_path(
            core_dir, module_name, module_path
        )
        
        assert result is True

    def test_is_core_site_package_path_false(self):
        """Test when module path is not from core site-packages."""
        core_dir = "/opt/splunk/lib/python3.9/site-packages"
        module_name = "external_lib"
        module_path = "/home/user/external_lib/__init__.py"
        
        result = core_lib_handler._is_core_site_package_path(
            core_dir, module_name, module_path
        )
        
        assert result is False

    def test_is_core_site_package_path_partial_match(self):
        """Test when module name is a substring but not the exact path."""
        core_dir = "/opt/splunk/lib/python3.9/site-packages"
        module_name = "lib"
        module_path = "/home/user/mylib/__init__.py"
        
        result = core_lib_handler._is_core_site_package_path(
            core_dir, module_name, module_path
        )
        
        assert result is False

    def test_is_core_site_package_path_none_module_path(self):
        """Test when module_path is None."""
        core_dir = "/opt/splunk/lib/python3.9/site-packages"
        module_name = "splunklib"
        module_path = None
        
        # Should handle None gracefully
        with pytest.raises(TypeError):
            core_lib_handler._is_core_site_package_path(
                core_dir, module_name, module_path
            )


class TestGetCoreSitePackagesRegex:
    """Test cases for _get_core_site_packages_regex function."""

    @patch('sys.platform', 'win32')
    @patch('os.path.sep', '\\')
    def test_get_core_site_packages_regex_windows(self):
        """Test regex pattern for Windows platform."""
        regex = core_lib_handler._get_core_site_packages_regex()
        
        # Test Windows paths
        assert regex.search(r"C:\Python-3.9\lib\site-packages") is not None
        assert regex.search(r"C:\Program Files\Splunk\Python-3.9\lib\site-packages") is not None
        
        # Test case insensitivity on Windows
        assert regex.search(r"C:\python-3.9\LIB\SITE-PACKAGES") is not None

    @patch('sys.platform', 'linux')
    def test_get_core_site_packages_regex_unix(self):
        """Test regex pattern for Unix-like platforms."""
        regex = core_lib_handler._get_core_site_packages_regex()
        
        # Test Unix paths
        assert regex.search("/opt/splunk/lib/python3.9/site-packages") is not None
        assert regex.search("/usr/local/lib/site-packages") is not None
        assert regex.search("/usr/lib/site-packages") is not None
        assert regex.search("/opt/splunk/lib/site-packages") is not None
        
        # Test paths without python version
        assert regex.search("/usr/lib/site-packages") is not None

    def test_get_core_site_packages_regex_invalid_paths(self):
        """Test that regex correctly rejects invalid paths."""
        regex = core_lib_handler._get_core_site_packages_regex()
        
        # Paths that should NOT match
        assert regex.search("/home/user/myproject") is None
        assert regex.search("/opt/splunk/etc/apps") is None
        assert regex.search("/usr/bin") is None
        assert regex.search("site-packages") is None  # Missing lib directory
        assert regex.search("/opt/splunk/lib/python3.9/site-packages/pypng-0.0.20-py3.9.egg") is None
        assert regex.search("/opt/splunk/lib/python3.9/site-packages/IPy-1.0-py3.9.egg") is None
        assert regex.search("/opt/splunk/lib/python3.9/site-packages/bottle-0.12.25-py3.9.egg") is None


class TestGetAppPath:
    """Test cases for _get_app_path function."""

    @pytest.mark.parametrize(
        "absolute_path,current_script_folder,expected_result",
        [
            # Standard Splunk app structure
            (
                "/opt/splunk/etc/apps/my_app/lib/mymodule.py",
                "lib",
                "/opt/splunk/etc/apps/my_app"
            ),
            (
                "/opt/splunk/etc/apps/my_app/lib/mymodule/decorators.py",
                "lib",
                "/opt/splunk/etc/apps/my_app"
            ),
            # Different script folder
            (
                "/opt/splunk/etc/apps/my_app/bin/mymodule.py",
                "bin",
                "/opt/splunk/etc/apps/my_app"
            ),
            (
                "/opt/splunk/etc/apps/my_app/scripts/mymodule.py",
                "scripts",
                "/opt/splunk/etc/apps/my_app"
            ),
            # Nested structure
            (
                "/opt/splunk/etc/apps/my_app/lib/vendor/requests/api.py",
                "lib",
                "/opt/splunk/etc/apps/my_app"
            ),
            # Multiple etc/apps in path (should use the last one)
            (
                "/home/user/etc/apps/backup/opt/splunk/etc/apps/my_app/lib/mymodule.py",
                "lib",
                "/home/user/etc/apps/backup/opt/splunk/etc/apps/my_app"
            ),
        ],
    )
    def test_get_app_path_success_cases(self, absolute_path, current_script_folder, expected_result):
        """Test successful cases of _get_app_path function."""
        result = core_lib_handler._get_app_path(absolute_path, current_script_folder)
        assert result == expected_result

    @pytest.mark.parametrize(
        "absolute_path,current_script_folder",
        [
            # No etc/apps in path
            (
                "/home/user/myproject/lib/mymodule.py",
                "lib"
            ),
            # etc/apps exists but script folder doesn't exist after it
            (
                "/opt/splunk/etc/apps/my_app/default/app.conf",
                "lib"
            ),
            # Script folder exists but not after etc/apps
            (
                "/home/user/lib/myproject/etc/apps/config",
                "lib"
            ),
            # Empty path
            (
                "",
                "lib"
            ),
        ],
    )
    def test_get_app_path_returns_none(self, absolute_path, current_script_folder):
        """Test cases where _get_app_path should return None."""
        result = core_lib_handler._get_app_path(absolute_path, current_script_folder)
        assert result is None

    def test_get_app_path_default_current_script_folder(self):
        """Test that _get_app_path uses 'lib' as default current_script_folder."""
        absolute_path = "/opt/splunk/etc/apps/my_app/lib/mymodule.py"
        
        # Call without current_script_folder parameter
        result = core_lib_handler._get_app_path(absolute_path)
        expected = "/opt/splunk/etc/apps/my_app"
        
        assert result == expected

    def test_get_app_path_case_sensitivity(self):
        """Test that _get_app_path is case sensitive."""
        # This should work (lowercase)
        path_lower = "/opt/splunk/etc/apps/my_app/lib/mymodule.py"
        result_lower = core_lib_handler._get_app_path(path_lower, "lib")
        assert result_lower == "/opt/splunk/etc/apps/my_app"
        
        # This should not work (uppercase LIB)
        path_upper = "/opt/splunk/etc/apps/my_app/LIB/mymodule.py"
        result_upper = core_lib_handler._get_app_path(path_upper, "lib")
        assert result_upper is None

    def test_get_app_path_relative_path(self):
        """Test _get_app_path with relative path elements."""
        absolute_path = "/opt/splunk/etc/apps/my_app/../my_app/lib/mymodule.py"
        result = core_lib_handler._get_app_path(absolute_path, "lib")
        # Should still find the pattern despite .. in path
        assert "/my_app" in result

    def test_get_app_path_multiple_script_folders(self):
        """Test _get_app_path when script folder appears multiple times."""
        # lib appears twice, should use the one after etc/apps
        absolute_path = "/home/lib/backup/opt/splunk/etc/apps/my_app/lib/mymodule.py"
        result = core_lib_handler._get_app_path(absolute_path, "lib")
        expected = "/home/lib/backup/opt/splunk/etc/apps/my_app"
        assert result == expected

    @pytest.mark.parametrize(
        "absolute_path,current_script_folder,expected_result",
        [
            # Standard Splunk app structure - Windows
            (
                "C:\\Program Files\\Splunk\\etc\\apps\\my_app\\lib\\mymodule.py",
                "lib",
                "C:\\Program Files\\Splunk\\etc\\apps\\my_app"
            ),
            (
                "C:\\Program Files\\Splunk\\etc\\apps\\search\\lib\\searchcommands\\decorators.py",
                "lib",
                "C:\\Program Files\\Splunk\\etc\\apps\\search"
            ),
            # Different script folder - Windows
            (
                "C:\\Program Files\\Splunk\\etc\\apps\\my_app\\bin\\mymodule.py",
                "bin",
                "C:\\Program Files\\Splunk\\etc\\apps\\my_app"
            ),
            (
                "C:\\Program Files\\Splunk\\etc\\apps\\my_app\\scripts\\mymodule.py",
                "scripts",
                "C:\\Program Files\\Splunk\\etc\\apps\\my_app"
            ),
            # Nested structure - Windows
            (
                "C:\\Program Files\\Splunk\\etc\\apps\\my_app\\lib\\vendor\\requests\\api.py",
                "lib",
                "C:\\Program Files\\Splunk\\etc\\apps\\my_app"
            ),
            # Multiple etc\\apps in path - Windows
            (
                "D:\\backup\\etc\\apps\\old\\C:\\Program Files\\Splunk\\etc\\apps\\my_app\\lib\\mymodule.py",
                "lib",
                "D:\\backup\\etc\\apps\\old\\C:\\Program Files\\Splunk\\etc\\apps\\my_app"
            ),
        ],
    )
    def test_get_app_path_windows_success_cases(self, absolute_path, current_script_folder, expected_result):
        """Test successful cases of _get_app_path function with Windows paths."""
        with patch('os.path.join') as mock_join:
            # Mock os.path.join to return Windows-style paths
            mock_join.return_value = "\\etc\\apps"
            
            result = core_lib_handler._get_app_path(absolute_path, current_script_folder)
            assert result == expected_result

    @pytest.mark.parametrize(
        "absolute_path,current_script_folder",
        [
            # No etc\\apps in path - Windows
            (
                "C:\\Users\\user\\myproject\\lib\\mymodule.py",
                "lib"
            ),
            # etc\\apps exists but script folder doesn't exist after it - Windows
            (
                "C:\\Program Files\\Splunk\\etc\\apps\\my_app\\default\\app.conf",
                "lib"
            ),
            # Script folder exists but not after etc\\apps - Windows
            (
                "C:\\Users\\user\\lib\\myproject\\etc\\apps\\config",
                "lib"
            ),
            # Empty path - Windows
            (
                "",
                "lib"
            ),
        ],
    )
    def test_get_app_path_windows_returns_none(self, absolute_path, current_script_folder):
        """Test cases where _get_app_path should return None with Windows paths."""
        with patch('os.path.join') as mock_join:
            # Mock os.path.join to return Windows-style paths
            mock_join.return_value = "\\etc\\apps"
            
            result = core_lib_handler._get_app_path(absolute_path, current_script_folder)
            assert result is None

    def test_get_app_path_windows_default_current_script_folder(self):
        """Test that _get_app_path uses 'lib' as default current_script_folder on Windows."""
        with patch('os.path.join') as mock_join:
            # Mock os.path.join to return Windows-style paths
            mock_join.return_value = "\\etc\\apps"
            
            absolute_path = "C:\\Program Files\\Splunk\\etc\\apps\\my_app\\lib\\mymodule.py"
            
            # Call without current_script_folder parameter
            result = core_lib_handler._get_app_path(absolute_path)
            expected = "C:\\Program Files\\Splunk\\etc\\apps\\my_app"
            
            assert result == expected

    def test_get_app_path_windows_case_sensitivity(self):
        """Test that _get_app_path is case sensitive on Windows."""
        with patch('os.path.join') as mock_join:
            # Mock os.path.join to return Windows-style paths
            mock_join.return_value = "\\etc\\apps"
            
            # This should work (lowercase)
            path_lower = "C:\\Program Files\\Splunk\\etc\\apps\\my_app\\lib\\mymodule.py"
            result_lower = core_lib_handler._get_app_path(path_lower, "lib")
            assert result_lower == "C:\\Program Files\\Splunk\\etc\\apps\\my_app"
            
            # This should not work (uppercase LIB)
            path_upper = "C:\\Program Files\\Splunk\\etc\\apps\\my_app\\LIB\\mymodule.py"
            result_upper = core_lib_handler._get_app_path(path_upper, "lib")
            assert result_upper is None

    def test_get_app_path_windows_multiple_script_folders(self):
        """Test _get_app_path when script folder appears multiple times on Windows."""
        with patch('os.path.join') as mock_join:
            # Mock os.path.join to return Windows-style paths
            mock_join.return_value = "\\etc\\apps"
            
            # lib appears twice, should use the one after etc\\apps
            absolute_path = "C:\\lib\\backup\\C:\\Program Files\\Splunk\\etc\\apps\\my_app\\lib\\mymodule.py"
            result = core_lib_handler._get_app_path(absolute_path, "lib")
            expected = "C:\\lib\\backup\\C:\\Program Files\\Splunk\\etc\\apps\\my_app"
            assert result == expected

    def test_get_app_path_windows_relative_path(self):
        """Test _get_app_path with relative path elements on Windows."""
        with patch('os.path.join') as mock_join:
            # Mock os.path.join to return Windows-style paths
            mock_join.return_value = "\\etc\\apps"
            
            absolute_path = "C:\\Program Files\\Splunk\\etc\\apps\\my_app\\..\\my_app\\lib\\mymodule.py"
            result = core_lib_handler._get_app_path(absolute_path, "lib")
            # Should still find the pattern despite .. in path
            assert "\\my_app" in result
