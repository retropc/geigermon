import mmap
import os
import struct

class PointFile:
  PACK = struct.Struct("@B").pack
  UNPACK = struct.Struct("@B").unpack

  def __init__(self, filename):
    self.__fd = os.open(filename, os.O_CREAT|os.O_RDWR|os.O_CLOEXEC)
    try:
      os.truncate(self.__fd, 43200)
      self.__m = mmap.mmap(self.__fd, 43200)
    except:
      os.close(self.__fd)
      raise

  def add_point(self, ts, data):
    m = self.__m

    offset = (ts % 86400) // 2
    if data < 0:
      raise Exception()
    data = min(15, data + 1)

    prev_value = m[offset]
    if ts % 2 == 0:
      value = (prev_value & 0xf0) | data
    else:
      value = (prev_value & 0x0f) | (data << 4)

    m[offset] = value

  def close(self):
    self.__m.close()
    if self.__fd is not None:
      fd, self.__fd = self.__fd, None
      os.close(fd)
