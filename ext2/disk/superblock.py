#!/usr/bin/env python
"""
Defines the internal superblock class used by the ext2 module.
"""
__license__ = "BSD"
__copyright__ = "Copyright 2013, Michael R. Falcone"


from struct import unpack_from
from math import ceil


class _Superblock(object):
  """Provides access to the filesystem's superblock. This class is for internal use only."""
  _saveCopies = True


  # READ-ONLY PROPERTIES -------------------------------------

  @property
  def numInodes(self):
    """Gets the total number of inodes."""
    return self._num_inodes

  @property
  def numBlocks(self):
    """Gets the total number of blocks."""
    return self._num_blocks

  @property
  def numReservedBlocks(self):
    """Gets the number of system reserved blocks."""
    return self._num_res_blocks

  @property
  def firstDataBlockId(self):
    """Gets the id of the first block of the filesystem."""
    return self._first_block_id

  @property
  def blockSize(self):
    """Gets the size of the filesystem blocks in bytes."""
    return self._block_size

  @property
  def fragmentSize(self):
    """Gets the size of the fragments in bytes."""
    return self._frag_size

  @property
  def numBlocksPerGroup(self):
    """Gets the number of blocks per block group."""
    return self._num_blocks_per_group

  @property
  def numFragmentsPerGroup(self):
    """Gets the number of fragments per block group."""
    return self._num_frags_per_group

  @property
  def numInodesPerGroup(self):
    """Gets the number of inodes per block group."""
    return self._num_inodes_per_group

  @property
  def numMountsMax(self):
    """Gets the maximum number of times the filesystem should be mounted before being checked."""
    return self._num_mounts_max

  @property
  def magicNumber(self):
    """Gets the value of the magic number field."""
    return self._magic_number

  @property
  def isValidExt2(self):
    """Gets whether the filesystem is Ext2 (if the magic number is 0xEF53)."""
    return (self._magic_number == 0xEF53)

  @property
  def errorAction(self):
    """Gets the action to take upon error."""
    return self._error_action

  @property
  def revisionMinor(self):
    """Gets the minor revision level."""
    return self._rev_minor

  @property
  def timeLastChecked(self):
    """Gets the time the filesystem was last checked."""
    return self._time_last_check

  @property
  def checkInterval(self):
    """Gets the maximum time that can pass before the filesystem should be checked, in ms."""
    return self._time_between_check

  @property
  def creatorOS(self):
    """Gets the name of the OS that created this filesystem."""
    return self._creator_os

  @property
  def revisionMajor(self):
    """Gets the major revision level."""
    return self._rev_level

  @property
  def defaultReservedUID(self):
    """Gets the default UID allowed to use reserved blocks."""
    return self._def_uid_res

  @property
  def defaultReservedGID(self):
    """Gets the default GID allowed to use reserved blocks."""
    return self._def_gid_res

  @property
  def numBlockGroups(self):
    """Gets the number of block groups."""
    return self._num_block_groups

  @property
  def copyLocations(self):
    """Gets a list of block group ids where a superblock copy is stored."""
    return self._copy_block_group_ids

  @property
  def firstInode(self):
    """Gets the first inode index that can be used by user data."""
    return self._first_inode_index

  @property
  def inodeSize(self):
    """Gets the size of the inode structure in bytes."""
    return self._inode_size

  @property
  def _groupNum(self):
    """Gets the group number of this superblock. This value is unique for each superblock copy."""
    return self._superblock_group_nr

  @property
  def featuresCompatible(self):
    """Gets the bitmap of compatible features."""
    return self._compat_feature_bitmask

  @property
  def featuresIncompatible(self):
    """Gets the bitmap of incompatible features (do not mount if an indicated feature is not supported)."""
    return self._incompat_feature_bitmask

  @property
  def featuresReadOnlyCompatible(self):
    """Gets the bitmap of features that are read-only compatible."""
    return self._rocompat_feature_bitmask

  @property
  def volumeId(self):
    """Gets the volume id."""
    return self._vol_id

  @property
  def lastMountPath(self):
    """Gets the path where the filesystem was last mounted."""
    return self._last_mount_path

  @property
  def compressionAlgorithms(self):
    """Gets the bitmap of compression algorithms used."""
    return self._compression_algo

  @property
  def numPreallocBlocksFile(self):
    """Gets the number of blocks to preallocate for new files."""
    return self._num_prealloc_blocks_file

  @property
  def numPreallocBlocksDir(self):
    """Gets the number of blocks to preallocate for new directories."""
    return self._num_prealloc_blocks_dir

  @property
  def journalSuperblockUUID(self):
    """Gets the UUID of the journal superblock."""
    return self._journal_superblock_uuid

  @property
  def journalFileInode(self):
    """Gets the inode number of the journal file."""
    return self._journal_file_inode_num

  @property
  def journalFileDevice(self):
    """Gets the device number of the journal file."""
    return self._journal_file_dev

  @property
  def lastOrphanInode(self):
    """Gets the inode number of the last orphan."""
    return self._last_orphan_inode_num

  @property
  def hashSeeds(self):
    """Gets a list of 4 hash seeds used for directory indexing."""
    return self._hash_seeds

  @property
  def defaultHashVersion(self):
    """Gets the default hash version used for directory indexing."""
    return self._def_hash_ver

  @property
  def defaultMountOptions(self):
    """Gets the default mount options."""
    return self._def_mount_options

  @property
  def firstMetaBlockGroup(self):
    """Gets the id of the first meta block group."""
    return self._first_meta_bgroup_id




  # WRITABLE PROPERTIES -------------------------------------

  @property
  def numFreeBlocks(self):
    """Gets the number of free blocks."""
    return self._num_free_blocks
  @numFreeBlocks.setter
  def numFreeBlocks(self, value):
    """Sets the number of free blocks."""
    self._num_free_blocks = value
    # TODO write to image

  @property
  def numFreeInodes(self):
    """Gets the number of free inodes."""
    return self._num_free_inodes
  @numFreeInodes.setter
  def numFreeInodes(self, value):
    """Sets the number of free inodes."""
    self._num_free_inodes = value
    # TODO write to image

  @property
  def timeLastMount(self):
    """Gets the last mount time."""
    return self._time_last_mount
  @timeLastMount.setter
  def timeLastMount(self, value):
    """Sets the last mount time."""
    self._time_last_mount = value
    # TODO write to image

  @property
  def timeLastWrite(self):
    """Gets the time of last write access."""
    return self._time_last_write
  @timeLastWrite.setter
  def timeLastWrite(self, value):
    """Sets the time of last write access."""
    self._time_last_write = value
    # TODO write to image

  @property
  def numMountsSinceCheck(self):
    """Gets the number of mounts since the last filesystem check."""
    return self._num_mounts_since_check
  @numMountsSinceCheck.setter
  def numMountsSinceCheck(self, value):
    """Sets the number of mounts since the last filesystem check."""
    self._num_mounts_since_check = value
    # TODO write to image

  @property
  def state(self):
    """Gets the state of the filesystem as a string that is either VALID or ERROR."""
    if self._state == 1:
      return "VALID"
    return "ERROR"
  @state.setter
  def state(self, value):
    """Sets the state of the filesystem as 1 for VALID or 0 for ERROR."""
    float(value) # raise exception if not a number
    self._state = value
    # TODO write to image

  @property
  def volumeName(self):
    """Gets the name of the volume."""
    return self._vol_name
  @volumeName.setter
  def volumeName(self, value):
    """Sets the name of the volume."""
    self._vol_name = value
    # TODO write to image




  # MAIN METHODS -------------------------------------------

  @classmethod
  def new(cls, byteOffset, imageFile):
    """Creates a new superblock at the byte offset in the specified image file, and returns
    the new object."""
    # TODO implement creation
    return None


  @classmethod
  def read(cls, byteOffset, imageFile):
    """Reads a superblock from the bytes at byteOffset in imageFile and returns the superblock object."""
    imageFile.seek(byteOffset)
    sbBytes = imageFile.read(1024)
    if len(sbBytes) < 1024:
      raise Exception("Invalid superblock.")
    return cls(sbBytes, byteOffset, imageFile)


  def __init__(self, sbBytes, byteOffset, imageFile):
    """Constructs a new superblock from the given byte array."""
    self._byteOffset = byteOffset
    self._imageFile = imageFile

    # read standard fields
    fields = unpack_from("<7Ii5I6H4I2H", sbBytes)
    self._num_inodes = fields[0]
    self._num_blocks = fields[1]
    self._num_res_blocks = fields[2]
    self._num_free_blocks = fields[3]
    self._num_free_inodes = fields[4]
    self._first_block_id = fields[5]
    self._block_size = 1024 << fields[6]
    if fields[7] > 0:
      self._frag_size = 1024 << fields[7]
    else:
      self._frag_size = 1024 >> abs(fields[7])
    self._num_blocks_per_group = fields[8]
    self._num_frags_per_group = fields[9]
    self._num_inodes_per_group = fields[10]
    self._time_last_mount = fields[11]
    self._time_last_write = fields[12]
    self._num_mounts_since_check = fields[13]
    self._num_mounts_max = fields[14]
    self._magic_number = fields[15]
    if fields[16] == 1:
      self._state = "VALID"
    else:
      self._state = "ERROR"
    if fields[17] == 1:
      self._error_action = "CONTINUE"
    elif fields[17] == 2:
      self._error_action = "RO"
    else:
      self._error_action = "PANIC"
    self._rev_minor = fields[18]
    self._time_last_check = fields[19]
    self._time_between_check = fields[20]
    if fields[21] == 0:
      self._creator_os = "LINUX"
    elif fields[21] == 1:
      self._creator_os = "HURD"
    elif fields[21] == 2:
      self._creator_os = "MASIX"
    elif fields[21] == 3:
      self._creator_os = "FREEBSD"
    elif fields[21] == 4:
      self._creator_os = "LITES"
    else:
      self._creator_os = "UNDEFINED"
    self._rev_level = fields[22]
    self._def_uid_res = fields[23]
    self._def_gid_res = fields[24]

    if self._num_blocks_per_group > 0:
      self._num_block_groups = int(ceil(self._num_blocks / self._num_blocks_per_group))
    else:
      self._num_block_groups = 0


    # read additional fields
    if self._rev_level == 0:
      self._first_inode_index = 11
      self._inode_size = 128
      self._superblock_group_nr = 0
      self._compat_feature_bitmask = 0
      self._incompat_feature_bitmask = 0
      self._rocompat_feature_bitmask = 0
      self._vol_id = ""
      self._vol_name = ""
      self._last_mount_path = ""
      self._compression_algo = None
      self._num_prealloc_blocks_file = 0
      self._num_prealloc_blocks_dir = 0
      self._journal_superblock_uuid = None
      self._journal_file_inode_num = None
      self._journal_file_dev = None
      self._last_orphan_inode_num = None
      self._hash_seeds = None
      self._def_hash_ver = None
      self._def_mount_options = None
      self._first_meta_bgroup_id = None
      self._copy_block_group_ids = range(self._num_block_groups)

    else:
      fields = unpack_from("<I2H3I16s16s64sI2B2x16s3I4IB3x2I", sbBytes, 84)
      self._first_inode_index = fields[0]
      self._inode_size = fields[1]
      self._superblock_group_nr = fields[2]
      self._compat_feature_bitmask = fields[3]
      self._incompat_feature_bitmask = fields[4]
      self._rocompat_feature_bitmask = fields[5]
      self._vol_id = fields[6].rstrip('\0')
      self._vol_name = fields[7].rstrip('\0')
      self._last_mount_path = fields[8].rstrip('\0')
      self._compression_algo = fields[9]
      self._num_prealloc_blocks_file = fields[10]
      self._num_prealloc_blocks_dir = fields[11]
      self._journal_superblock_uuid = fields[12].rstrip('\0')
      self._journal_file_inode_num = fields[13]
      self._journal_file_dev = fields[14]
      self._last_orphan_inode_num = fields[15]
      self._hash_seeds = []
      self._hash_seeds.append(fields[16])
      self._hash_seeds.append(fields[17])
      self._hash_seeds.append(fields[18])
      self._hash_seeds.append(fields[19])
      self._def_hash_ver = fields[20]
      self._def_mount_options = fields[21]
      self._first_meta_bgroup_id = fields[22]

      self._copy_block_group_ids = []
      self._copy_block_group_ids.append(0)
      if self._num_block_groups > 1:
        self._copy_block_group_ids.append(1)
        last3 = 3
        while last3 < self._num_block_groups:
          self._copy_block_group_ids.append(last3)
          last3 *= 3
        last7 = 7
        while last7 < self._num_block_groups:
          self._copy_block_group_ids.append(last7)
          last7 *= 7
        self._copy_block_group_ids.sort()

