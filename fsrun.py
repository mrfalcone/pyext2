#!/usr/bin/env python

__author__ = "Michael R. Falcone"
__version__ = "0.1"

"""
Driver application for interfacing with a filesystem image that can generate
information about the filesystem and enter an interactive shell.
"""

import sys
from threading import Thread
from Queue import Queue
from ext2mod import *


class FilesystemNotSupportedError(Exception):
  """Thrown when the image's filesystem type is not supported."""
  pass


class WaitIndicatorThread(Thread):
  """Shows a wait indicator for the current action."""
  done = False
  
  def __init__(self, msg):
    Thread.__init__(self)
    self._msg = msg
    self._pos = 0
  
  def run(self):
    while not self.done:
      sys.stdout.write(self._msg)
      sys.stdout.write(" ")
      if self._pos == 0:
        sys.stdout.write("-")
      elif self._pos == 1:
        sys.stdout.write("\\")
      elif self._pos == 2:
        sys.stdout.write("|")
      else:
        sys.stdout.write("/")
      sys.stdout.flush()
      sys.stdout.write("\r")
      self._pos = (self._pos + 1) % 3
    sys.stdout.write(self._msg)
    sys.stdout.write(" Done.")
    sys.stdout.flush()
    print




# ========= DISK INFORMATION ==============================================

def printInfoPairs(pairs):
  """Prints the info strings stored in a list of pairs, justified."""
  maxLeftLen = 0
  for p in pairs:
    if len(p[0]) > maxLeftLen:
      maxLeftLen = len(p[0])
  for p in pairs:
    if p[1]:
      print "{0}{1}".format(p[0].ljust(maxLeftLen+5, "."), p[1])
    else:
      print
      print p[0]
  print



def getGeneralInfo(disk):
  """Gets general information about the disk and generates a list of information pairs."""
  pairs = []
  if disk.fsType == "EXT2":
    pairs.append( ("GENERAL INFORMATION", None) )
    pairs.append( ("Ext2 revision", "{0}".format(disk.revision)) )
    pairs.append( ("Total space", "{0:.2f} MB ({1} bytes)".format(float(disk.totalSpace) / 1048576, disk.totalSpace)) )
    pairs.append( ("Used space", "{0:.2f} MB ({1} bytes)".format(float(disk.usedSpace) / 1048576, disk.usedSpace)) )
    pairs.append( ("Block size", "{0} bytes".format(disk.blockSize)) )
    pairs.append( ("Num inodes", "{0}".format(disk.numInodes)) )
    pairs.append( ("Num block groups", "{0}".format(disk.numBlockGroups)) )
    
  else:
    raise FilesystemNotSupportedError()
  
  return pairs



def generateDetailedInfo(disk):
  """Scans the disk to gather detailed information about space usage and returns
  a list of information pairs."""
  if disk.fsType == "EXT2":
    wait = WaitIndicatorThread("Scanning block groups...")
    wait.start()
    report = disk.scanBlockGroups()
    wait.done = True
    wait.join()
    pairs = []
    pairs.append( ("DETAILED STORAGE INFORMATION", None) )
    pairs.append( ("Num files", "{0}".format(report.numFiles)) )
    pairs.append( ("Num directories", "{0}".format(report.numDirs)) )
    
  else:
    raise FilesystemNotSupportedError()
  
  return pairs



def generateIntegrityReport(disk):
  """Runs an integrity report on the disk and returns the results as a list of
  information pairs."""
  if disk.fsType == "EXT2":
    wait = WaitIndicatorThread("Checking disk integrity...")
    wait.start()
    report = disk.checkIntegrity()
    wait.done = True
    wait.join()
    
    pairs = []
    pairs.append( ("INTEGRITY REPORT", None) )
    pairs.append( ("Contains magic number", "{0}".format(report.hasMagicNumber)) )
    
  else:
    raise FilesystemNotSupportedError()
  
  return pairs






# ========= SHELL COMMANDS ==============================================

def printShellHelp():
  """Prints a help screen for the shell, listing supported commands."""
  sp = 26
  rsp = 4
  print "Supported commands:"
  print "{0}{1}".format("pwd".ljust(sp), "Prints the current working directory.")
  print "{0}{1}".format("ls [-R,-a,-v]".ljust(sp), "Prints the entries in the working directory.")
  print "{0}{1}".format("".ljust(sp), "Optional flags:")
  print "{0}{1}{2}".format("".ljust(sp), "-R".ljust(rsp), "Lists entries recursively.")
  print "{0}{1}{2}".format("".ljust(sp), "-a".ljust(rsp), "Lists hidden entries.")
  print "{0}{1}{2}".format("".ljust(sp), "-v".ljust(rsp), "Verbose listing.")
  print
  print "{0}{1}".format("cd directory".ljust(sp), "Changes to the specified directory. Treats everything")
  print "{0}{1}".format("".ljust(sp), "following the command as a directory name.")
  print
  print "{0}{1}".format("help".ljust(sp), "Prints this message.")
  print "{0}{1}".format("exit".ljust(sp), "Exits shell mode.")
  print


def printDirectory(directory, recursive = False, showAll = False, verbose = False):
  """Prints the specified directory according to the given parameters."""
  if not directory.fsType == "EXT2":
    raise FilesystemNotSupportedError()
  
  q = Queue()
  q.put(directory)
  while not q.empty():
    dir = q.get()
    if recursive:
      print "{0}:".format(dir.absolutePath)
    for f in dir.listContents():
      if not showAll and f.name[0] == ".":
        continue
      
      inode = "{0}".format(f.inodeNum).rjust(7)
      numLinks = "{0}".format(f.numLinks).rjust(3)
      uid = "{0}".format(f.uid).rjust(5)
      gid = "{0}".format(f.gid).rjust(5)
      size = "{0}".format(f.size).rjust(10)
      modified = f.timeModified.ljust(17)
      name = f.name
      if f.isDir and f.name != "." and f.name != "..":
        name = "{0}/".format(f.name)
        if recursive:
          q.put(f)
      
      if verbose:
        print "{0} {1} {2} {3} {4} {5} {6} {7}".format(inode, f.modeStr, numLinks,
          uid, gid, size, modified, name)
      else:
        print name
    print





def shell(disk):
  """Enters a command-line shell with commands for operating on the specified disk."""
  wd = disk.rootDir
  print "Entered shell mode. Type 'help' for shell commands."
  while True:
    input = raw_input(": '{0}' >> ".format(wd.absolutePath)).rstrip().split()
    if len(input) == 0:
      continue
    cmd = input[0]
    args = input[1:]
    if cmd == "help":
      printShellHelp()
    elif cmd == "exit":
      break
    elif cmd == "pwd":
      print wd.absolutePath
    elif cmd == "ls":
      printDirectory(wd, "-R" in args, "-a" in args, "-v" in args)
    elif cmd == "cd":
      if len(args) == 0:
        print "No path specified."
      else:
        path = " ".join(args)
        if not path.startswith("/"):
          path = "{0}/{1}".format(wd.absolutePath, path)
        try:
          f = disk.getFile(path)
          if f.isDir:
            wd = f
          else:
            print "Not a directory."
        except FileNotFoundError:
          print "The specified directory does not exist."
    else:
      print "Command not recognized."






# ========= MAIN APPLICATION ==============================================

def printHelp():
  sp = 26
  print "Usage: {0} options disk_image_file".format(sys.argv[0])
  print
  print "Options:"
  print "{0}{1}".format("-s".ljust(sp), "Enters shell mode.")
  print "{0}{1}".format("-h".ljust(sp), "Prints this message and exits.")
  print "{0}{1}".format("-f filepath hostdir".ljust(sp), "Fetches the specified file from the filesystem")
  print "{0}{1}".format("".ljust(sp), "into the specified host directory.")
  print
  print "{0}{1}".format("-i".ljust(sp), "Prints general information about the filesystem.")
  print "{0}{1}".format("-d".ljust(sp), "Scans the filesystem and prints detailed space")
  print "{0}{1}".format("".ljust(sp), "space usage information.")
  print
  print "{0}{1}".format("-c".ljust(sp), "Checks the filesystem's integrity and prints an")
  print "{0}{1}".format("".ljust(sp), "integrity report, including general and detailed")
  print "{0}{1}".format("".ljust(sp), "information.")
  print


def run(args, disk):
  """Runs the program on the specified disk with the given command line arguments."""
  showHelp = False
  enterShell = False
  showGeneralInfo = False
  showDetailedInfo = False
  showIntegrityCheck = False
  
  for a in args:
    if a == "-h":
      showHelp = True
    if a == "-s":
      enterShell = True
    if a == "-i":
      showGeneralInfo = True
    if a == "-d":
      showDetailedInfo = True
    if a == "-c":
      showIntegrityCheck = True
      showGeneralInfo = True
      showDetailedInfo = True
  
  if showHelp:
    printHelp()
    quit()
  
  if disk is None:
    print "Error! No disk image specified."
  elif not (showGeneralInfo or enterShell or showDetailedInfo or showIntegrityCheck):
    printHelp()
  else:
    info = []
    if showGeneralInfo:
      info.extend(getGeneralInfo(disk))
    if showDetailedInfo:
      info.extend(generateDetailedInfo(disk))
    if showIntegrityCheck:
      info.extend(generateIntegrityReport(disk))
    if len(info) > 0:
      printInfoPairs(info)
    if enterShell:
      shell(disk)



def main():
  """Main entry point of the application."""
  args = list(sys.argv)
  if len(args) < 2:
    printHelp()
    quit()
  else:
    del args[0]
    if args[-1][0] == "-":
      disk = None
    else:
      try:
        disk = Ext2Disk(args[-1])
      except InvalidImageFormatError as e:
        print "Error! The specified disk image is not formatted properly."
        print
        quit()
      except Exception as e:
        print "Error! The specified disk image could not be loaded."
        quit()
      del args[-1]
    
    run(args, disk)


main()
