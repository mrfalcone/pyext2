#!/usr/bin/env python
"""
Defines classes and functions for directory object of the ext2 module.
"""
__license__ = "BSD"
__copyright__ = "Copyright 2013, Michael R. Falcone"


import re
from struct import unpack_from
from ..error import *
from .file import Ext2File
from .symlink import Ext2Symlink
from .regularfile import Ext2RegularFile


def _openRootDirectory(disk):
  """Opens and returns the root directory of the specified disk."""
  return Ext2Directory._openEntry(None, disk)




class _DirectoryEntryList(object):
  """Represents a directory listing on a block in the Ext2 filesystem."""
  def __init__(self, blockBytes, parentDir):
    self._entry = _DirectoryEntry(0, blockBytes, None, parentDir)
  def __iter__(self):
    return self
  def next(self):
    """Gets the next entry in the linked list."""
    if self._entry:
      if self._entry.inodeNumber == 0:
        raise StopIteration
      entry = self._entry
      self._entry = self._entry.nextEntry
      return entry
    raise StopIteration




class _DirectoryEntry(object):
  """Represents a directory entry in a linked entry list on the Ext2 filesystem."""

  @property
  def name(self):
    """Gets the name of the file represented by this entry."""
    return self._name

  @property
  def inodeNumber(self):
    """Gets the inode number of the file represented by this entry."""
    return self._inodeNum

  @property
  def prevEntry(self):
    """Gets the previous entry in the list."""
    return self._prevEntry
  
  @property
  def nextEntry(self):
    """Gets the next entry in the list."""
    return self._nextEntry

  @property
  def parentDir(self):
    """Gets the directory to which this entry belongs."""
    return self._parentDir
  
  def __init__(self, entryOffset, blockBytes, prevEntry, parentDir):
    """Contructs a new entry in the linked list."""
    self._parentDir = parentDir
    self._prevEntry = prevEntry
    self._blockBytes = blockBytes
    self._entryOffset = entryOffset
    fields = unpack_from("<IHB", blockBytes, entryOffset)
    self._inodeNum = fields[0]
    self._entrySize = fields[1]
    self._name = unpack_from("<{0}s".format(fields[2]), blockBytes, entryOffset + 8)[0]
    if self._inodeNum == 0:
      self._nextEntry = None
    elif self._entryOffset + self._entrySize + 7 > len(self._blockBytes):
      self._nextEntry = None
    else:
      self._nextEntry = _DirectoryEntry(self._entryOffset + self._entrySize, self._blockBytes, self, self._parentDir)





class Ext2Directory(Ext2File):
  """Represents a directory on the Ext2 filesystem."""

  @property
  def isDir(self):
    """Gets whether the file object is a directory."""
    return True


  def __init__(self, dirEntry, inode, disk):
    """Constructs a new directory object from the specified directory entry."""
    super(Ext2Directory, self).__init__(dirEntry, inode, disk)
    assert (self._inode.mode & 0x4000) != 0, "Inode does not point to a directory."



  @classmethod
  def _openEntry(cls, dirEntry, disk):
    """Opens and returns the file object described by the specified directory entry."""
    if dirEntry:
      inode = disk._readInode(dirEntry.inodeNumber)
    else:
      inode = disk._readInode(2)

    if (inode.mode & 0x4000) != 0:
      return Ext2Directory(dirEntry, inode, disk)
    if (inode.mode & 0x8000) != 0:
      return Ext2RegularFile(dirEntry, inode, disk)
    if (inode.mode & 0xA000) != 0:
      return Ext2Symlink(dirEntry, inode, disk)

    return Ext2File(dirEntry, inode, disk)



  # PUBLIC METHODS ------------------------------------------------

  def files(self):
    """Generates a list of files in the directory."""
    for entry in self.__entries():
      yield Ext2Directory._openEntry(entry, self._disk)



  def getFileAt(self, relativePath):
    """Looks up and returns the file specified by the relative path from this directory. Raises a
    FileNotFoundError if the file object cannot be found."""
    
    pathParts = re.compile("/+").split(relativePath)
    if len(pathParts) > 1 and pathParts[0] == "":
      del pathParts[0]
    if len(pathParts) > 1 and pathParts[-1] == "":
      del pathParts[-1]
    if len(pathParts) == 0:
      raise FileNotFoundError()
    
    curFile = self
    for curPart in pathParts:
      for entry in curFile.__entries():
        if entry.name == curPart:
          curFile = Ext2Directory._openEntry(entry, self._disk)
          break
    
    if pathParts[-1] != "" and pathParts[-1] != curFile.name:
      raise FileNotFoundError()
    
    return curFile


  def makeDirectory(self, absolutePath):
    """Creates a new directory in this directory and returns the new file object."""

    # make sure destination does not already exist
    destExists = True
    try:
      self.getFile(absolutePath)
    except FileNotFoundError:
      destExists = False
    if destExists:
      raise FileAlreadyExistsError()

    # find parent directory and add an entry for the file
    pathParts = re.compile("/+").split(absolutePath)
    if len(pathParts) == 0:
      raise FileNotFoundError()
    if not pathParts[0] == "":
      raise FileNotFoundError()
    if len(pathParts) > 1 and pathParts[-1] == "":
      del pathParts[-1]

    fileName = pathParts[-1]
    parentPath = "/{0}".format("/".join(pathParts[:-1]))
    parentDir = self.getFile(parentPath)


    mode = 0
    mode |= 0x4000 # set directory
    mode |= 0x0100 # user read
    mode |= 0x0080 # user write
    mode |= 0x0040 # user execute
    mode |= 0x0020 # group read
    mode |= 0x0008 # group execute
    mode |= 0x0004 # others read
    mode |= 0x0001 # others execute
    inode = self._allocateInode(mode, 1000, 1000)
    # TODO use inode
    print inode



  def makeRegularFile(self, absolutePath):
    """Creates a new regular file in this directory and returns the new file object."""
    pass



  def makeLink(self, absolutePath, linkedFile, isSymbolic):
    """Creates a new link in this directory to the given file object and returns the new file object."""
    pass




  # PRIVATE METHODS ------------------------------------------------

  def __entries(self):
    """Generates the next entry in the directory."""
    for i in range(self.numBlocks):
      blockId = self._lookupBlockId(i)
      if blockId == 0:
        break
      for entry in _DirectoryEntryList(self._disk._readBlock(blockId), self):
        yield entry
  

