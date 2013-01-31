#!/usr/bin/env python
"""
Defines classes for accessing the device on which the filesystem resides.
"""
__license__ = "BSD"
__copyright__ = "Copyright 2013, Michael R. Falcone"


from os import fsync


class _DeviceFromFile(object):
  """Represents a device from a filesystem image file."""
  
  @property
  def isMounted(self):
    """Returns whether the device is currently mounted."""
    return (not self._imageFile is None)
  
  def __init__(self, filename):
    """Constructs a new device object from the specified file."""
    self._imageFilename = filename
    self._imageFile = None
  
  def mount(self):
    """Opens reading/writing from/to the device."""
    self._imageFile = open(self._imageFilename, "r+b")
  
  def unmount(self):
    """Closes reading/writing from/to the device."""
    if self._imageFile:
      self._imageFile.flush()
      fsync(self._imageFile.fileno())
      self._imageFile.close()
    self._imageFile = None

  def read(self, position, size):
    """Reads a byte string of the specified size from the specified position."""
    assert self.isMounted, "Device not mounted."
    self._imageFile.seek(position)
    return self._imageFile.read(size)
  
  def write(self, position, byteString):
    """Writes the specified byte string to the specified position."""
    self._imageFile.seek(position)
    # TODO self._imageFile.write(byteString)
    self._imageFile.flush()