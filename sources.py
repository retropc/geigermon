import gmc300eplus
import struct
import socket

IP_ADD_SOURCE_MEMBERSHIP = 39

GMC300EPlusSource = gmc300eplus.GMC300EPlus

class Source:
  def __iter__(self): raise Exception("not implemented")
  def close(self): pass

class GeigerSource(Source):
  def __init__(self, g):
    self.__g = g

  def __iter__(self):
    return iter(self.__g)

  def close(self):
    if self.__g is None:
      return
    try:
      self.__g.close()
    finally:
      self.__g = None

class MulticastSource(Source):
  def __init__(self, bind_addr, target, source_addr):
    self.__s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.__s.bind(target)
    self.__s.setsockopt(socket.IPPROTO_IP, IP_ADD_SOURCE_MEMBERSHIP, socket.inet_aton(target[0]) + socket.inet_aton(bind_addr) + socket.inet_aton(source_addr))

  def __iter__(self):
    p = struct.Struct("!IHIIf").unpack_from
    b = bytearray(22 + 1)
    while True:
      if self.__s.recv_into(b) != 22 or b[:4] != b"GEIG":
        raise Exception("invalid data: %r" % b)
      yield p(b, 4)[1:]

  def close(self):
    if self.__s is None:
      return
    try:
      self.__s.close()
    finally:
      self.__s = None
