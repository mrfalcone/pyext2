#!/usr/bin/env python
"""
Defines classes and functions for directory object of the ext2 module.
"""
__license__ = "BSD"
__copyright__ = "Copyright 2013, Michael R. Falcone"


import re
from struct import pack, unpack_from
from ..error import *
from .file import Ext2File
from .symlink import Ext2Symlink
from .regularfile import Ext2RegularFile


def _openRootDirectory(disk):
  """Opens and returns the root directory of the specified disk."""
  return Ext2Directory._openEntry(None, disk)



class _EntryList(object):
  """Represents a doubly-liked directory list in the Ext2 filesystem. For internal use only."""
  
  def __init__(self, containingDir):
    """Constructs a new directory entry list for the specified directory."""
    self._containingDir = containingDir
    self._entries = []
    offset = 0
    prevEntry = None
    for i in range(containingDir.numBlocks):
      blockId = containingDir._inode.lookupBlockId(i)
      if blockId == 0:
        break
      blockBytes = containingDir._disk._readBlock(blockId)
      while offset < containingDir._disk.blockSize:
        entry = _Entry(i, blockId, offset, prevEntry, blockBytes[offset:], containingDir)
        if entry.inodeNum == 0:
          break
        prevEntry = entry
        offset += entry.size
        self._entries.append(entry)
  
  
  
  def __iter__(self):
    """Gets the iterator to this list."""
    self._itIndex = 0
    return self
  
  
  def next(self):
    """Gets the next entry in the linked list."""
    if self._itIndex == len(self._entries):
      raise StopIteration
    entry = self._entries[self._itIndex]
    self._itIndex += 1
    return entry
  
  
  def append(self, name, inodeNum):
    """Appends a new entry for the specified inode number at the end of the list, and returns
    the entry object."""
    
    nameLength = len(name)
    assert nameLength <= 255, "Name is too long."
    assert nameLength > 0, "Name is too short."

    lastEntry = self._entries[-1]

    entrySize = nameLength + 11 # 7 bytes for record base, 4 bytes for alignment
    entrySize -= entrySize % 4 # align to 4 bytes

    # if new entry doesn't fit on current block, allocate a new one
    if entrySize + lastEntry._offset + lastEntry._size < self._containingDir._disk.blockSize:
      entryBlockIndex = lastEntry._bindex
      entryBlockId = lastEntry._bid
      entryOffset = lastEntry._offset + lastEntry._size
    else:
      entryBlockId = self._containingDir._disk._allocateBlock(True)
      entryBlockIndex = self._containingDir._inode.assignNextBlockId(entryBlockId)
      self._containingDir._inode.size += self._containingDir._disk.blockSize
      entryOffset = 0
    
    byteString = pack("<IHB{0}s".format(nameLength), inodeNum, entrySize, nameLength, name)
    self._containingDir._disk._writeToBlock(entryBlockId, entryOffset, byteString)
    newEntry = _Entry(entryBlockIndex, entryBlockId, entryOffset, None, byteString, self._containingDir)
    newEntry.prevEntry = lastEntry
    lastEntry.nextEntry = newEntry
    return newEntry




class _Entry(object):
  """Represents a directory entry in a linked entry list on the Ext2 filesystem. For internal use only."""

  @property
  def size(self):
    """Gets the size of this entry in bytes."""
    return self._size

  @property
  def containingDir(self):
    """Gets the directory object that contains this entry."""
    return self._containingDir
  
  @property
  def name(self):
    """Gets the name of the file represented by this entry."""
    return self._name

  @property
  def inodeNum(self):
    """Gets the inode number of the file represented by this entry."""
    return self._inodeNum

  @property
  def prevEntry(self):
    """Gets the previous entry in the list."""
    return self._prevEntry
  @prevEntry.setter
  def prevEntry(self, value):
    """Sets the previous entry in the list."""
    self._prevEntry = value
  
  @property
  def nextEntry(self):
    """Gets the next entry in the list."""
    return self._nextEntry
  @nextEntry.setter
  def nextEntry(self, value):
    """Sets the next entry in the list."""
    if not value is None:
      if value._bindex == self._bindex:
        newSize = value._offset - self._offset
        assert newSize > 0, "Next entry not after previous entry."
      else:
        newSize = self._containingDir._disk.blockSize - self._offset + value._offset
      self.__writeData(4, pack("<H", newSize))
    self._nextEntry = value

  
  def __init__(self, blockIndex, blockId, blockOffset, prevEntry, byteString, containingDir):
    """Contructs a new entry in the linked list."""
    
    fields = unpack_from("<IHB", byteString)
    self._name = unpack_from("<{0}s".format(fields[2]), byteString, 8)[0]
    self._inodeNum = fields[0]
    self._size = fields[1]
    self._bindex = blockIndex
    self._bid = blockId
    self._offset = blockOffset
    self._containingDir = containingDir
    self._nextEntry = None
    self._prevEntry = prevEntry
    if not (self._inodeNum == 0 or self._prevEntry is None):
      self._prevEntry._nextEntry = self
  
  
  def __writeData(self, offset, byteString):
    """Writes the specified byte string to the offset within the entry."""
    self._containingDir._disk._writeToBlock(self._bid, self._offset + offset, byteString)

    




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
    self._entryList = _EntryList(self)



  @classmethod
  def _openEntry(cls, dirEntry, disk):
    """Opens and returns the file object described by the specified directory entry."""
    if dirEntry:
      inode = disk._readInode(dirEntry.inodeNum)
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
    for entry in self._entryList:
      yield Ext2Directory._openEntry(entry, self._disk)



  def getFileAt(self, relativePath):
    """Looks up and returns the file specified by the relative path from this directory. Raises a
    FileNotFoundError if the file cannot be found."""
    
    pathParts = re.compile("/+").split(relativePath)
    if len(pathParts) > 1 and pathParts[0] == "":
      del pathParts[0]
    if len(pathParts) > 1 and pathParts[-1] == "":
      del pathParts[-1]
    if len(pathParts) == 0:
      raise FileNotFoundError()
    
    curFile = self
    for curPart in pathParts:
      if curFile.isDir:
        for entry in curFile._entryList:
          if entry.name == curPart:
            curFile = Ext2Directory._openEntry(entry, self._disk)
            break
    
    if pathParts[-1] != "" and pathParts[-1] != curFile.name:
      raise FileNotFoundError()
    
    return curFile


  def makeDirectory(self, name, uid = None, gid = None):
    """Creates a new directory in this directory and returns the new file object."""
    
    if uid is None:
      uid = self.uid
    if gid is None:
      gid = self.gid
    
    mode = 0
    mode |= 0x4000 # set directory
    mode |= 0x0100 # user read
    mode |= 0x0080 # user write
    mode |= 0x0040 # user execute
    mode |= 0x0020 # group read
    mode |= 0x0008 # group execute
    mode |= 0x0004 # others read
    mode |= 0x0001 # others execute
    
    entry = self.__makeNewEntry(name, mode, uid, gid)
    entry._append(".", entry.inodeNum)
    entry._append("..", entry.containingDir.parentDir.inodeNum)
    return Ext2Directory._openEntry(entry, self._disk)



  def makeRegularFile(self, name):
    """Creates a new regular file in this directory and returns the new file object."""
    pass



  def makeLink(self, name, linkedFile, isSymbolic):
    """Creates a new link in this directory to the given file object and returns the new file object."""
    pass




  # PRIVATE METHODS ------------------------------------------------

  def __makeNewEntry(self, name, mode, uid, gid):
    """Creates a new entry with the given parameters and returns the new object."""

    if name.find("/") >= 0:
      parent = self.getFileAt(name[:name.rindex("/")])
      return parent.__makeNewEntry(name[name.rindex("/")+1:], mode, uid, gid)
    
    if len(name.strip()) == 0:
      raise Exception("No name specified.")

    # make sure destination does not already exist
    for entry in self._entryList:
      if entry.name == name:
        raise Exception("An entry with that name already exists.")
    
    inode = self._disk._allocateInode(mode, uid, gid)
    bid = self._disk._allocateBlock(True)
    inode.assignNextBlockId(bid)
    inode.size += self._disk.blockSize
    
    entry = self._entryList.append(name, inode.number)
    inode.numLinks += 1
    
    return entry