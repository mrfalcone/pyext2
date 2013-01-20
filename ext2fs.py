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



# MAIN SCRIPT METHODS --------------------------------------------

def printTuples(tuples):
  maxLeftLen = 0
  for t in tuples:
    if len(t[0]) > maxLeftLen:
      maxLeftLen = len(t[0])
  for t in tuples:
    if t[1]:
      print "{0}{1}".format(t[0].ljust(maxLeftLen+5, "."), t[1])
    else:
      print t[0]



def getDiskInfo(disk):
  tuples = []
  tuples.append( ("Ext2 revision", "{0}".format(disk.revision)) )
  tuples.append( ("Total space", "{0:.2f} MB ({1} bytes)".format(float(disk.totalSpace) / 1048576, disk.totalSpace)) )
  tuples.append( ("Used space", "{0:.2f} MB ({1} bytes)".format(float(disk.usedSpace) / 1048576, disk.usedSpace)) )
  tuples.append( ("Block size", "{0} bytes".format(disk.blockSize)) )
  tuples.append( ("Num inodes", "{0}".format(disk.numInodes)) )
  tuples.append( ("Num block groups", "{0}".format(disk.numBlockGroups)) )
  return tuples



def getBlockGroupInfo(disk):
  bgroupReport = disk.scanBlockGroups()
  tuples = []
  tuples.append( ("Num files", "{0}".format(bgroupReport.numFiles)) )
  tuples.append( ("Num directories", "{0}".format(bgroupReport.numDirs)) )
  return tuples







if len(sys.argv) < 2:
  print("Usage: {0} disk_image_file".format(sys.argv[0]))
  print
  quit()


diskFilename = sys.argv[1]


disk = Ext2Disk(diskFilename)
#info = getDiskInfo(disk)

info = getBlockGroupInfo(disk)
#printTuples(info)

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
