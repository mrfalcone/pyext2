__author__ = "Michael R. Falcone"
__version__ = "0.1"

"""
Module for reading and checking an ext2 disk image. Attempts to support
revision levels 0-1.
"""

import re
import inspect
from Queue import Queue
from struct import unpack, unpack_from
from math import ceil
from time import localtime, strftime


class InvalidImageFormatError(Exception):
  """Thrown when the format of the disk image does not match the filesystem."""
  pass

class InvalidFileTypeError(Exception):
  """Thrown when a file object does not have the proper type for the
  requested operation."""
  pass

class UnsupportedOperationError(Exception):
  """Thrown when the filesystem does not support the requested operation."""
  pass

class FileNotFoundError(Exception):
  """Thrown when the filesystem cannot find a file object."""
  pass



class InformationReport(object):
  """Structure used to return information about the filesystem."""
  pass





# ====== EXT2 FILE ================================================

class Ext2File(object):
  """Represents a file or directory on the ext2 filesystem."""
  
  @property
  def fsType(self):
    """Gets a string representing the filesystem type. Always EXT2"""
    return "EXT2"
  
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
    return self._inode.num
  
  @property
  def isValid(self):
    """Returns True if the inode of this file is in use, or False if it is not."""
    return self._inode.used
  
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
    """Gets the number of hard linkes to this file object."""
    return self._inode.num_links
  
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
    """Gets the number of blocks used by the file on the filesystem."""
    return self._numBlocks
  
  @property
  def timeCreated(self):
    """Gets the time and date the file was last created as a string."""
    return strftime("%b %d %I:%M %Y", localtime(self._inode.time_created))
  
  @property
  def timeAccessed(self):
    """Gets the time and date the file was last accessed as a string."""
    return strftime("%b %d %I:%M %Y", localtime(self._inode.time_accessed))
  
  @property
  def timeModified(self):
    """Gets the time and date the file was last modified as a string."""
    return strftime("%b %d %I:%M %Y", localtime(self._inode.time_modified))
  
  @property
  def parentDir(self):
    """Gets this file object's parent directory."""
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
      
  
  def __str__(self):
    return "{0},{1},{2},{3},{4},{5},{6},{7},{8},{9}".format(self.inodeNum,
      self.modeStr, self.numLinks, self.uid, self.gid, self.size, self.timeCreated,
      self.timeAccessed, self.timeModified, self.name)
  
  def listContents(self):
    """Gets directory contents if this file object is a directory. Ignores
    file types and treats name length as one byte."""
    if not self.isDir:
      raise InvalidFileTypeError()
    if (self._inode.flags & 0x00001000) != 0:
      raise UnsupportedOperationError() # indexed directory structure not supported
    
    contents = []
    for i in range(self.numBlocks):
      blockId = self.__findBlockId(i)
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
    """Resets the file pointer used for reading bytes from the file."""
    self._filePointer = 0
  
  
  def read(self):
    """If the file object is a regular file, reads the next chunk of bytes as
    a byte array and updates the file pointer. Returns an empty array if
    the file pointer is at the end of the file."""
    if not self.isRegular:
      raise InvalidFileTypeError()
    if self._filePointer >= self.size:
      return []
    
    chunkBlockId = self.__findBlockId(self._filePointer / self._disk.blockSize)
    
    chunk = self._disk._readBlock(chunkBlockId)[(self._filePointer % self._disk.blockSize):]
    self._filePointer += len(chunk)
    if self._filePointer > self.size:
      chunk = chunk[:(self.size % self._disk.blockSize)]
    
    return chunk
  
  
  def __findBlockId(self, index):
    """Looks up the block id corresponding to the block at the specified index."""
    if index >= self.numBlocks:
      raise Exception("Block index out of range.")
    
    numIdsPerBlock = self._disk.blockSize / 4
    def __bidListAtBid(bid):
      bytes = self._disk._readBlock(bid)
      return unpack_from("<{0}I".format(numIdsPerBlock), bytes)
    
    maxDirect = 12
    maxIndirect = maxDirect + numIdsPerBlock
    maxDoublyIndirect = maxIndirect + numIdsPerBlock ** 2
    maxTreblyIndirect = maxDoublyIndirect + numIdsPerBlock ** 3
    
    if index < maxDirect:
      return self._inode.blocks[index]
    
    elif index < maxIndirect:
      direct = __bidListAtBid(self._inode.blocks[12])
      return direct[index - maxDirect]
    
    elif index < maxDoublyIndirect:
      indirect = __bidListAtBid(self._inode.blocks[13])
      index -= maxIndirect # get index from start of doubly indirect list
      direct = __bidListAtBid(indirect[index / numIdsPerBlock])
      return direct[index % numIdsPerBlock]
    
    
    raise Exception("Block id not found.")







# ====== EXT2 DISK ================================================

class Ext2Disk(object):
  """Models a disk image within a file formatted to the ext2 filesystem."""
  
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
    return "{0}.{1}".format(self._superblock.rev_level, self._superblock.rev_minor)
  
  @property
  def totalSpace(self):
    """Gets the total filesystem size in bytes."""
    return self._superblock.block_size * self._superblock.num_blocks
  
  @property
  def freeSpace(self):
    """Gets the number of free bytes."""
    return self._superblock.block_size * self._superblock.num_free_blocks
  
  @property
  def usedSpace(self):
    """Gets the number of used bytes."""
    return self.totalSpace - self.freeSpace
  
  @property
  def blockSize(self):
    """Gets the block size in bytes."""
    return self._superblock.block_size
  
  @property
  def numBlockGroups(self):
    """Gets the number of block groups."""
    return len(self._bgroupDescTable.entries)
  
  @property
  def numInodes(self):
    """Gets the total number of inodes."""
    return self._superblock.num_inodes
  
  @property
  def rootDir(self):
    """Gets the file object representing the root directory."""
    return self._rootDir
  
  
  
  
  # PUBLIC METHODS ------------------------------------
  
  def __init__(self, imageFile):
    """Constructs a new ext2 disk from the specified image file. Raises an
    InvalidImageFormatError if the root directory cannot be loaded."""
    self._imageFile = imageFile
    try:
      self._superblock = self.__readSuperblock(1024)
      self._bgroupDescTable = self.__readBGroupDescriptorTable(self._superblock)
      self._rootDir = Ext2File("", None, 2, self)
    except:
      raise InvalidImageFormatError()
  
  
  def getFile(self, absolutePath):
    """Looks up and returns the file specified by the absolute path. Raises a
    FileNotFoundError if the file object cannot be found."""
    pathParts = re.compile(r"/+").split(absolutePath)
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
  
  
  
  def scanBlockGroups(self):
    """Scans all block groups and returns an information report about them."""
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
    
    
    # validate inode references
    inodes = self.__getUsedInodes()
    inodesReachable = dict(zip(inodes, [False] * len(inodes)))
    
    q = Queue()
    q.put(self.rootDir)
    while not q.empty():
      dir = q.get()
      for f in dir.listContents():
        if f.name == "." or f.name == "..":
          continue
        if f.isDir:
          q.put(f)
        if not (f.isValid and f.inodeNum in inodesReachable):
          report.messages.append("The filesystem contains an entry for {0} but its inode is not marked as used (inode number {1}).".format(f.absolutePath, f.inodeNum))
        else:
          inodesReachable[f.inodeNum] = True
    
    for inodeNum in inodesReachable:
      if not inodesReachable[inodeNum]:
        report.messages.append("Inode number {0} is marked as used but does not have a reachable directory entry.".format(inodeNum))
    
    
    # validate data block references
    # TODO
    
    return report
  
  
  
  
  # PRIVATE METHODS ------------------------------------
  
  def __readSuperblock(self, startPos):
    """Reads the superblock at the specified position in bytes. Returns a structure
    containing the superblock values. Structure members prefixed with an underscore are
    unique to each copy of the superblock."""
    with open(self._imageFile, "rb") as f:
      f.seek(startPos)
      sbBytes = f.read(1024)
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
          last3 = last3 * 3
        last7 = 7
        while last7 < sb.num_block_groups:
          sb.copy_block_group_ids.append(last7)
          last7 = last7 * 7
        sb.copy_block_group_ids.sort()
    
    return sb
  
  
  def __readBGroupDescriptorTable(self, superblock):
    """Reads the block group descriptor table following the specified superblock."""
    groupStart = superblock._superblock_group_nr * superblock.num_blocks_per_group * superblock.block_size
    startPos = groupStart + (superblock.block_size * (superblock.first_block_id + 1))
    tableSize = superblock.num_block_groups * 32
    
    with open(self._imageFile, "rb") as f:
      f.seek(startPos)
      bgdtBytes = f.read(tableSize)
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
    with open(self._imageFile, "rb") as f:
      for bgroupDescEntry in self._bgroupDescTable.entries:
        bitmapStartPos = bgroupDescEntry.bid_inode_bitmap * self._superblock.block_size
        bitmapSize = self._superblock.num_inodes_per_group / 8
        f.seek(bitmapStartPos)
        bitmapBytes = f.read(bitmapSize)
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
    
    with open(self._imageFile, "rb") as f:
      f.seek(bitmapStartPos + bitmapByteIndex)
      bitmapByte = unpack("B", f.read(1))[0]
      f.seek(inodeStartPos)
      inodeBytes = f.read(self._superblock.inode_size)
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
  
  
  def _readBlock(self, blockId):
    """Reads the entire block specified by the given block id."""
    startPos = blockId * self._superblock.block_size
    with open(self._imageFile, "rb") as f:
      f.seek(startPos)
      bytes = f.read(self._superblock.block_size)
    if len(bytes) < self._superblock.block_size:
      raise Exception("Invalid block.")
    return bytes
  



