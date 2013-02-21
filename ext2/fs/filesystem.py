#!/usr/bin/env python
"""
Defines the filesystem class used by the ext2 module.
"""
__license__ = "BSD"
__copyright__ = "Copyright 2013, Michael R. Falcone"


import inspect
from collections import deque
from struct import pack, unpack
from time import time
from ..file.directory import _openRootDirectory
from ..error import FilesystemError
from .superblock import _Superblock
from .bgdt import _BGDT
from .inode import _Inode
from .device import _DeviceFromFile


class InformationReport(object):
  """Structure used to return information about the filesystem."""
  pass


class Ext2Filesystem(object):
  """Models a filesystem image file formatted to Ext2."""
  
  
  @property
  def fsType(self):
    """Gets a string representing the filesystem type. Always EXT2."""
    return "EXT2"
  
  @property
  def revision(self):
    """Gets the filesystem revision string formatted as MAJOR.MINOR."""
    if not self.isValid:
      raise FilesystemError("Filesystem is not valid.")
    return "{0}.{1}".format(self._superblock.revisionMajor, self._superblock.revisionMinor)
  
  @property
  def totalSpace(self):
    """Gets the total filesystem size in bytes."""
    if not self.isValid:
      raise FilesystemError("Filesystem is not valid.")
    return self._superblock.blockSize * self._superblock.numBlocks
  
  @property
  def freeSpace(self):
    """Gets the number of free bytes."""
    if not self.isValid:
      raise FilesystemError("Filesystem is not valid.")
    return self._superblock.blockSize * self._superblock.numFreeBlocks
  
  @property
  def usedSpace(self):
    """Gets the number of used bytes."""
    if not self.isValid:
      raise FilesystemError("Filesystem is not valid.")
    return self.totalSpace - self.freeSpace
  
  @property
  def blockSize(self):
    """Gets the block size in bytes."""
    if not self.isValid:
      raise FilesystemError("Filesystem is not valid.")
    return self._superblock.blockSize
  
  @property
  def numBlockGroups(self):
    """Gets the number of block groups."""
    if not self.isValid:
      raise FilesystemError("Filesystem is not valid.")
    return len(self._bgdt.entries)
  
  @property
  def numInodes(self):
    """Gets the total number of inodes."""
    if not self.isValid:
      raise FilesystemError("Filesystem is not valid.")
    return self._superblock.numInodes
  
  @property
  def rootDir(self):
    """Gets the file object representing the root directory."""
    if not self.isValid:
      raise FilesystemError("Filesystem is not valid.")
    return self._rootDir

  @property
  def isValid(self):
    """Gets whether the filesystem is valid and mounted."""
    return self._isValid
  
  
  
  @classmethod
  def fromImageFile(cls, imageFilename):
    """Creates a new Ext2 filesystem from the specified image file."""
    return cls(_DeviceFromFile(imageFilename))
  
  def __init__(self, device):
    """Constructs a new Ext2 filesystem from the specified device object."""
    self._device = device
    self._isValid = False
  
  def __del__(self):
    """Destructor that unmounts the filesystem if it has not been unmounted."""
    if self._device.isMounted:
      self.unmount()
  
  def __enter__ (self):
    """Mounts the filesystem and returns the root directory."""
    self.mount()
    return self.rootDir

  def __exit__ (self, t, value, tb):
    """Unmounts the filesystem and re-raises any exception that occurred."""
    self.unmount()
  
  
  
  def mount(self):
    """Mounts the Ext2 filesystem for reading and writing and reads the root directory. Raises an
    error if the root directory cannot be read."""
    self._device.mount()
    try:
      self._superblock = _Superblock.read(1024, self._device)
      self._bgdt = _BGDT.read(0, self._superblock, self._device)
      self._isValid = True
      self._rootDir = _openRootDirectory(self)
    except:
      if self._device.isMounted:
        self._device.unmount()
      self._isValid = False
      raise FilesystemError("Root directory could not be read.")
  
  
  
  def unmount(self):
    """Unmounts the Ext2 filesystem so that reading and writing may no longer occur, and closes
    access to the device."""
    if self._device.isMounted:
      self._device.unmount()
    self._isValid = False
  
  
  
  
  def scanBlockGroups(self):
    """Scans all block groups and returns an information report about them."""
    assert self.isValid, "Filesystem is not valid."
    
    report = InformationReport()
    
    # count files and directories
    report.numRegFiles = 0
    report.numSymlinks = 0
    report.numDirs = 1 # initialize with root directory
    q = deque([])
    q.append(self.rootDir)
    while len(q) > 0:
      d = q.popleft()
      for f in d.files():
        if f.name == "." or f.name == "..":
          continue
        if f.isDir:
          report.numDirs += 1
          q.append(f)
        elif f.isRegular:
          report.numRegFiles += 1
        elif f.isSymlink:
          report.numSymlinks += 1
    
    # report block group information
    report.groupReports = []
    for i,entry in enumerate(self._bgdt.entries):
      groupReport = InformationReport()
      groupReport.numFreeBlocks = entry.numFreeBlocks
      groupReport.numFreeInodes = entry.numFreeInodes
      report.groupReports.append(groupReport)
    
    return report
  
  
  
  
  def checkIntegrity(self):
    """Evaluates the integrity of the filesystem and returns an information report."""
    assert self.isValid, "Filesystem is not valid."
    
    report = InformationReport()
    
    # basic integrity checks
    report.hasMagicNumber = self._superblock.isValidExt2
    report.numSuperblockCopies = len(self._superblock.copyLocations)
    report.copyLocations = list(self._superblock.copyLocations)
    report.messages = []
    
    
    # check consistency across superblock/group table copies
    sbMembers = dict(inspect.getmembers(self._superblock))
    bgtMembersEntries = map(dict, map(inspect.getmembers, self._bgdt.entries))
    for groupId in self._superblock.copyLocations:
      if groupId == 0:
        continue
      
      # evaluate superblock copy consistency
      try:
        startPos = 1024 + groupId * self._superblock.numBlocksPerGroup * self._superblock.blockSize
        sbCopy = _Superblock.read(startPos, self._device)
        sbCopyMembers = dict(inspect.getmembers(sbCopy))
      except:
        report.messages.append("Superblock at block group {0} could not be read.".format(groupId))
        continue
      for m in sbMembers:
        if m.startswith("_"):
          continue
        if not m in sbCopyMembers:
          report.messages.append("Superblock at block group {0} has missing field '{1}'.".format(groupId, m))
        elif not sbCopyMembers[m] == sbMembers[m]:
          report.messages.append("Superblock at block group {0} has inconsistent field '{1}' with value '{2}' (primary value is '{3}').".format(groupId, m, sbCopyMembers[m], sbMembers[m]))
      
      # evaluate block group descriptor table consistency
      try:
        bgtCopy = _BGDT.read(groupId, self._superblock, self._device)
        bgtCopyMembersEntries = map(dict, map(inspect.getmembers, bgtCopy.entries))
      except:
        report.messages.append("Block group descriptor table at block group {0} could not be read.".format(groupId))
        continue
      if len(bgtCopyMembersEntries) != len(bgtMembersEntries):
        report.messages.append("Block group descriptor table at block group {0} has {1} entries while primary has {2}.".format(groupId, len(bgtCopyMembersEntries), len(bgtMembersEntries)))
        continue
      for entryNum in range(len(bgtMembersEntries)):
        bgtPrimaryEntryMembers = bgtMembersEntries[entryNum]
        bgtCopyEntryMembers = bgtCopyMembersEntries[entryNum]
        for m in bgtPrimaryEntryMembers:
          if m.startswith("_"):
            continue
          if not m in bgtCopyEntryMembers:
            report.messages.append("Block group descriptor table entry {0} at block group {1} has missing field '{2}'.".format(entryNum, groupId, m))
          elif not bgtCopyEntryMembers[m] == bgtPrimaryEntryMembers[m]:
            report.messages.append("Block group descriptor table entry {0} at block group {1} has inconsistent field '{2}' with value '{3}' (primary value is '{4}').".format(entryNum, groupId, m, bgtCopyEntryMembers[m], bgtPrimaryEntryMembers[m]))
    
    
    # validate inode and block references
    inodes = self.__getUsedInodes()
    inodesReachable = dict(zip(inodes, [False] * len(inodes)))
    blocks = self.__getUsedBlocks()
    blocksAccessedBy = dict(zip(blocks, [None] * len(blocks)))
    
    q = deque([])
    q.append(self.rootDir)
    while len(q) > 0:
      d = q.popleft()
      for f in d.files():
        if f.name == "." or f.name == "..":
          continue
        if f.isDir:
          q.append(f)
        
        # check inode references
        if not (f.isValid and f.inodeNum in inodesReachable):
          report.messages.append("The filesystem contains an entry for {0} but its inode is not marked as used (inode number {1}).".format(f.absolutePath, f.inodeNum))
        else:
          inodesReachable[f.inodeNum] = True
        
        # check block references
        if not f.isSymlink or f.size > 60:
          for bid in f._inode.usedBlocks():
            if not bid in blocksAccessedBy:
              report.messages.append("The file {0} is referencing a block that is not marked as used by the filesystem (block id: {1})".format(f.absolutePath, bid))
            elif blocksAccessedBy[bid]:
              report.messages.append("Block id {0} is being referenced by both {1} and {2}.".format(bid, blocksAccessedBy[bid], f.absolutePath))
            else:
              blocksAccessedBy[bid] = f.absolutePath
    
    for inodeNum in inodesReachable:
      if not inodesReachable[inodeNum]:
        report.messages.append("Inode number {0} is marked as used but is not reachable from a directory entry.".format(inodeNum))
    
    return report
  
  
  
  def __getUsedInodes(self):
    """Returns a list of all used inode numbers, excluding those reserved by the
    filesystem."""
    used = []
    bitmaps = []
    for bgdtEntry in self._bgdt.entries:
      bitmapStartPos = bgdtEntry.inodeBitmapLocation * self._superblock.blockSize
      bitmapSize = self._superblock.numInodesPerGroup / 8
      bitmapBytes = self._device.read(bitmapStartPos, bitmapSize)
      if len(bitmapBytes) < bitmapSize:
        raise FilesystemError("Invalid inode bitmap.")
      bitmaps.append(unpack("{0}B".format(bitmapSize), bitmapBytes))
    
    for groupNum,bitmap in enumerate(bitmaps):
      for byteIndex, byte in enumerate(bitmap):
        if byte != 0:
          for i in range(8):
            if (1 << i) & byte != 0:
              inum = (groupNum * self._superblock.numInodesPerGroup) + (byteIndex * 8) + i + 1
              if inum >= self._superblock.firstInode:
                used.append(inum)
    
    return used
  
  
  
  def __getUsedBlocks(self):
    """Returns a list off all block ids currently in use by the filesystem."""
    used = []
    bitmaps = []
    for bgdtEntry in self._bgdt.entries:
      bitmapStartPos = bgdtEntry.blockBitmapLocation * self._superblock.blockSize
      bitmapSize = self._superblock.numBlocksPerGroup / 8
      bitmapBytes = self._device.read(bitmapStartPos, bitmapSize)
      if len(bitmapBytes) < bitmapSize:
        raise FilesystemError("Invalid block bitmap.")
      bitmaps.append(unpack("{0}B".format(bitmapSize), bitmapBytes))
        
    for groupNum,bitmap in enumerate(bitmaps):
      for byteIndex, byte in enumerate(bitmap):
        if byte != 0:
          for i in range(8):
            if (1 << i) & byte != 0:
              bid = (groupNum * self._superblock.numBlocksPerGroup) + (byteIndex * 8) + i + self._superblock.firstDataBlockId
              used.append(bid)
    
    return used
    
  
  
  
  def _readBlock(self, bid, offset = 0, count = None):
    """Reads from the block specified by the given block id and returns a string of bytes."""
    if not count:
      count = self._superblock.blockSize
    block = self._device.read(bid * self._superblock.blockSize + offset, count)
    if len(block) < count:
      raise FilesystemError("Invalid block.")
    return block



  def _freeBlock(self, bid):
    """Frees the block specified by the given block id."""
    groupNum = (bid - self._superblock.firstDataBlockId) / self._superblock.numBlocksPerGroup
    indexInGroup = (bid - self._superblock.firstDataBlockId) % self._superblock.numBlocksPerGroup
    byteIndex = indexInGroup / 8
    bitIndex = indexInGroup % 8

    bgdtEntry = self._bgdt.entries[groupNum]
    bitmapStartPos = bgdtEntry.blockBitmapLocation * self._superblock.blockSize
    byte = unpack("B", self._device.read(bitmapStartPos + byteIndex, 1))[0]
    self._device.write(bitmapStartPos + byteIndex, pack("B", int(byte) & ~(1 << bitIndex)))
    self._superblock.numFreeBlocks += 1
    bgdtEntry.numFreeBlocks += 1



  def _allocateBlock(self, zeros = False):
    """Allocates the first free block and returns its id."""
    bitmapSize = self._superblock.numBlocksPerGroup / 8
    bitmapStartPos = None
    bgdtEntry = None
    groupNum = 0
    
    for groupNum, bgdtEntry in enumerate(self._bgdt.entries):
      if bgdtEntry.numFreeBlocks > 0:
        bitmapStartPos = bgdtEntry.blockBitmapLocation * self._superblock.blockSize
        break
    if bitmapStartPos is None:
      raise FilesystemError("No free blocks.")

    bitmapBytes = self._device.read(bitmapStartPos, bitmapSize)
    if len(bitmapBytes) < bitmapSize:
      raise FilesystemError("Invalid block bitmap.")
    bitmap = unpack("{0}B".format(bitmapSize), bitmapBytes)

    for byteIndex, byte in enumerate(bitmap):
      if byte != 255:
        for i in range(8):
          if (1 << i) & byte == 0:
            bid = (groupNum * self._superblock.numBlocksPerGroup) + (byteIndex * 8) + i + self._superblock.firstDataBlockId
            self._device.write(bitmapStartPos + byteIndex, pack("B", byte | (1 << i)))
            self._superblock.numFreeBlocks -= 1
            bgdtEntry.numFreeBlocks -= 1
            if zeros:
              start = bid * self._superblock.blockSize
              for i in range(self._superblock.blockSize):
                self._device.write(start + i, pack("B", 0))
            self._superblock.timeLastWrite = int(time())
            return bid
    
    raise FilesystemError("No free blocks.")
  
  
  
  def _writeToBlock(self, bid, offset, byteString):
    """Writes the specified byte string to the specified block id at the given offset within the block."""
    assert offset + len(byteString) <= self._superblock.blockSize, "Byte array does not fit within block."
    self._device.write(offset + bid * self._superblock.blockSize, byteString)
    self._superblock.timeLastWrite = int(time())
    
  
  
  def _readInode(self, inodeNum):
    """Reads the specified inode number and returns the inode object."""
    return _Inode.read(inodeNum, self._bgdt, self._superblock, self)
  
  
  
  def _allocateInode(self, mode, uid, gid, creationTime, modTime, accessTime):
    """Allocates a new inode and returns the inode object."""
    return _Inode.new(self._bgdt, self._superblock, self, mode, uid, gid, creationTime, modTime, accessTime)




