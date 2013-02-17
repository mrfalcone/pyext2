#!/usr/bin/env python
"""
Defines the base file class used by the ext2 module.
"""
__license__ = "BSD"
__copyright__ = "Copyright 2013, Michael R. Falcone"


from time import localtime, strftime
from math import ceil
from ..error import *


class Ext2File(object):
  """Represents a file or directory on the Ext2 filesystem."""

  @property
  def fsType(self):
    """Gets a string representing the filesystem type."""
    return self._fs.fsType

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
    return False

  @property
  def isRegular(self):
    """Gets whether the file object is a regular file."""
    return False

  @property
  def isSymlink(self):
    """Gets whether the file object is a symbolic link."""
    return False

  @property
  def modeStr(self):
    """Gets a string representing the file object's mode."""
    return "".join(self._modeStr)

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
    return int(ceil(float(self._inode.size) / self._fs.blockSize))

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
    """Gets this file object's parent directory. The root directory's parent is itself."""
    return self._parentDir


  def __init__(self, dirEntry, inode, fs):
    """Constructs a new file object from the specified entry and inode."""
    self._fs = fs
    self._inode = inode
    self._dirEntry = dirEntry
    self._name = ""
    
    if self._dirEntry:
      self._name = self._dirEntry.name
      
    
    # resolve current/up directories
    if self._dirEntry:
      if self._name == ".":
        self._dirEntry = dirEntry.containingDir._dirEntry
      elif self._name == "..":
        self._dirEntry = dirEntry.containingDir.parentDir._dirEntry

    # determine absolute path to file
    if self._dirEntry:
      self._parentDir = self._dirEntry.containingDir
      if self._parentDir.absolutePath == "/":
        parentPath = ""
      else:
        parentPath = self._parentDir.absolutePath
      self._path = "{0}/{1}".format(parentPath, self._dirEntry.name)
    else:
      self._parentDir = self
      self._path = "/"
    
    if not self._parentDir.isDir:
      raise FilesystemError("Invalid parent directory.")
    

    self._modeStr = list("----------")
    if self.isDir:
      self._modeStr[0] = "d"
    if (self._inode.mode & 0x0100) != 0:
      self._modeStr[1] = "r"
    if (self._inode.mode & 0x0080) != 0:
      self._modeStr[2] = "w"
    if (self._inode.mode & 0x0040) != 0:
      self._modeStr[3] = "x"
    if (self._inode.mode & 0x0020) != 0:
      self._modeStr[4] = "r"
    if (self._inode.mode & 0x0010) != 0:
      self._modeStr[5] = "w"
    if (self._inode.mode & 0x0008) != 0:
      self._modeStr[6] = "x"
    if (self._inode.mode & 0x0004) != 0:
      self._modeStr[7] = "r"
    if (self._inode.mode & 0x0002) != 0:
      self._modeStr[8] = "w"
    if (self._inode.mode & 0x0001) != 0:
      self._modeStr[9] = "x"
    


  def __str__(self):
    """Gets a string representation of this file object."""
    return "{0},{1},{2},{3},{4},{5},{6},{7},{8},{9}".format(self.inodeNum,
      self.modeStr, self.numLinks, self.uid, self.gid, self.size, self.timeCreated,
      self.timeAccessed, self.timeModified, self.name)



  def files(self):
    """Generates a list of files in the directory."""
    raise InvalidFileTypeError()


  def getFileAt(self, relativePath):
    """Looks up and returns the file specified by the relative path from this directory. Raises a
    FileNotFoundError if the file object cannot be found."""
    raise InvalidFileTypeError()


  def makeDirectory(self, absolutePath):
    """Creates a new directory in this directory and returns the new file object."""
    raise InvalidFileTypeError()


  def makeRegularFile(self, absolutePath):
    """Creates a new regular file in this directory and returns the new file object."""
    raise InvalidFileTypeError()


  def makeLink(self, absolutePath, linkedFile, isSymbolic):
    """Creates a new link in this directory to the given file object and returns the new file object."""
    raise InvalidFileTypeError()
  
  
  def blocks(self):
    """Generates a list of block data in the file."""
    raise InvalidFileTypeError()
  
