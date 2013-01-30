#!/usr/bin/env python
"""
Defines exceptions raised by the ext2 module.
"""
__license__ = "BSD"
__copyright__ = "Copyright 2013, Michael R. Falcone"


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

