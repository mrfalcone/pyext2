#!/usr/bin/env python
"""
Driver application for interfacing with a filesystem image that can generate
information about the filesystem and enter an interactive shell.
"""
__license__ = "BSD"
__copyright__ = "Copyright 2013, Michael R. Falcone"

import sys
import os
from time import sleep, clock
from threading import Thread
from collections import deque
from ext2 import *


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
  
  def run(self):
    """Prints and updates the wait indicator until done becomes True."""
    lastProgress = None
    indpos = 0
    ind = ["-", "\\", "|", "/"]
    while not self.done:
      if self.maxProgress == 0:
        sys.stdout.write("\r")
        sys.stdout.write(self._msg)
        sys.stdout.write(" ")
        sys.stdout.write(ind[indpos])
        sys.stdout.flush()
        indpos = (indpos + 1) % 4
      else:
        if self.progress != lastProgress:
          sys.stdout.write("\r")
          sys.stdout.write(self._msg)
          sys.stdout.write(" ")
          sys.stdout.write("{0:.0f}%".format(float(self.progress) / self.maxProgress * 100))
          sys.stdout.flush()
          lastProgress = self.progress
      sleep(0.03)
    sys.stdout.write("\r")
    sys.stdout.write(self._msg)
    sys.stdout.write(" Done.")
    sys.stdout.flush()
    print




# ========= FILESYSTEM INFORMATION ==============================================

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



def getGeneralInfo(fs):
  """Gets general information about the filesystem and generates a list of information pairs."""
  pairs = []
  if fs.fsType == "EXT2":
    pairs.append( ("GENERAL INFORMATION", None) )
    pairs.append( ("Ext2 revision", "{0}".format(fs.revision)) )
    pairs.append( ("Total space", "{0:.2f} MB ({1} bytes)".format(float(fs.totalSpace) / 1048576, fs.totalSpace)) )
    pairs.append( ("Used space", "{0:.2f} MB ({1} bytes)".format(float(fs.usedSpace) / 1048576, fs.usedSpace)) )
    pairs.append( ("Block size", "{0} bytes".format(fs.blockSize)) )
    pairs.append( ("Num inodes", "{0}".format(fs.numInodes)) )
    pairs.append( ("Num block groups", "{0}".format(fs.numBlockGroups)) )
    
  else:
    raise FilesystemNotSupportedError()
  
  return pairs



def generateDetailedInfo(fs, showWaitIndicator = True):
  """Scans the filesystem to gather detailed information about space usage and returns
  a list of information pairs."""
  if fs.fsType == "EXT2":
    if showWaitIndicator:
      wait = WaitIndicatorThread("Scanning filesystem...")
      wait.start()
      try:
        report = fs.scanBlockGroups()
      finally:
        wait.done = True
      wait.join()
    else:
      report = fs.scanBlockGroups()
    
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



def generateIntegrityReport(fs, showWaitIndicator = True):
  """Runs an integrity report on the filesystem and returns the results as a list of
  information pairs."""
  if fs.fsType == "EXT2":
    if showWaitIndicator:
      wait = WaitIndicatorThread("Checking filesystem integrity...")
      wait.start()
      try:
        report = fs.checkIntegrity()
      finally:
        wait.done = True
      wait.join()
    else:
      report = fs.checkIntegrity()
    
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
  print "{0}{1}".format("ls [-R,-a,-l]".ljust(sp), "Prints the entries in the working directory.")
  print "{0}{1}".format("".ljust(sp), "Optional flags:")
  print "{0}{1}{2}".format("".ljust(sp), "-R".ljust(rsp), "Lists entries recursively.")
  print "{0}{1}{2}".format("".ljust(sp), "-a".ljust(rsp), "Lists hidden entries.")
  print "{0}{1}{2}".format("".ljust(sp), "-l".ljust(rsp), "Detailed listing.")
  print
  print "{0}{1}".format("cd directory".ljust(sp), "Changes to the specified directory. Treats everything")
  print "{0}{1}".format("".ljust(sp), "following the command as a directory name.")
  print
  print "{0}{1}".format("mkdir name".ljust(sp), "Makes a new directory with the specified name. Treats")
  print "{0}{1}".format("".ljust(sp), "everything following the command as a directory name.")
  print
  print "{0}{1}".format("rm [-r] name".ljust(sp), "Removes the specified file or directory. The optional")
  print "{0}{1}".format("".ljust(sp), "-r flag forces recursive deletion of directories.")
  print
  print "{0}{1}".format("help".ljust(sp), "Prints this message.")
  print "{0}{1}".format("exit".ljust(sp), "Exits shell mode.")
  print


def printDirectory(directory, recursive = False, showAll = False, listMode = False):
  """Prints the specified directory according to the given parameters."""
  if not directory.fsType == "EXT2":
    raise FilesystemNotSupportedError()
  
  q = deque([])
  q.append(directory)
  while len(q) > 0:
    d = q.popleft()
    if recursive:
      print "{0}:".format(d.absolutePath)
    for f in d.files():
      if not showAll and f.name.startswith("."):
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
          q.append(f)
      
      if listMode:
        print "{0} {1} {2} {3} {4} {5} {6} {7}".format(inode, f.modeStr, numLinks,
          uid, gid, size, modified, name)
      else:
        print name
    print




def removeFile(parentDir, rmFile, recursive = False):
  """Removes the specified file or directory from the given directory."""
  
  if recursive and rmFile.isDir:
    
    def getFilesToRemove(rmDir):
      filesToRemove = deque([])
      for f in rmDir.files():
        if f.name == "." or f.name == "..":
          continue
        if f.isDir:
          filesToRemove.extend(getFilesToRemove(f))
        filesToRemove.append((rmDir, f))
      return filesToRemove
    
    for parent,f in getFilesToRemove(rmFile):
      parent.removeFile(f)
  
  parentDir.removeFile(rmFile)




def shell(fs):
  """Enters a command-line shell with commands for operating on the specified filesystem."""
  wd = fs.rootDir
  print "Entered shell mode. Type 'help' for shell commands."
  while True:
    inputline = raw_input(": '{0}' >> ".format(wd.absolutePath)).rstrip().split()
    if len(inputline) == 0:
      continue
    cmd = inputline[0]
    args = inputline[1:]
    if cmd == "help":
      printShellHelp()
    elif cmd == "exit":
      break
    elif cmd == "pwd":
      print wd.absolutePath
    elif cmd == "ls":
      printDirectory(wd, "-R" in args, "-a" in args, "-l" in args)
    elif cmd == "cd":
      if len(args) == 0:
        print "No path specified."
      else:
        path = " ".join(args)
        try:
          if path.startswith("/"):
            cdDir = fs.rootDir.getFileAt(path[1:])
          else:
            cdDir = wd.getFileAt(path)
          if not cdDir.isDir:
            raise FilesystemError("Not a directory.")
          wd = cdDir
        except FileNotFoundError:
          print "The specified directory does not exist."
        except FilesystemError as e:
          print "Error! {0}".format(e)
    elif cmd == "mkdir":
      try:
        path = " ".join(args)
        if path.startswith("/"):
          fs.rootDir.makeDirectory(path[1:])
        else:
          wd.makeDirectory(path)
      except FilesystemError as e:
        print "Error! {0}".format(e)
    elif cmd == "rm":
      if len(args) == 0:
        print "No path specified."
      else:
        recursive = (args[0] == "-r")
        if args[0][0] == "-":
          args = args[1:]
        try:
          path = " ".join(args)
          if len(path) == 0:
            print "No path specified."
          else:
            rmFile = wd.getFileAt(path)
            removeFile(wd, rmFile, recursive)
        except FileNotFoundError:
          print "The specified file or directory does not exist."
        except FilesystemError as e:
          print "Error! {0}".format(e)
    else:
      print "Command not recognized."






# ========= FILE TRANSFER ==============================================

def fetchFile(fs, srcFilename, destDirectory, showWaitIndicator = True):
  """Fetches the specified file from the filesystem image and places it in
  the local destination directory."""
  if not fs.fsType == "EXT2":
    raise FilesystemNotSupportedError()
  
  filesToFetch = []
  if srcFilename.endswith("/*"):
    directory = fs.rootDir.getFileAt(srcFilename[:-1])
    destDirectory = "{0}/{1}".format(destDirectory, directory.name)
    for f in directory.files():
      if f.isRegular:
        filesToFetch.append(f.absolutePath)
  else:
    filesToFetch.append(srcFilename)
  
  if len(filesToFetch) == 0:
    raise Exception("No files exist in the specified directory.")
  
  if not os.path.exists(destDirectory):
    print "Making directory {0}".format(destDirectory)
    os.mkdir(destDirectory)
    
  for srcFilename in filesToFetch:
    try:
      srcFile = fs.rootDir.getFileAt(srcFilename)
    except FileNotFoundError:
      raise Exception("The source file cannot be found on the filesystem image.")
    
    if not srcFile.isRegular:
      raise Exception("The source path does not point to a regular file.")
    
    srcPath = "{0}/{1}".format(destDirectory, srcFile.name)
    try:
      outFile = open(srcPath, "wb")
    except:
      raise Exception("Cannot access specified destination directory.")
    
    def __read(wait = None):
      readCount = 0
      with outFile:
        for block in srcFile.blocks():
          outFile.write(block)
          readCount += len(block)
          if wait:
            wait.progress += len(block)
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
    
    os.utime(srcPath, (srcFile.timeAccessedEpoch, srcFile.timeModifiedEpoch))
    
  print



def pushFile(fs, srcFilename, destDirectory, showWaitIndicator = True):
  """Pushes the specified local file to the specified destination directory on the filesystem image."""
  if not fs.fsType == "EXT2":
    raise FilesystemNotSupportedError()
  
  destFilename = srcFilename[srcFilename.rfind("/")+1:]
  
  try:
    directory = fs.rootDir.getFileAt(destDirectory)
  except FileNotFoundError:
    raise FilesystemError("Destination directory does not exist.")

  if not os.path.exists(srcFilename):
    raise FilesystemError("Source file does not exist.")
  
  if not os.path.isfile(srcFilename):
    raise FilesystemError("Source is not a file.")
  
  uid = os.stat(srcFilename).st_uid
  gid = os.stat(srcFilename).st_gid
  creationTime = int(os.stat(srcFilename).st_birthtime)
  modTime = int(os.stat(srcFilename).st_mtime)
  accessTime = int(os.stat(srcFilename).st_atime)
  newFile = directory.makeRegularFile(destFilename, uid, gid, creationTime, modTime, accessTime)

  inFile = open(srcFilename, "rb")
  def __write(wait = None):
    written = 0
    with inFile:
      inFile.seek(0, 2)
      length = inFile.tell()
      if wait:
        wait.maxProgress = length
        wait.start()
      inFile.seek(0)
      while written < length:
        byteString = inFile.read(fs.blockSize)
        newFile.write(byteString)
        written += len(byteString)
        if wait:
          wait.progress += len(byteString)
    return written

  if showWaitIndicator:
    wait = WaitIndicatorThread("Pushing {0} to {1}...".format(srcFilename, newFile.absolutePath))
    try:
      transferStart = clock()
      written = __write(wait)
      transferTime = clock() - transferStart
    finally:
      wait.done = True
    wait.join()
  else:
    transferStart = clock()
    written = __write()
    transferTime = clock() - transferStart

  mbps = float(written) / (1024*1024) / transferTime
  print "Wrote {0} bytes at {1:.2f} MB/sec.".format(written, mbps)

  





# ========= MAIN APPLICATION ==============================================

def printHelp():
  """Prints the help screen for the main application, with usage and command options."""
  sp = 26
  print "Usage: {0} image_file options".format(sys.argv[0])
  print
  print "Options:"
  print "{0}{1}".format("-s".ljust(sp), "Enters shell mode.")
  print "{0}{1}".format("-h".ljust(sp), "Prints this message and exits.")
  print "{0}{1}".format("-f filepath [hostdir]".ljust(sp), "Fetches the specified file from the filesystem")
  print "{0}{1}".format("".ljust(sp), "into the optional host directory. If no directory")
  print "{0}{1}".format("".ljust(sp), "is specified, defaults to the current directory.")
  print
  print "{0}{1}".format("-p hostfile destpath".ljust(sp), "Pushes the specified host file into the specified")
  print "{0}{1}".format("".ljust(sp), "directory on the filesystem.")
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


def run(args, fs):
  """Runs the program on the specified filesystem with the given command line arguments."""
  showHelp = ("-h" in args)
  enterShell = ("-s" in args)
  showGeneralInfo = ("-i" in args)
  showDetailedInfo = ("-d" in args)
  showIntegrityCheck = ("-c" in args)
  suppressIndicator = ("-w" in args)
  fetch = ("-f" in args)
  push = ("-p" in args)
  
  if showHelp or not (showGeneralInfo or enterShell or showDetailedInfo or showIntegrityCheck or fetch or push):
    printHelp()
    quit()
  
  else:
    info = []
    if showGeneralInfo:
      info.extend(getGeneralInfo(fs))
    if showDetailedInfo:
      info.extend(generateDetailedInfo(fs, not suppressIndicator))
    if showIntegrityCheck:
      info.extend(generateIntegrityReport(fs, not suppressIndicator))
    if len(info) > 0:
      printInfoPairs(info)
      
    if push:
      srcNameIndex = args.index("-p") + 1
      destNameIndex = srcNameIndex + 1
      if len(args) <= srcNameIndex:
        print "Error! No source file specified to push."
      elif len(args) <= destNameIndex:
        print "Error! No destination directory specified for pushed file."
      else:
        try:
          pushFile(fs, args[srcNameIndex], args[destNameIndex], not suppressIndicator)
        except FilesystemError as e:
          print "Error! {0}".format(e)
    
    if fetch:
      srcNameIndex = args.index("-f") + 1
      destNameIndex = srcNameIndex + 1
      if len(args) <= srcNameIndex:
        print "Error! No source file specified to fetch."
      else:
        if len(args) <= destNameIndex:
          destDirectory = "."
        elif args[destNameIndex][0] == "-":
          destDirectory = "."
        else:
          destDirectory = args[destNameIndex]
        try:
          fetchFile(fs, args[srcNameIndex], destDirectory, not suppressIndicator)
        except FilesystemError as e:
          print "Error! {0}".format(e)
    
    if enterShell:
      shell(fs)



def main():
  """Main entry point of the application."""
  fs = None
  args = list(sys.argv)
  if len(args) < 3:
    printHelp()
    quit()
  elif args[1][0] == "-":
    printHelp()
    quit()
  else:
    filename = args[1]
    del args[0:1]
    try:
      fs = Ext2Filesystem.fromImageFile(filename)
      with fs:
        run(args, fs)
    except FilesystemError as e:
      print "Error! {0}".format(e)
      print
      quit()



main()
