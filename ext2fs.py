#!/usr/bin/env python

__author__ = "Michael R. Falcone"
__version__ = "0.1"

"""
Driver application for interfacing with an ext2 disk image.
"""

import threading
import sys
from diskmod import *


# PROGRESS INDICATOR THREAD -------------------------------------
class ProgressIndicatorThread(threading.Thread):
  """Shows a progress indicator for the current disk action."""
  _length = 20
  _character = "-"
  
  def __init__(self, disk):
    threading.Thread.__init__(self)
    self._disk = disk
  
  def __printIndicator(self, progressPercent):
    numMarkers = progressPercent / (100 / self._length)
    sys.stdout.write("\r > [")
    for i in range(numMarkers):
      sys.stdout.write(self._character)
    for i in range(self._length - numMarkers):
      sys.stdout.write(" ")
    sys.stdout.write("] {0}%".format(progressPercent))
    sys.stdout.flush()
  
  def run(self):
    self._disk.resetActionProgress()
    currentProgress = 0
    while currentProgress < 100:
      self.__printIndicator(currentProgress)
      currentProgress = self._disk.actionProgress
    self.__printIndicator(100)
    print
# ----------------------------------------------------------



# MAIN APPLICATION METHODS --------------------------------------------

def printPairs(pairs):
  """Prints the strings stored in a list of pairs, justified."""
  maxLeftLen = 0
  for p in pairs:
    if len(p[0]) > maxLeftLen:
      maxLeftLen = len(p[0])
  for p in pairs:
    if p[1]:
      print "{0}{1}".format(p[0].ljust(maxLeftLen+5, "."), p[1])
    else:
      print p[0]


def getDiskInfo(disk):
  """Gets general information about the disk and generates a list of information pairs."""
  pairs = []
  pairs.append( ("Ext2 revision", "{0}".format(disk.revision)) )
  pairs.append( ("Total space", "{0:.2f} MB ({1} bytes)".format(float(disk.totalSpace) / 1048576, disk.totalSpace)) )
  pairs.append( ("Used space", "{0:.2f} MB ({1} bytes)".format(float(disk.usedSpace) / 1048576, disk.usedSpace)) )
  pairs.append( ("Block size", "{0} bytes".format(disk.blockSize)) )
  pairs.append( ("Num inodes", "{0}".format(disk.numInodes)) )
  pairs.append( ("Num block groups", "{0}".format(disk.numBlockGroups)) )
  return pairs



def getBlockGroupInfo(disk):
  """Gets information about all the disk's block groups and generates a list
  of information pairs."""
  bgroupReport = disk.scanBlockGroups()
  pairs = []
  pairs.append( ("Num files", "{0}".format(bgroupReport.numFiles)) )
  pairs.append( ("Num directories", "{0}".format(bgroupReport.numDirs)) )
  return pairs


def printDirectory(dir, showAll = False, verbose = False):
  """Prints the specified directory according to the given parameters."""
  print "{0}:".format(dir.name)
  for f in dir.listContents():
    if not showAll and f.name[0] == ".":
      continue
    
    inode = "{0}".format(f.inodeNum).rjust(10)
    numLinks = "{0}".format(f.numLinks).rjust(3)
    uid = "{0}".format(f.uid).rjust(5)
    gid = "{0}".format(f.gid).rjust(5)
    size = "{0}".format(f.size).rjust(10)
    modified = f.timeModified.ljust(14)
    
    if verbose:
      print "{0} {1} {2} {3} {4} {5} {6} {7}".format(inode, f.modeStr, numLinks,
        uid, gid, size, modified, f.name)
    else:
      print f.name



def main():
  """Main entry point."""
  if len(sys.argv) < 2:
    print("Usage: {0} disk_image_file".format(sys.argv[0]))
    print
    quit()
  
  diskFilename = sys.argv[1]
  
  
  disk = Ext2Disk(diskFilename)
  #info = getDiskInfo(disk)
  #info = getBlockGroupInfo(disk)
  #printPairs(info)
  
  root = disk.rootDir
  printDirectory(root)


main()
quit()



try:
  disk = Ext2Disk(diskFilename)
except InvalidImageFormatError as e:
  print "Error! The disk image is not formatted properly."
  print
  quit()
except Exception as e:
  print "Error! The specified disk image could not be loaded."
  quit()
  
print "Loaded ext2 image from {0}.".format(diskFilename)
print

quit()
print "Checking filesystem integrity..."
indicator = ProgressIndicatorThread(disk)
indicator.start()
integrityReport = disk.generateIntegrityReport()
indicator.join()
print
print "INTEGRITY REPORT"
print "================"
print integrityReport
print
