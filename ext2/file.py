#!/usr/bin/env python
"""
Defines the file object used by the ext2 module.
"""
__license__ = "BSD"
__copyright__ = "Copyright 2013, Michael R. Falcone"


from time import localtime, strftime
from struct import unpack_from
from math import ceil
from .error import *


class Ext2File(object):
  """Represents a file or directory on the Ext2 filesystem."""

  @property
  def fsType(self):
    """Gets a string representing the filesystem type."""
    return self._disk.fsType

  @property
  def name(self):
    """Gets the name of this file on the filesystem."""
    return self._name

  @property
  def absolutePath(self):
    """Gets the absolute path to this file or directory, including the name if
    it is a file or symlink."""
    return self._path

  @property
  def inodeNum(self):
    """Gets the inode number of this file on the filesystem."""
    return self._inode.number

  @property
  def isValid(self):
    """Returns True if the inode of this file is in use, or False if it is not."""
    return self._inode.isUsed

  @property
  def isDir(self):
    """Gets whether the file object is a directory."""
    return (self._inode.mode & 0x4000) != 0

  @property
  def isRegular(self):
    """Gets whether the file object is a regular file."""
    return (self._inode.mode & 0x8000) != 0

  @property
  def isSymlink(self):
    """Gets whether the file object is a symbolic link."""
    return (self._inode.mode & 0xA000) != 0

  @property
  def modeStr(self):
    """Gets a string representing the file object's mode."""
    return "".join(self._mode)

  @property
  def numLinks(self):
    """Gets the number of hard links to this file object."""
    return self._inode.numLinks

  @property
  def uid(self):
    """Gets the uid of the file owner."""
    return self._inode.uid

  @property
  def gid(self):
    """Gets the gid of the file owner."""
    return self._inode.gid

  @property
  def size(self):
    """Gets the size of the file in bytes, or 0 if it is not a regular file."""
    if self.isRegular:
      return self._inode.size
    return 0

  @property
  def numBlocks(self):
    """Gets the number of data blocks used by the file on the filesystem."""
    return self._numBlocks

  @property
  def timeCreated(self):
    """Gets the time and date the file was last created as a string."""
    return strftime("%b %d %I:%M %Y", localtime(self._inode.timeCreated))

  @property
  def timeAccessed(self):
    """Gets the time and date the file was last accessed as a string."""
    return strftime("%b %d %I:%M %Y", localtime(self._inode.timeAccessed))

  @property
  def timeModified(self):
    """Gets the time and date the file was last modified as a string."""
    return strftime("%b %d %I:%M %Y", localtime(self._inode.timeModified))

  @property
  def parentDir(self):
    """Gets this file object's parent directory. The root directory returns itself."""
    return self._parentDir


  def __init__(self, name, parentDir, inodeNum, disk):
    """Constructs a new file object from the specified inode number on the
    specified disk."""
    self._name = name
    self._inode = disk._readInode(inodeNum)
    self._disk = disk
    self._numBlocks = int(ceil(float(self._inode.size) / self._disk.blockSize))
    self.resetFilePointer()

    if parentDir is None:
      self._parentDir = self
    elif self._name == "..":
      self._parentDir = parentDir.parentDir
    else:
      self._parentDir = parentDir
    if not self._parentDir.isDir:
      raise Exception("Invalid parent directory.")


    absPath = []
    if not (self._name == "." or self._name == ".."):
      absPath.append(self._name)
    upParent = self._parentDir
    while not upParent.name == "":
      if upParent.name == ".":
        upParent = upParent.parentDir
      elif upParent.name == "..":
        upParent = upParent.parentDir.parentDir
      else:
        absPath.insert(0, upParent.name)
        upParent = upParent.parentDir
    self._path = "/{0}".format("/".join(absPath))

    self._mode = list("----------")
    if self.isDir:
      self._mode[0] = "d"
    if (self._inode.mode & 0x0100) != 0:
      self._mode[1] = "r"
    if (self._inode.mode & 0x0080) != 0:
      self._mode[2] = "w"
    if (self._inode.mode & 0x0040) != 0:
      self._mode[3] = "x"
    if (self._inode.mode & 0x0020) != 0:
      self._mode[4] = "r"
    if (self._inode.mode & 0x0010) != 0:
      self._mode[5] = "w"
    if (self._inode.mode & 0x0008) != 0:
      self._mode[6] = "x"
    if (self._inode.mode & 0x0004) != 0:
      self._mode[7] = "r"
    if (self._inode.mode & 0x0002) != 0:
      self._mode[8] = "w"
    if (self._inode.mode & 0x0001) != 0:
      self._mode[9] = "x"

    self._numIdsPerBlock = self._disk.blockSize / 4
    self._numDirectBlocks = 12
    self._numIndirectBlocks = self._numDirectBlocks + self._numIdsPerBlock
    self._numDoublyIndirectBlocks = self._numIndirectBlocks + self._numIdsPerBlock ** 2
    self._numTreblyIndirectBlocks = self._numDoublyIndirectBlocks + self._numIdsPerBlock ** 3


  def __str__(self):
    """Gets a string representation of this file object."""
    return "{0},{1},{2},{3},{4},{5},{6},{7},{8},{9}".format(self.inodeNum,
      self.modeStr, self.numLinks, self.uid, self.gid, self.size, self.timeCreated,
      self.timeAccessed, self.timeModified, self.name)


  def listContents(self):
    """Gets directory contents if this file object is a directory."""
    if not self.isDir:
      raise InvalidFileTypeError()

    contents = []
    for i in range(self.numBlocks):
      blockId = self.__lookupBlockId(i)
      if blockId == 0:
        break
      blockBytes = self._disk._readBlock(blockId)

      offset = 0
      while offset < self._disk.blockSize:
        fields = unpack_from("<IHB", blockBytes, offset)
        if fields[0] == 0:
          break
        name = unpack_from("<{0}s".format(fields[2]), blockBytes, offset + 8)[0]
        contents.append(Ext2File(name, self, fields[0], self._disk))
        offset += fields[1]

    return contents


  def resetFilePointer(self):
    """Resets the file pointer used for reading and writing bytes from/to the file."""
    self._filePointer = 0


  def read(self):
    """If the file object is a regular file, reads the next chunk of bytes as
    a byte array and updates the file pointer. Returns an empty array if
    the file pointer is at the end of the file."""
    if not self.isRegular:
      raise InvalidFileTypeError()
    if self._filePointer >= self.size:
      return []

    chunkBlockId = self.__lookupBlockId(self._filePointer / self._disk.blockSize)

    chunk = self._disk._readBlock(chunkBlockId)[(self._filePointer % self._disk.blockSize):]
    self._filePointer += len(chunk)
    if self._filePointer > self.size:
      chunk = chunk[:(self.size % self._disk.blockSize)]

    return chunk


  def _getUsedBlocks(self):
    """Returns a list of ALL block ids in use by the file object, including data
    and indirect blocks."""
    blocks = []
    for bid in self._inode.blocks:
      if bid != 0:
        blocks.append(bid)
      else:
        break

    # get indirect blocks
    if self._inode.blocks[12] != 0:
      for bid in self.__getBidListAtBid(self._inode.blocks[12]):
        if bid != 0:
          blocks.append(bid)
        else:
          return blocks

    # get doubly indirect blocks
    if self._inode.blocks[13] != 0:
      for indirectBid in self.__getBidListAtBid(self._inode.blocks[13]):
        if indirectBid != 0:
          blocks.append(indirectBid)
          for bid in self.__getBidListAtBid(indirectBid):
            if bid != 0:
              blocks.append(bid)
            else:
              return blocks
        else:
          return blocks

    # get trebly indirect blocks
    if self._inode.blocks[14] != 0:
      for doublyIndirectBid in self.__getBidListAtBid(self._inode.blocks[14]):
        if doublyIndirectBid != 0:
          blocks.append(doublyIndirectBid)
          for indirectBid in self.__getBidListAtBid(doublyIndirectBid):
            if indirectBid != 0:
              blocks.append(indirectBid)
              for bid in self.__getBidListAtBid(indirectBid):
                if bid != 0:
                  blocks.append(bid)
                else:
                  return blocks
        else:
          return blocks

    return blocks


  def __getBidListAtBid(self, bid):
    bytes = self._disk._readBlock(bid)
    return unpack_from("<{0}I".format(self._numIdsPerBlock), bytes)


  def __lookupBlockId(self, index):
    """Looks up the block id corresponding to the block at the specified index,
    where the block index is the absolute block number within the file."""
    if index >= self.numBlocks:
      raise Exception("Block index out of range.")

    if index < self._numDirectBlocks:
      return self._inode.blocks[index]

    elif index < self._numIndirectBlocks:
      directList = self.__getBidListAtBid(self._inode.blocks[12])
      return directList[index - self._numDirectBlocks]

    elif index < self._numDoublyIndirectBlocks:
      indirectList = self.__getBidListAtBid(self._inode.blocks[13])
      index -= self._numIndirectBlocks # get index from start of doubly indirect list
      directList = self.__getBidListAtBid(indirectList[index / self._numIdsPerBlock])
      return directList[index % self._numIdsPerBlock]

    elif index < self._numTreblyIndirectBlocks:
      doublyIndirectList = self.__getBidListAtBid(self._inode.blocks[14])
      index -= self._numDoublyIndirectBlocks # get index from start of trebly indirect list
      indirectList = self.__getBidListAtBid(doublyIndirectList[index / (self._numIdsPerBlock ** 2)])
      index %= (self._numIdsPerBlock ** 2) # get index from start of indirect list
      directList = self.__getBidListAtBid(indirectList[index / self._numIdsPerBlock])
      return directList[index % self._numIdsPerBlock]

    raise Exception("Block not found.")

