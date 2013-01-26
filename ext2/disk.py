#!/usr/bin/env python
"""
Defines classes for the disk object used by the ext2 module.
"""
__license__ = "BSD"
__copyright__ = "Copyright 2013, Michael R. Falcone"


import re
import inspect
from Queue import Queue
from struct import pack, unpack, unpack_from
from math import ceil
from os import fsync
from .error import *
from .file import Ext2File


class InformationReport(object):
  """Structure used to return information about the filesystem."""
  pass


class Ext2Disk(object):
  """Models a disk image file formatted to the Ext2 filesystem."""
  
  class __Superblock:
    pass
  class __BGroupDescriptorTable:
    pass
  class __BGroupDescriptorEntry:
    pass
  class __Inode:
    pass
  
  
  # PROPERTIES -------------------------------------------------
  
  @property
  def fsType(self):
    """Gets a string representing the filesystem type. Always EXT2"""
    return "EXT2"
  
  @property
  def revision(self):
    """Gets the filesystem revision string formatted as MAJOR.MINOR."""
    assert self.isValid, "Filesystem is not valid."
    return "{0}.{1}".format(self._superblock.rev_level, self._superblock.rev_minor)
  
  @property
  def totalSpace(self):
    """Gets the total filesystem size in bytes."""
    assert self.isValid, "Filesystem is not valid."
    return self._superblock.block_size * self._superblock.num_blocks
  
  @property
  def freeSpace(self):
    """Gets the number of free bytes."""
    assert self.isValid, "Filesystem is not valid."
    return self._superblock.block_size * self._superblock.num_free_blocks
  
  @property
  def usedSpace(self):
    """Gets the number of used bytes."""
    assert self.isValid, "Filesystem is not valid."
    return self.totalSpace - self.freeSpace
  
  @property
  def blockSize(self):
    """Gets the block size in bytes."""
    assert self.isValid, "Filesystem is not valid."
    return self._superblock.block_size
  
  @property
  def numBlockGroups(self):
    """Gets the number of block groups."""
    assert self.isValid, "Filesystem is not valid."
    return len(self._bgroupDescTable.entries)
  
  @property
  def numInodes(self):
    """Gets the total number of inodes."""
    assert self.isValid, "Filesystem is not valid."
    return self._superblock.num_inodes
  
  @property
  def rootDir(self):
    """Gets the file object representing the root directory."""
    assert self.isValid, "Filesystem is not valid."
    return self._rootDir

  @property
  def isValid(self):
    """Gets whether the disk's filesystem is valid and mounted."""
    return self._isValid
  
  
  
  
  # LIFECYCLE METHODS ------------------------------------
  
  def __init__(self, imageFilename):
    """Constructs a new Ext2 disk from the specified image filename."""
    self._imageFile = None
    self._imageFilename = imageFilename
    self._isValid = False
  
  def __del__(self):
    """Destructor that unmounts the filesystem if it has not been unmounted."""
    if self._imageFile:
      self.unmount()
  
  def __enter__ (self):
    """Mounts the filesystem and returns the root directory."""
    self.mount()
    return self.rootDir

  def __exit__ (self, type, value, tb):
    """Unmounts the filesystem and re-raises any exception that occurred."""
    self.unmount()
  
  
  
  def mount(self):
    """Mounts the Ext2 disk for reading and writing and reads the root directory. Raises an
    InvalidImageFormatError if the root directory cannot be read."""
    self._imageFile = open(self._imageFilename, "r+b")
    try:
      self._superblock = self.__readSuperblock(1024)
      self._bgroupDescTable = self.__readBGroupDescriptorTable(self._superblock)
      self._isValid = True
      self._rootDir = Ext2File("", None, 2, self)
    except:
      if self._imageFile:
        self._imageFile.close()
      self._imageFile = None
      self._isValid = False
      raise InvalidImageFormatError()
  
  
  
  def unmount(self):
    """Unmounts the Ext2 disk so that reading and writing may no longer occur, and closes
    access to the disk image file."""
    if self._imageFile:
      self._imageFile.flush()
      fsync(self._imageFile.fileno())
      self._imageFile.close()
    self._imageFile = None
    self._isValid = False
  
  
  
  
  
  # PUBLIC METHODS ------------------------------------
  
  
  def getFile(self, absolutePath):
    """Looks up and returns the file specified by the absolute path. Raises a
    FileNotFoundError if the file object cannot be found."""
    assert self.isValid, "Filesystem is not valid."
    
    pathParts = re.compile("/+").split(absolutePath)
    if len(pathParts) == 0:
      raise FileNotFoundError()
    if not pathParts[0] == "":
      raise FileNotFoundError()
    
    if len(pathParts) > 1 and pathParts[-1] == "":
      del pathParts[-1]
    localName = pathParts[-1]
    fileObject = self._rootDir
    del pathParts[0]
    for localPath in pathParts:
      if not fileObject.isDir:
        break
      for f in fileObject.listContents():
        if f.name == localPath:
          fileObject = f
          break
    
    if not fileObject.name == localName:
      raise FileNotFoundError()
    
    return fileObject
  
  
  
  def makeDirFile(self, absolutePath):
    """Creates a new directory on the filesystem and returns its file object."""
    assert self.isValid, "Filesystem is not valid."
    
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
    
    
    # TODO allocate inode
    print parentDir.absolutePath
    print fileName
  
  
  
  def makeRegularFile(self, absolutePath):
    """Creates a new regular file on the filesystem and returns its file object."""
    assert self.isValid, "Filesystem is not valid."
    pass
  
  
  
  def makeLink(self, absolutePath, linkedFile, isSymbolic):
    """Creates a new link to the specified file object and returns the link file object."""
    assert self.isValid, "Filesystem is not valid."
    pass
  
  
  
  def scanBlockGroups(self):
    """Scans all block groups and returns an information report about them."""
    assert self.isValid, "Filesystem is not valid."
    
    report = InformationReport()
    
    # count files and directories
    report.numRegFiles = 0
    report.numSymlinks = 0
    report.numDirs = 1 # initialize with root directory
    q = Queue()
    q.put(self.rootDir)
    while not q.empty():
      dir = q.get()
      for f in dir.listContents():
        if f.name == "." or f.name == "..":
          continue
        if f.isDir:
          report.numDirs += 1
          q.put(f)
        elif f.isRegular:
          report.numRegFiles += 1
        elif f.isSymlink:
          report.numSymlinks += 1
    
    # report block group information
    report.groupReports = []
    for i,entry in enumerate(self._bgroupDescTable.entries):
      groupReport = InformationReport()
      groupReport.numFreeBlocks = entry.num_free_blocks
      groupReport.numFreeInodes = entry.num_free_inodes
      report.groupReports.append(groupReport)
    
    return report
  
  
  
  
  def checkIntegrity(self):
    """Evaluates the integrity of the filesystem and returns an information report."""
    assert self.isValid, "Filesystem is not valid."
    
    report = InformationReport()
    
    # basic integrity checks
    report.hasMagicNumber = (self._superblock.magic_number == 0xEF53)
    report.numSuperblockCopies = len(self._superblock.copy_block_group_ids)
    report.copyLocations = list(self._superblock.copy_block_group_ids)
    report.messages = []
    
    
    # check consistency across superblock/group table copies
    sbMembers = dict(inspect.getmembers(self._superblock))
    bgtMembersEntries = map(dict, map(inspect.getmembers, self._bgroupDescTable.entries))
    for groupId in self._superblock.copy_block_group_ids:
      if groupId == 0:
        continue
      
      # evaluate superblock copy consistency
      try:
        startPos = 1024 + groupId * self._superblock.num_blocks_per_group * self._superblock.block_size
        sbCopy = self.__readSuperblock(startPos)
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
        bgtCopy = self.__readBGroupDescriptorTable(sbCopy)
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
    
    q = Queue()
    q.put(self.rootDir)
    while not q.empty():
      dir = q.get()
      for f in dir.listContents():
        if f.name == "." or f.name == "..":
          continue
        if f.isDir:
          q.put(f)
        
        # check inode references
        if not (f.isValid and f.inodeNum in inodesReachable):
          report.messages.append("The filesystem contains an entry for {0} but its inode is not marked as used (inode number {1}).".format(f.absolutePath, f.inodeNum))
        else:
          inodesReachable[f.inodeNum] = True
        
        # check block references
        for bid in f._getUsedBlocks():
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
  
  
  
  
  # PRIVATE METHODS ------------------------------------
  
  def __readSuperblock(self, startPos):
    """Reads the superblock at the specified position in bytes. Returns a structure
    containing the superblock values. Structure members prefixed with an underscore are
    unique to each copy of the superblock."""
    self._imageFile.seek(startPos)
    sbBytes = self._imageFile.read(1024)
    if len(sbBytes) < 1024:
      raise Exception("Invalid superblock.")
    
    sb = self.__Superblock()
    
    # read standard fields
    fields = unpack_from("<7Ii5I6H4I2H", sbBytes)
    sb.num_inodes = fields[0]
    sb.num_blocks = fields[1]
    sb.num_res_blocks = fields[2]
    sb.num_free_blocks = fields[3]
    sb.num_free_inodes = fields[4]
    sb.first_block_id = fields[5]
    sb.block_size = 1024 << fields[6]
    if fields[7] > 0:
      sb.frag_size = 1024 << fields[7]
    else:
      sb.frag_size = 1024 >> abs(fields[7])
    sb.num_blocks_per_group = fields[8]
    sb.num_frags_per_group = fields[9]
    sb.num_inodes_per_group = fields[10]
    sb.time_last_mount = fields[11]
    sb.time_last_write = fields[12]
    sb.num_mounts_since_check = fields[13]
    sb.num_mounts_max = fields[14]
    sb.magic_number = fields[15]
    if fields[16] == 1:
      sb.state = "VALID"
    else:
      sb.state = "ERROR"
    if fields[17] == 1:
      sb.error_action = "CONTINUE"
    elif fields[17] == 2:
      sb.error_action = "RO"
    else:
      sb.error_action = "PANIC"
    sb.rev_minor = fields[18]
    sb.time_last_check = fields[19]
    sb.time_between_check = fields[20]
    if fields[21] == 0:
      sb.creator_os = "LINUX"
    elif fields[21] == 1:
      sb.creator_os = "HURD"
    elif fields[21] == 2:
      sb.creator_os = "MASIX"
    elif fields[21] == 3:
      sb.creator_os = "FREEBSD"
    elif fields[21] == 4:
      sb.creator_os = "LITES"
    else:
      sb.creator_os = "UNDEFINED"
    sb.rev_level = fields[22]
    sb.def_uid_res = fields[23]
    sb.def_gid_res = fields[24]
    
    # read additional fields
    fields = unpack_from("<I2H3I16s16s64sI2B2x16s3I4IB3x2I", sbBytes, 84)
    sb.first_inode_index = fields[0]
    sb.inode_size = fields[1]
    sb._superblock_group_nr = fields[2]
    sb.compat_feature_bitmask = fields[3]
    sb.incompat_feature_bitmask = fields[4]
    sb.rocompat_feature_bitmask = fields[5]
    sb.vol_id = fields[6].rstrip('\0')
    sb.vol_name = fields[7].rstrip('\0')
    sb.last_mount_path = fields[8].rstrip('\0')
    if fields[9] == 1:
      sb.compression_algo = "LZV1"
    elif fields[9] == 2:
      sb.compression_algo = "LZRW3A"
    elif fields[9] == 4:
      sb.compression_algo = "GZIP"
    elif fields[9] == 8:
      sb.compression_algo = "BZIP2"
    elif fields[9] == 16:
      sb.compression_algo = "LZO"
    else:
      sb.compression_algo = "UNDEFINED"
    sb.num_prealloc_blocks_file = fields[10]
    sb.num_prealloc_blocks_dir = fields[11]
    sb.journal_superblock_uuid = fields[12].rstrip('\0')
    sb.journal_file_inode_num = fields[13]
    sb.journal_file_dev = fields[14]
    sb.last_orphan_inode_num = fields[15]
    sb.hash_seeds = []
    sb.hash_seeds.append(fields[16])
    sb.hash_seeds.append(fields[17])
    sb.hash_seeds.append(fields[18])
    sb.hash_seeds.append(fields[19])
    sb.def_hash_ver = fields[20]
    sb.def_mount_options = fields[21]
    sb.first_meta_bgroup_id = fields[22]
    
    if sb.num_blocks_per_group > 0:
      sb.num_block_groups = int(ceil(sb.num_blocks / sb.num_blocks_per_group))
    else:
      sb.num_block_groups = 0
    
    if sb.rev_level == 0:
      sb.copy_block_group_ids = range(sb.num_block_groups)
    else:
      sb.copy_block_group_ids = []
      sb.copy_block_group_ids.append(0)
      if sb.num_block_groups > 1:
        sb.copy_block_group_ids.append(1)
        last3 = 3
        while last3 < sb.num_block_groups:
          sb.copy_block_group_ids.append(last3)
          last3 *= 3
        last7 = 7
        while last7 < sb.num_block_groups:
          sb.copy_block_group_ids.append(last7)
          last7 *= 7
        sb.copy_block_group_ids.sort()
    
    return sb
  
  
  def __readBGroupDescriptorTable(self, superblock):
    """Reads the block group descriptor table following the specified superblock."""
    groupStart = superblock._superblock_group_nr * superblock.num_blocks_per_group * superblock.block_size
    startPos = groupStart + (superblock.block_size * (superblock.first_block_id + 1))
    tableSize = superblock.num_block_groups * 32

    self._imageFile.seek(startPos)
    bgdtBytes = self._imageFile.read(tableSize)
    if len(bgdtBytes) < tableSize:
      raise Exception("Invalid block group descriptor table.")
    
    bgdt = self.__BGroupDescriptorTable()
    bgdt.entries = []
    
    for i in range(superblock.num_block_groups):
      fields = unpack_from("<3I3H", bgdtBytes, i*32)
      entry = self.__BGroupDescriptorEntry()
      entry.bid_block_bitmap = fields[0]
      entry.bid_inode_bitmap = fields[1]
      entry.bid_inode_table = fields[2]
      entry.num_free_blocks = fields[3]
      entry.num_free_inodes = fields[4]
      entry.num_inodes_as_dirs = fields[5]
      bgdt.entries.append(entry)
    
    return bgdt
  
  
  def __getUsedInodes(self):
    """Returns a list of all used inode numbers, excluding those reserved by the
    filesystem."""
    used = []
    bitmaps = []
    for bgroupDescEntry in self._bgroupDescTable.entries:
      bitmapStartPos = bgroupDescEntry.bid_inode_bitmap * self._superblock.block_size
      bitmapSize = self._superblock.num_inodes_per_group / 8
      self._imageFile.seek(bitmapStartPos)
      bitmapBytes = self._imageFile.read(bitmapSize)
      if len(bitmapBytes) < bitmapSize:
        raise Exception("Invalid inode bitmap.")
      bitmaps.append(unpack("{0}B".format(bitmapSize), bitmapBytes))
    
    for groupNum,bitmap in enumerate(bitmaps):
      for byteIndex, byte in enumerate(bitmap):
        if byte != 0:
          for i in range(8):
            if (1 << i) & byte != 0:
              inum = (groupNum * self._superblock.num_inodes_per_group) + (byteIndex * 8) + i + 1
              if inum >= self._superblock.first_inode_index:
                used.append(inum)
    
    return used
  
  
  
  
  def _readInode(self, inodeNum):
    """Reads the specified inode. Ignores fragments, generation, and ACL data."""
    bgroupNum = (inodeNum - 1) / self._superblock.num_inodes_per_group
    bgroupIndex = (inodeNum - 1) % self._superblock.num_inodes_per_group
    bgroupDescEntry = self._bgroupDescTable.entries[bgroupNum]
    
    bitmapStartPos = bgroupDescEntry.bid_inode_bitmap * self._superblock.block_size
    bitmapByteIndex = bgroupIndex / 8
    usedTest = 1 << (bgroupIndex % 8)
    
    tableStartPos = bgroupDescEntry.bid_inode_table * self._superblock.block_size
    inodeStartPos = tableStartPos + (bgroupIndex * self._superblock.inode_size)

    self._imageFile.seek(bitmapStartPos + bitmapByteIndex)
    bitmapByte = unpack("B", self._imageFile.read(1))[0]
    self._imageFile.seek(inodeStartPos)
    inodeBytes = self._imageFile.read(self._superblock.inode_size)
    if len(inodeBytes) < self._superblock.inode_size:
      raise Exception("Invalid inode.")
    
    if self._superblock.rev_level == 0:
      fields = unpack_from("<2Hi4IHh4xI4x15I", inodeBytes)
    else:
      fields = unpack_from("<2H5IHh4xI4x15I8xI", inodeBytes)
    
    if self._superblock.creator_os == "LINUX":
      osFields = unpack_from("<4x2H", inodeBytes, 116)
    elif self._superblock.creator_os == "HURD":
      osFields = unpack_from("<2x3H", inodeBytes, 116)
    
    inode = self.__Inode()
    inode.num = inodeNum
    inode.used = (bitmapByte & usedTest != 0)
    inode.mode = fields[0]
    inode.uid = fields[1]
    inode.size = fields[2]
    inode.time_accessed = fields[3]
    inode.time_created = fields[4]
    inode.time_modified = fields[5]
    inode.time_deleted = fields[6]
    inode.gid = fields[7]
    inode.num_links = fields[8]
    inode.flags = fields[9]
    inode.blocks = []
    for i in range(15):
      inode.blocks.append(fields[10+i])
    if self._superblock.rev_level > 0:
      inode.size |= (fields[25] << 32)
    if self._superblock.creator_os == "LINUX":
      inode.uid |= (osFields[0] << 16)
      inode.gid |= (osFields[1] << 16)
    elif self._superblock.creator_os == "HURD":
      inode.mode |= (osFields[0] << 16)
      inode.uid |= (osFields[1] << 16)
      inode.gid |= (osFields[2] << 16)
    
    return inode
  
  
  
  
  
  def __getUsedBlocks(self):
    """Returns a list off all block ids currently in use by the filesystem."""
    used = []
    bitmaps = []
    for bgroupDescEntry in self._bgroupDescTable.entries:
      bitmapStartPos = bgroupDescEntry.bid_block_bitmap * self._superblock.block_size
      bitmapSize = self._superblock.num_blocks_per_group / 8
      self._imageFile.seek(bitmapStartPos)
      bitmapBytes = self._imageFile.read(bitmapSize)
      if len(bitmapBytes) < bitmapSize:
        raise Exception("Invalid block bitmap.")
      bitmaps.append(unpack("{0}B".format(bitmapSize), bitmapBytes))
        
    for groupNum,bitmap in enumerate(bitmaps):
      for byteIndex, byte in enumerate(bitmap):
        if byte != 0:
          for i in range(8):
            if (1 << i) & byte != 0:
              bid = (groupNum * self._superblock.num_blocks_per_group) + (byteIndex * 8) + i + 1
              used.append(bid)
    
    return used
    
  
  
  
  
  def _readBlock(self, blockId):
    """Reads the entire block specified by the given block id."""
    self._imageFile.seek(blockId * self._superblock.block_size)
    bytes = self._imageFile.read(self._superblock.block_size)
    if len(bytes) < self._superblock.block_size:
      raise Exception("Invalid block.")
    return bytes
  
  
  
  
  def _allocateInode(self, isForDirectory):
    """Finds the first free inode, marks it as used, and returns the inode number."""
    bitmapStartPos = None
    bgroupNum = 0
    bitmapSize = self._superblock.num_inodes_per_group / 8
    
    for bgroupNum, bgroupDescEntry in enumerate(self._bgroupDescTable.entries):
      if bgroupDescEntry.num_free_inodes > 0:
        bitmapStartPos = bgroupDescEntry.bid_inode_bitmap * self._superblock.block_size
        break
    if bitmapStartPos is None:
      raise Exception("No free inodes.")

    self._imageFile.seek(bitmapStartPos)
    bitmapBytes = self._imageFile.read(bitmapSize)
    if len(bitmapBytes) < bitmapSize:
      raise Exception("Invalid inode bitmap.")
    
    bitmap = unpack("{0}B".format(bitmapSize), bitmapBytes)
    for byteIndex, byte in enumerate(bitmap):
      if byte != 255:
        for i in range(8):
          if (1 << i) & byte == 0:
            inum = (bgroupNum * self._superblock.num_inodes_per_group) + (byteIndex * 8) + i + 1
            self._imageFile.seek(bitmapStartPos + byteIndex)
            self._imageFile.write(byte | (1 << i))
            # TODO mark as used, update bgdt, superblock
  



