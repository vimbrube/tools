#!/usr/bin/python

"""
sortexternal.py:  Sort files larger than available memory

There are no restrictions on record contents (e.g. record may contain \n or \x00).
Records do not need to end with \n or \x00.
Records may be up to 2^31 bytes long.

Uses ideas from:
  Title: Sorting big files the Python 2.4 way
  Submitter: Nicolas Lehuen
  http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/466302

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2008  Jeremy Mortis
"""

from heapq import heapify, heappop, heappush
from tempfile import gettempdir
import os
import sys
import struct

class VariableLengthRecordFile(file):

    def __init__(self, name, mode, bufsize = -1):
        file.__init__(self, name, mode, bufsize)
        self.headerFormat = "i"
        self.headerLength = struct.calcsize(self.headerFormat)
    
    def readline(self):

        header = self.read(self.headerLength)
        if header == "":
            return (-2, "")

        recordLength = struct.unpack(self.headerFormat, header)[0]
        if recordLength == -1:
            return (-1, "")

        return (1, self.read(recordLength))

    def writeline(self, s):

            
        self.write(struct.pack(self.headerFormat, len(s)))
        self.write(s)

        #sys.stderr.write("wrote: %s %s\n" % (s, self.name))

    def mark(self):
        
        self.write(struct.pack(self.headerFormat, -1))

class SortExternal:

    def __init__(self, buffer_size = 200000, filenum = 16):
        self.buffer_size = buffer_size
        self.tempdir = gettempdir()
        self.chunk = []
        self.chunksize = 0
        
        self.inputChunkFiles = []
        self.outputChunkFiles = []
        
        for i in range(filenum):
            filename = os.path.join(self.tempdir, "sort-" + ('%06i'%i))
            self.inputChunkFiles.append(VariableLengthRecordFile(filename,'w+b',64*1024))
        for i in range(filenum, filenum * 2):
            filename = os.path.join(self.tempdir, "sort-" + ('%06i'%i))
            self.outputChunkFiles.append(VariableLengthRecordFile(filename,'w+b',64*1024))

        self.currOutputFile = -1
        self.chunkDepth = 1


    def __iter__(self):
        return self
    
    def put(self, value):
    
        self.chunk.append(value)
        self.chunksize = self.chunksize + len(value)
        
        if self.chunksize < self.buffer_size:
            return

        self.chunk.sort()
        self.put_chunk(self.chunk)
        self.chunk = []
        self.chunksize = 0

    def put_chunk(self, valueIterator):

        self.currOutputFile = self.currOutputFile + 1
        if self.currOutputFile >= len(self.outputChunkFiles):
            self.currOutputFile = 0
            self.chunkDepth = self.chunkDepth + 1

        #sys.stderr.write("writing chunk %i:%i\n"%(self.currOutputFile, self.chunkDepth))

        for value in valueIterator:
            #sys.stderr.write(value + "\n")
            self.outputChunkFiles[self.currOutputFile].writeline(value)

        self.outputChunkFiles[self.currOutputFile].mark()

    def sort(self):

        if len(self.chunk) > 0:
            self.chunk.sort()
            self.put_chunk(self.chunk)

        while self.chunkDepth > 1:
            self.mergeFiles()

        t = self.inputChunkFiles
        self.inputChunkFiles = self.outputChunkFiles
        self.outputChunkFiles = t
        
        for f in self.inputChunkFiles:
            f.flush()
            f.seek(0)

        self.prepareChunkMerge()

    def prepareChunkMerge(self):
        
        self.chunkHeap = []

        for chunkFile in self.inputChunkFiles:
            status, value = chunkFile.readline()
            if status > 0:
                heappush(self.chunkHeap,(value,chunkFile))

        #sys.stderr.write("prepare: %i\n" % len(self.chunkHeap))

    def mergeFiles(self):

        #sys.stderr.write("merging files\n")

        t = self.inputChunkFiles
        self.inputChunkFiles = self.outputChunkFiles
        self.outputChunkFiles = t

        self.currOutputFile = -1
        self.chunkDepth = 1

        for f in self.outputChunkFiles:
            f.flush()
            f.truncate(0)
            f.seek(0)
        
        for f in self.inputChunkFiles:
            f.flush()
            f.seek(0)

        # for each layer of chunks
        while True:
            #sys.stderr.write("merge layer\n")
            self.prepareChunkMerge()
            if not self.chunkHeap:
                break
            self.put_chunk(self)
        
    def next(self):
        # merges current chunk layer
        
        if not self.chunkHeap:
            raise StopIteration

        value, chunkFile = heappop(self.chunkHeap)

        returnValue = value
        status, value = chunkFile.readline()
        if status > 0:
            heappush(self.chunkHeap, (value, chunkFile))

        #sys.stderr.write("Value: %s\n" % returnValue)

        return returnValue
        

    def cleanup(self):

        for chunkFile in self.inputChunkFiles:
            try:
                chunkFile.close()
                os.remove(chunkFile.name)
            except:
                pass

        for chunkFile in self.outputChunkFiles:
            try:
                chunkFile.close()
                os.remove(chunkFile.name)
            except:
                pass


if __name__ == '__main__':
    import random
    
    s = SortExternal(buffer_size=100000, filenum=32)

    for i in range(100000):
        line = "%08i" % random.randint(0, 99999999)
        s.put(line)
        #sys.stderr.write(">" + repr(line) + "\n")
        sys.stderr.write(line + "\n")

    s.sort()
        
    for line in s:
        #sys.stderr.write("<" + repr(line) + "\n")
        sys.stdout.write(line + "\n")








