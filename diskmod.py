__author__ = "Michael R. Falcone"
__version__ = "0.1"

"""
Module for reading and checking an ext2 disk image.
"""

import re
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



class BlockGroupReport(object):
  """Contains information about the filesystem's block groups."""
  pass

class IntegrityReport(object):
  """Contains the results of an integrity check on the filesystem."""
  pass





# ====== EXT2 FILE ================================================

class Ext2File(object):
  """Represents a file or directory on the ext2 filesystem."""
  
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
  def timeCreated(self):
    """Gets the time and date the file was last created as a string."""
    return strftime("%b %d %I:%M", localtime(self._inode.time_created))
  
  @property
  def timeAccessed(self):
    """Gets the time and date the file was last accessed as a string."""
    return strftime("%b %d %I:%M", localtime(self._inode.time_accessed))
  
  @property
  def timeModified(self):
    """Gets the time and date the file was last modified as a string."""
    return strftime("%b %d %I:%M", localtime(self._inode.time_modified))
  
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
      raise UnsupportedOperationError()
    
    contents = []
    for i in range(12):
      blockId = self._inode.blocks[i]
      if blockId == 0:
        break
      blockBytes = self._disk._readBlock(blockId)
      
      offset = 0
      while offset < self._disk.blockSize:
        fields = unpack_from("<IHBx255s", blockBytes, offset)
        if fields[0] == 0:
          break
        name = fields[3][:fields[2]]
        contents.append(Ext2File(name, self, fields[0], self._disk))
        offset += fields[1]
    
    return contents









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
  def revision(self):
    """Gets the filesystem revision as a string formatted as MAJOR.MINOR."""
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
    """Scans all block groups and returns information about them."""
    report = BlockGroupReport()
    
    report.numFiles = 0
    report.numDirs = 0
    
    for i,entry in enumerate(self._bgroupDescTable.entries):
      pass
    
    return report
  
  
  
  def checkIntegrity(self):
    """Evaluates the integrity of the filesystem and generates a report."""
    report = IntegrityReport()
    
    report.hasMagicNumber = True
    
    return report
  
  
  
  
  # PRIVATE METHODS ------------------------------------
  
  def __readSuperblock(self, startPos):
    """Reads the superblock at the specified position in bytes."""
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
      sb.frag_size = 1024 >> fields[7]
    sb.num_blocks_per_group = fields[8]
    sb.num_frags_per_group = fields[9]
    sb.num_inodes_per_group = fields[10]
    sb.time_last_mount = fields[11]
    sb.time_last_write = fields[12]
    sb.num_mounts_since_ck = fields[13]
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
    sb.time_last_ck = fields[19]
    sb.time_between_ck = fields[20]
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
    sb.superblock_group_nr = fields[2]
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
    
    return sb
  
  
  def __readBGroupDescriptorTable(self, superblock):
    """Reads the block group descriptor table following the specified superblock."""
    startPos = (superblock.first_block_id + 1) * superblock.block_size
    numGroups = int(ceil(superblock.num_blocks / superblock.num_blocks_per_group))
    tableSize = numGroups * 32
    
    with open(self._imageFile, "rb") as f:
      f.seek(startPos)
      bgdtBytes = f.read(tableSize)
    if len(bgdtBytes) < tableSize:
      raise Exception("Invalid block group descriptor table.")
    
    bgdt = self.__BGroupDescriptorTable()
    bgdt.entries = []
    
    for i in range(numGroups):
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
    if bitmapByte & usedTest == 0:
      raise Exception("Inode not in use.")
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
  



