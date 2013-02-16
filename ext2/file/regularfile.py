#!/usr/bin/env python
"""
Defines the regular file class used by the ext2 module.
"""
__license__ = "BSD"
__copyright__ = "Copyright 2013, Michael R. Falcone"


from ..error import FilesystemError
from .file import Ext2File


class Ext2RegularFile(Ext2File):
  """Represents a regular file on the Ext2 filesystem."""

  @property
  def isRegular(self):
    """Gets whether the file object is a regular file."""
    return True
  
  def __init__(self, dirEntry, inode, disk):
    """Constructs a new regular file object from the specified directory entry."""
    super(Ext2RegularFile, self).__init__(dirEntry, inode, disk)
    if (self._inode.mode & 0x8000) == 0:
      raise FilesystemError("Inode does not point to a regular file.")


  def blocks(self):
    """Generates the next block in the file."""
    for i in range(self.numBlocks):
      blockId = self._inode.lookupBlockId(i)
      if blockId == 0:
        break
      block = self._disk._readBlock(blockId)
      if (i+1) * self._disk.blockSize > self.size:
        block = block[:(self.size % self._disk.blockSize)]
      yield block
