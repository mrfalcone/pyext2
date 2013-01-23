#!/usr/bin/env python
"""
Driver application for interfacing with a filesystem image that can generate
information about the filesystem and enter an interactive shell.
"""
__license__ = "BSD"
__copyright__ = "Copyright 2013, Michael R. Falcone"

import sys
from time import clock
from threading import Thread
from Queue import Queue
from ext2mod import *



class FilesystemNotSupportedError(Exception):
  """Thrown when the image's filesystem type is not supported."""
  pass


class WaitIndicatorThread(Thread):
  """Shows a wait indicator for the current action. If maxProgress is set then a
  percentage towards completion is shown instead."""
  done = False
  progress = 0
  maxProgress = 0
  
  def __init__(self, msg):
    Thread.__init__(self)
    self._msg = msg
    self._pos = 0
  
  def run(self):
    while not self.done:
      sys.stdout.write(self._msg)
      sys.stdout.write(" ")
      if self.maxProgress == 0:
        if self._pos == 0:
          sys.stdout.write("-")
        elif self._pos == 1:
          sys.stdout.write("\\")
        elif self._pos == 2:
          sys.stdout.write("|")
        else:
          sys.stdout.write("/")
      else:
        sys.stdout.write("{0:.0f}%".format(float(self.progress) / self.maxProgress * 100))
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
      if isinstance(p[1], list):
        print "{0}:".format(p[0])
        for message in p[1]:
          print "- {0}".format(message)
      else:
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



def generateDetailedInfo(disk, showWaitIndicator = True):
  """Scans the disk to gather detailed information about space usage and returns
  a list of information pairs."""
  if disk.fsType == "EXT2":
    if showWaitIndicator:
      wait = WaitIndicatorThread("Scanning filesystem...")
      wait.start()
      try:
        report = disk.scanBlockGroups()
      finally:
        wait.done = True
      wait.join()
    else:
      report = disk.scanBlockGroups()
    
    pairs = []
    pairs.append( ("DETAILED STORAGE INFORMATION", None) )
    pairs.append( ("Num regular files", "{0}".format(report.numRegFiles)) )
    pairs.append( ("Num directories", "{0}".format(report.numDirs)) )
    pairs.append( ("Num symlinks", "{0}".format(report.numSymlinks)) )
    pairs.append( ("Space used for files", "{0} bytes".format("-")) )
    pairs.append( ("Space unused for files", "{0} bytes".format("-")) )
    for i,groupReport in enumerate(report.groupReports):
      groupInfo = []
      groupInfo.append("Free inodes: {0}".format(groupReport.numFreeInodes))
      groupInfo.append("Free blocks: {0}".format(groupReport.numFreeBlocks))
      pairs.append( ("Block group {0}".format(i), groupInfo) )
    
  else:
    raise FilesystemNotSupportedError()
  
  return pairs



def generateIntegrityReport(disk, showWaitIndicator = True):
  """Runs an integrity report on the disk and returns the results as a list of
  information pairs."""
  if disk.fsType == "EXT2":
    if showWaitIndicator:
      wait = WaitIndicatorThread("Checking disk integrity...")
      wait.start()
      try:
        report = disk.checkIntegrity()
      finally:
        wait.done = True
      wait.join()
    else:
      report = disk.checkIntegrity()
    
    pairs = []
    pairs.append( ("INTEGRITY REPORT", None) )
    pairs.append( ("Contains magic number", "{0}".format(report.hasMagicNumber)) )
    pairs.append( ("Num superblock copies", "{0}".format(report.numSuperblockCopies)) )
    pairs.append( ("Superblock copy locations", "Block groups {0}".format(",".join(map(str,report.copyLocations)))) )
    messages = list(report.messages)
    if len(messages) == 0:
      messages.append("Integrity check passed.")
    pairs.append( ("Diagnostic messages", messages) )
    
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






# ========= FILE TRANSFER ==============================================

def fetchFile(disk, srcFilename, destDirectory, showWaitIndicator = True):
  """Fetches the specified file from the disk image filesystem and places it in
  the local destination directory."""
  if not disk.fsType == "EXT2":
    raise FilesystemNotSupportedError()
  
  try:
    srcFile = disk.getFile(srcFilename)
  except FileNotFoundError:
    raise Exception("The source file cannot be found on the filesystem image.")
  
  if not srcFile.isRegular:
    raise Exception("The source path does not point to a regular file.")
  
  try:
    outFile = open("{0}/{1}".format(destDirectory, srcFile.name), "wb")
  except:
    raise Exception("Cannot access specified destination directory.")
  
  def __read(wait = None):
    readCount = 0
    with outFile:
      byteBuffer = srcFile.read()
      while len(byteBuffer) > 0:
        outFile.write(byteBuffer)
        readCount += len(byteBuffer)
        if wait:
          wait.progress += len(byteBuffer)
        byteBuffer = srcFile.read()
    return readCount
  
  if showWaitIndicator:
    wait = WaitIndicatorThread("Fetching {0}...".format(srcFilename))
    wait.maxProgress = srcFile.size
    wait.start()
    try:
      transferStart = clock()
      readCount = __read(wait)
      transferTime = clock() - transferStart
    finally:
      wait.done = True
    wait.join()
  else:
    transferStart = clock()
    readCount = __read()
    transferTime = clock() - transferStart
  
  mbps = float(readCount) / (1024*1024) / transferTime
  print "Read {0} bytes at {1:.2f} MB/sec.".format(readCount, mbps)
  print





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
  print "{0}{1}".format("".ljust(sp), "usage information.")
  print
  print "{0}{1}".format("-c".ljust(sp), "Checks the filesystem's integrity and prints a")
  print "{0}{1}".format("".ljust(sp), "detailed integrity report.")
  print
  print "{0}{1}".format("-w".ljust(sp), "Suppress the wait indicator that is typically")
  print "{0}{1}".format("".ljust(sp), "shown for long operations. This is useful when")
  print "{0}{1}".format("".ljust(sp), "redirecting the output of this program.")
  print


def run(args, disk):
  """Runs the program on the specified disk with the given command line arguments."""
  showHelp = ("-h" in args)
  enterShell = ("-s" in args)
  showGeneralInfo = ("-i" in args)
  showDetailedInfo = ("-d" in args)
  showIntegrityCheck = ("-c" in args)
  suppressIndicator = ("-w" in args)
  fetch = ("-f" in args)
  
  if showHelp:
    printHelp()
    quit()
  
  if disk is None:
    print "Error! No disk image specified."
  elif not (showGeneralInfo or enterShell or showDetailedInfo or showIntegrityCheck or fetch):
    printHelp()
  else:
    info = []
    if showGeneralInfo:
      info.extend(getGeneralInfo(disk))
    if showDetailedInfo:
      info.extend(generateDetailedInfo(disk, not suppressIndicator))
    if showIntegrityCheck:
      info.extend(generateIntegrityReport(disk, not suppressIndicator))
    if len(info) > 0:
      printInfoPairs(info)
    if fetch:
      srcNameIndex = args.index("-f") + 1
      destNameIndex = srcNameIndex + 1
      if len(args) <= srcNameIndex:
        print "Error! No source file specified to fetch."
      elif len(args) <= destNameIndex:
        print "Error! No destination directory specified for fetched file."
      else:
        try:
          fetchFile(disk, args[srcNameIndex], args[destNameIndex], not suppressIndicator)
        except Exception as e:
          print "Error! {0}".format(e)
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
