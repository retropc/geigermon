import struct
import socket
import util
import json

class Sink:
  def emit(self, cps, cpm, cph, usvh): raise Exception("not implemented")
  def close(self): pass

class FileSink(Sink):
  def __init__(self, filename):
    self.filename = filename

  def emit(self, cps, cpm, cph, usvh):
    util.atomic_write(self.filename, json.dumps({"cps": cps, "cpm": cpm, "cph": cph, "usvh": usvh}).encode("utf8"), fsync=False)

class StdoutSink(Sink):
  def emit(self, cps, cpm, cph, usvh):
    print("cps: %d cpm: %d cph: %d μsv/h: %4.4f" % (cps, cpm, cph, usvh))

class MulticastSink(Sink):
  def __init__(self, target, bind_addr=None, ttl=None):
    self.__s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if ttl is not None:
      self.__s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
    if bind_addr is not None:
      self.__s.bind(bind_addr)
    self.__s.connect(target)
    self.__packet = bytearray(22)
    self.__packet[0:4] = b"GEIG"
    self.__pack = struct.Struct("!IHIIf").pack_into
    self.__count = 0

  def emit(self, cps, cpm, cph, usvh):
    self.__pack(self.__packet, 4, self.__count, cps, cpm, cph, usvh)
    self.__s.send(self.__packet)

    self.__count+=1
    if self.__count == 0xFFFFFFFF:
      self.__count = 0

  def close(self):
    if self.__s is None:
      return
    try:
      self.__s.close()
    finally:
      self.__s = None
