#!/usr/bin/env python
"""
Defines the regular file class used by the ext2 module.
"""
__license__ = "BSD"
__copyright__ = "Copyright 2013, Michael R. Falcone"


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
    assert (self._inode.mode & 0x8000) != 0, "Inode does not point to a regular file."


#  def read(self):
#    """If the file object is a regular file, reads the next chunk of bytes as
#    a byte array and updates the file pointer. Returns an empty array if
#    the file pointer is at the end of the file."""
#
#    raise InvalidFileTypeError()
#
#    if self._filePointer >= self.size:
#      return []
#
#    chunkBlockId = self.__lookupBlockId(self._filePointer / self._disk.blockSize)
#
#    chunk = self._disk._readBlock(chunkBlockId)[(self._filePointer % self._disk.blockSize):]
#    self._filePointer += len(chunk)
#    if self._filePointer > self.size:
#      chunk = chunk[:(self.size % self._disk.blockSize)]
#
#    return chunk