"""MetaFunction Application Package."""

__version__ = "2.0.0"
__author__ = "Sanjeeva Dodlapati"
__email__ = "sdodl001@odu.edu"

# Export main factory function
from .main import create_app

__all__ = ['create_app']
