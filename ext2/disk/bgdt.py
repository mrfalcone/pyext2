#!/usr/bin/env python
"""
Defines internal classes for the block group descriptor table used by the ext2 module.
"""
__license__ = "BSD"
__copyright__ = "Copyright 2013, Michael R. Falcone"


from struct import unpack_from


class _BGDTEntry(object):
  """Models an entry in the block group descriptor table. For internal use only."""
  _saveCopies = True


  # READ-ONLY PROPERTIES -------------------------------------

  @property
  def blockBitmapLocation(self):
    """Gets the block id of the block bitmap for this block group."""
    return self._blockBitmapBid


  @property
  def inodeBitmapLocation(self):
    """Gets the block id of the inode bitmap for this block group."""
    return self._inodeBitmapBid

  @property
  def inodeTableLocation(self):
    """Gets the block id of the inode table for this block group."""
    return self._inodeTableBid


  # WRITABLE PROPERTIES -------------------------------------

  @property
  def numFreeBlocks(self):
    """Gets the number of free blocks."""
    return self._numFreeBlocks
  @numFreeBlocks.setter
  def numFreeBlocks(self, value):
    """Sets the number of free blocks."""
    self._numFreeBlocks = value
    # TODO write to image


  @property
  def numFreeInodes(self):
    """Gets the number of free inodes."""
    return self._numFreeInodes
  @numFreeInodes.setter
  def numFreeInodes(self, value):
    """Sets the number of free inodes."""
    self._numFreeInodes = value
    # TODO write to image


  @property
  def numInodesAsDirs(self):
    """Gets the number of inodes used as directories."""
    return self._numInodesAsDirs
  @numInodesAsDirs.setter
  def numInodesAsDirs(self, value):
    """Sets the number of inodes used as directories."""
    self._numInodesAsDirs = value
    # TODO write to image
    
  
  def __init__(self, startPos, imageFile, superblock, fields):
    """Creates a new BGDT entry from the given fields."""
    self._superblock = superblock
    self._imageFile = imageFile
    self._startPos = startPos
    self._blockBitmapBid = fields[0]
    self._inodeBitmapBid = fields[1]
    self._inodeTableBid = fields[2]
    self._numFreeBlocks = fields[3]
    self._numFreeInodes = fields[4]
    self._numInodesAsDirs = fields[5]




class _BGDT(object):
  """Models the block group descriptor table for an Ext2 filesystem, storing information about
  each block group. For internal use only."""

  @property
  def entries(self):
    """Gets the list of BGDT entries. Indexes are block group ids."""
    return self._entries


  @classmethod
  def new(cls, groupId, superblock, imageFile):
    """Creates a new BGDT at the specified group number and returns the new object."""
    # TODO implement creation
    return None


  @classmethod
  def read(cls, groupId, superblock, imageFile):
    """Reads a BDGT at the specified group number and returns the new object."""
    groupStart = groupId * superblock.numBlocksPerGroup * superblock.blockSize
    startPos = groupStart + (superblock.blockSize * (superblock.firstDataBlockId + 1))
    tableSize = superblock.numBlockGroups * 32
    imageFile.seek(startPos)
    bgdtBytes = imageFile.read(tableSize)
    if len(bgdtBytes) < tableSize:
      raise Exception("Invalid block group descriptor table.")
    return cls(bgdtBytes, superblock, imageFile)
  
  
  def __init__(self, bgdtBytes, superblock, imageFile):
    """Constructs a new BGDT from the given byte array."""
    self._entries = []
    for i in range(superblock.numBlockGroups):
      startPos = i * 32
      fields = unpack_from("<3I3H", bgdtBytes, startPos)
      self._entries.append(_BGDTEntry(startPos, imageFile, superblock, fields))


