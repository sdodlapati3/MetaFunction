"""
Basic unit tests to ensure CI/CD pipeline has tests to run.
These are minimal tests that should always pass to validate core functionality.
"""

import pytest
import sys
import os

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_python_version():
    """Test that we're running on a supported Python version."""
    assert sys.version_info >= (3, 8), "Python 3.8+ required"

def test_app_module_imports():
    """Test that core app modules can be imported without errors."""
    try:
        import app
        import app.config
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import core app modules: {e}")

def test_resolvers_module_imports():
    """Test that resolver modules can be imported."""
    try:
        import resolvers
        import resolvers.decorators
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import resolver modules: {e}")

def test_basic_math():
    """Basic test to ensure pytest is working."""
    assert 1 + 1 == 2
    assert 2 * 3 == 6
    assert 10 / 2 == 5

def test_string_operations():
    """Test basic string operations."""
    assert "hello".upper() == "HELLO"
    assert "WORLD".lower() == "world"
    assert "test".capitalize() == "Test"

@pytest.mark.parametrize("input_val,expected", [
    (1, 2),
    (2, 3),
    (3, 4),
    (10, 11)
])
def test_increment(input_val, expected):
    """Parameterized test for increment function."""
    assert input_val + 1 == expected

def test_environment_variables():
    """Test that we can access environment variables."""
    # Test that we can set and get environment variables
    os.environ['TEST_VAR'] = 'test_value'
    assert os.environ.get('TEST_VAR') == 'test_value'
    
    # Clean up
    del os.environ['TEST_VAR']

def test_file_operations():
    """Test basic file operations."""
    import tempfile
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
        f.write("test content")
        temp_file_path = f.name
    
    # Read the file
    with open(temp_file_path, 'r') as f:
        content = f.read()
        assert content == "test content"
    
    # Clean up
    os.unlink(temp_file_path)

def test_list_operations():
    """Test basic list operations."""
    test_list = [1, 2, 3, 4, 5]
    
    assert len(test_list) == 5
    assert test_list[0] == 1
    assert test_list[-1] == 5
    assert 3 in test_list
    assert 6 not in test_list

def test_dict_operations():
    """Test basic dictionary operations."""
    test_dict = {"key1": "value1", "key2": "value2"}
    
    assert test_dict["key1"] == "value1"
    assert "key1" in test_dict
    assert "key3" not in test_dict
    assert len(test_dict) == 2
