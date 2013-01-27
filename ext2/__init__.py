#!/usr/bin/env python
"""
Module for interfacing with an Ext2 filesystem image.
"""
__license__ = "BSD"
__copyright__ = "Copyright 2013, Michael R. Falcone"

from .error import *
from .disk import Ext2Disk
from .file import Ext2File
__all__ = ["Ext2File", "Ext2Disk", "InvalidImageFormatError", "InvalidFileTypeError", "UnsupportedOperationError",
           "FileNotFoundError", "FileAlreadyExistsError"]
