#!/usr/bin/env python
"""
Defines the symbolic link class used by the ext2 module.
"""
__license__ = "BSD"
__copyright__ = "Copyright 2013, Michael R. Falcone"


from ..error import FilesystemError
from .file import Ext2File


class Ext2Symlink(Ext2File):
  """Represents a symbolic link to a file or directory on the Ext2 filesystem."""

  @property
  def isSymlink(self):
    """Gets whether the file object is a symbolic link."""
    return True
  
  def __init__(self, dirEntry, inode, fs):
    """Constructs a new symbolic link object from the specified directory entry."""
    super(Ext2Symlink, self).__init__(dirEntry, inode, fs)
    if (self._inode.mode & 0xA000) == 0:
      raise FilesystemError("Inode does not point to a symbolic link.")
