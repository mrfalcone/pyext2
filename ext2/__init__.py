#!/usr/bin/env python
"""
Module for interfacing with an Ext2 filesystem image.
"""
__license__ = "BSD"
__copyright__ = "Copyright 2013, Michael R. Falcone"

from .disk import *
from .file import *
from .error import *
__all__ = ["Ext2File", "Ext2Disk", "InvalidImageFormatError", "InvalidFileTypeError", "UnsupportedOperationError",
           "FileNotFoundError", "FileAlreadyExistsError"]
