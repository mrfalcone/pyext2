#!/usr/bin/env python
"""
Defines the internal inode class used by the ext2 module.
"""
__license__ = "BSD"
__copyright__ = "Copyright 2013, Michael R. Falcone"


from struct import pack, unpack, unpack_from
from time import time


class _Inode(object):
  """Models an inode on the Ext2 fileystem. For internal use only."""


  # READ-ONLY PROPERTIES -------------------------------------

  @property
  def number(self):
    """Gets the inode number of this inode."""
    return self._num

  @property
  def isUsed(self):
    """Returns True if the inode is marked as used, False otherwise."""
    return self._used

  @property
  def timeCreated(self):
    """Gets the time this inode was created."""
    return self._time_created

  @property
  def flags(self):
    """Gets the flags bitmap for this inode."""
    return self._flags

  @property
  def blocks(self):
    """Gets the list of block ids used by the inode."""
    return self._blocks




  # WRITABLE PROPERTIES -------------------------------------

  @property
  def mode(self):
    """Gets the mode bitmap."""
    return self._mode
  @mode.setter
  def mode(self, value):
    """Sets the mode bitmap."""
    self._mode = value
    self.__writeData(0, pack("<H", (self._mode & 0xFFFF)))
    if self._superblock.creatorOS == "HURD":
      self.__writeData(118, pack("<H", (self._mode >> 16)))

  @property
  def uid(self):
    """Gets the uid of the inode's owner."""
    return self._uid
  @uid.setter
  def uid(self, value):
    """Sets the uid of the inode's owner."""
    self._uid = value
    self.__writeData(2, pack("<H", (self._uid & 0xFFFF)))
    if self._superblock.creatorOS == "LINUX" or self._superblock.creatorOS == "HURD":
      self.__writeData(120, pack("<H", (self._uid >> 16)))

  @property
  def size(self):
    """Gets the size in bytes of the inode's file."""
    return self._size
  @size.setter
  def size(self, value):
    """Sets the size in bytes of the inode's file."""
    self._size = value
    self.__writeData(4, pack("<I", (self._size & 0xFFFFFFFF)))
    # if regular file on revision > 0, save upper 32 bits of size in dir ACL field
    if self._superblock.revisionMajor > 0 and (self._mode & 0x8000) != 0:
      self.__writeData(108, pack("<I", (self._size >> 32)))

  @property
  def timeAccessed(self):
    """Gets the time the inode was last accessed."""
    return self._time_accessed
  @timeAccessed.setter
  def timeAccessed(self, value):
    """Sets the time the inode was last accessed."""
    self._time_accessed = value
    self.__writeData(8, pack("<I", self._time_accessed))

  @property
  def timeModified(self):
    """Gets the time the inode was last modified."""
    return self._time_modified
  @timeModified.setter
  def timeModified(self, value):
    """Sets the time the inode was last modified."""
    self._time_modified = value
    self.__writeData(16, pack("<I", self._time_modified))

  @property
  def timeDeleted(self):
    """Gets the time the inode was deleted."""
    return self._time_deleted
  @timeDeleted.setter
  def timeDeleted(self, value):
    """Sets the time the inode was deleted."""
    self._time_deleted = value
    self.__writeData(20, pack("<I", self._time_deleted))

  @property
  def gid(self):
    """Gets the gid of the inode's owner."""
    return self._gid
  @gid.setter
  def gid(self, value):
    """Sets the gid of the inode's owner."""
    self._gid = value
    self.__writeData(24, pack("<H", (self._gid & 0xFFFF)))
    if self._superblock.creatorOS == "LINUX" or self._superblock.creatorOS == "HURD":
      self.__writeData(122, pack("<H", (self._gid >> 16)))

  @property
  def numLinks(self):
    """Gets the number of hard links to the inode."""
    return self._num_links
  @numLinks.setter
  def numLinks(self, value):
    """Sets the number of hard links to the inode."""
    self._num_links = value
    self.__writeData(26, pack("<h", self._num_links))






  # MAIN METHODS -------------------------------------

  @classmethod
  def new(cls, bgdt, superblock, imageFile, mode, uid, gid):
    """Allocates the first free inode and returns the new inode object."""
    bitmapStartPos = None
    bgroupNum = 0
    bgdtEntry = None
    bitmapSize = superblock.numInodesPerGroup / 8

    for bgroupNum, bgdtEntry in enumerate(bgdt.entries):
      if bgdtEntry.numFreeInodes > 0:
        bitmapStartPos = bgdtEntry.inodeBitmapLocation * superblock.blockSize
        break
    if bitmapStartPos is None:
      raise Exception("No free inodes.")

    imageFile.seek(bitmapStartPos)
    bitmapBytes = imageFile.read(bitmapSize)
    if len(bitmapBytes) < bitmapSize:
      raise Exception("Invalid inode bitmap.")

    inodeNum = None
    bitmap = unpack("{0}B".format(bitmapSize), bitmapBytes)
    for byteIndex, byte in enumerate(bitmap):
      if byte != 255:
        for i in range(8):
          if (1 << i) & byte == 0:
            inodeNum = (bgroupNum * superblock.numInodesPerGroup) + (byteIndex * 8) + i + 1
            imageFile.seek(bitmapStartPos + byteIndex)
            # TODO imageFile.write(pack("B", byte | (1 << i)))
            break
    if inodeNum is None:
      raise Exception("No free inodes.")

    superblock.numFreeInodes -= 1
    bgdtEntry.numFreeInodes -= 1
    if (mode & 0x4000) != 0:
      bgdtEntry.numInodesAsDirs += 1


    if superblock.creatorOS == "LINUX":
      osdBytes = pack("<4x2H", (uid >> 16), (gid >> 16))
    elif superblock.creatorOS == "HURD":
      osdBytes = pack("<2x3H", (mode >> 16), (uid >> 16), (gid >> 16))
    else:
      osdBytes = pack("<12x")
      
    inodeBytes = pack("<2Hi4IH90x12s", (mode & 0xFFFF), (uid & 0xFFFF), 0, 0, int(time()), 0, 0,
      (gid & 0xFFFF), osdBytes)
    
    # write new inode bytes to disk image
    bgroupIndex = (inodeNum - 1) % superblock.numInodesPerGroup
    tableStartPos = bgdtEntry.inodeTableLocation * superblock.blockSize
    inodeStartPos = tableStartPos + (bgroupIndex * superblock.inodeSize)
    imageFile.seek(inodeStartPos)
    # TODO imageFile.write(inodeBytes)

    return cls(inodeStartPos, inodeBytes, True, inodeNum, superblock, imageFile)



  @classmethod
  def read(cls, inodeNum, bgdt, superblock, imageFile):
    """Reads the inode with the specified inode number and returns the new object."""

    bgroupNum = (inodeNum - 1) / superblock.numInodesPerGroup
    bgroupIndex = (inodeNum - 1) % superblock.numInodesPerGroup
    bgdtEntry = bgdt.entries[bgroupNum]

    bitmapStartPos = bgdtEntry.inodeBitmapLocation * superblock.blockSize
    bitmapByteIndex = bgroupIndex / 8
    
    tableStartPos = bgdtEntry.inodeTableLocation * superblock.blockSize
    inodeStartPos = tableStartPos + (bgroupIndex * superblock.inodeSize)

    imageFile.seek(bitmapStartPos + bitmapByteIndex)
    bitmapByte = unpack("B", imageFile.read(1))[0]
    imageFile.seek(inodeStartPos)
    inodeBytes = imageFile.read(superblock.inodeSize)
    if len(inodeBytes) < superblock.inodeSize:
      raise Exception("Invalid inode.")

    isUsed = (bitmapByte & (1 << (bgroupIndex % 8)) != 0)
    return cls(inodeStartPos, inodeBytes, isUsed, inodeNum, superblock, imageFile)




  def __init__(self, inodeStartPos, inodeBytes, isUsed, inodeNum, superblock, imageFile):
    """Constructs a new inode from the given byte array."""
    self._imageFile = imageFile
    self._superblock = superblock
    self._inodeStartPos = inodeStartPos
    
    if superblock.revisionMajor == 0:
      fields = unpack_from("<2Hi4IHh4xI4x15I", inodeBytes)
    else:
      fields = unpack_from("<2H5IHh4xI4x15I8xI", inodeBytes)

    osFields = []
    if superblock.creatorOS == "LINUX":
      osFields = unpack_from("<4x2H", inodeBytes, 116)
    elif superblock.creatorOS == "HURD":
      osFields = unpack_from("<2x3H", inodeBytes, 116)
      
    self._num = inodeNum
    self._used = isUsed
    self._mode = fields[0]
    self._uid = fields[1]
    self._size = fields[2]
    self._time_accessed = fields[3]
    self._time_created = fields[4]
    self._time_modified = fields[5]
    self._time_deleted = fields[6]
    self._gid = fields[7]
    self._num_links = fields[8]
    self._flags = fields[9]
    self._blocks = []
    for i in range(15):
      self._blocks.append(fields[10+i])
    if superblock.revisionMajor > 0:
      self._size |= (fields[25] << 32)
    if superblock.creatorOS == "LINUX":
      self._uid |= (osFields[0] << 16)
      self._gid |= (osFields[1] << 16)
    elif superblock.creatorOS == "HURD":
      self._mode |= (osFields[0] << 16)
      self._uid |= (osFields[1] << 16)
      self._gid |= (osFields[2] << 16)
  
  
  def __writeData(self, offset, byteString):
    """Writes the specified string of bytes at the specified offset (from the start of the inode bytes)
    on the disk image."""
    self._imageFile.seek(self._inodeStartPos + offset)
    # TODO imageFile.write(byteString)