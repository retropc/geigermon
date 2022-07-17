import struct
import socket
import util
import json
import time
import datetime
import os
import pointfile

class Sink:
  def emit(self, cps, cpm, cph, usvh): raise Exception("not implemented")
  def close(self): pass

class FileSink(Sink):
  def __init__(self, filename):
    self.filename = filename

  def emit(self, cps, cpm, cph, usvh):
    util.atomic_write(self.filename, json.dumps({"cps": cps, "cpm": cpm, "cph": cph, "usvh": usvh}).encode("utf8"), fsync=False)

class PointFileSink(Sink):
  def __init__(self, path):
    self.__path = path
    os.makedirs(path, exist_ok=True)

    self.__last_ts = -1
    self.__last_v = 0
    self.__last_f = None
    self.__last_d = None

  def emit(self, cps, cpm, cph, usvh):
    ts = int(time.time())
    if ts == self.__last_ts:
      self.__last_v += cps
    else:
      self.__last_ts = ts
      self.__last_v = cps

    self.__write_point(ts, self.__last_v)

  def __write_point(self, ts, v):
    self.__get_file(ts).add_point(ts, v)

  def __get_file(self, ts):
    date = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).date()
    if date != self.__last_d:
      if self.__last_f is not None:
        self.__last_f.close()
      self.__last_f = pointfile.PointFile(os.path.join(self.__path, date.strftime("%Y-%m-%d.pf")))
      self.__last_d = date
    return self.__last_f

  def close(self):
    if self.__last_f is not None:
      if self.__last_ts != -1:
        self.__write_point(self.__last_ts, self.__last_v)
        self.__last_ts = -1
      self.__last_f.close()
      self.__last_f = None

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
