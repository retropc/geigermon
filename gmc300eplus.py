import termios
import os
import time
import struct
import util

# http://www.gqelectronicsllc.com/forum/topic.asp?TOPIC_ID=4447 and https://sourceforge.net/projects/gqgmc/files/gqgmc/ (odt file)
#   0                   5             10               15               20                  25               30               35                  40                  45               50               55                60
# b"\x00\x01\x01\x02\x1f\x00\x00d\x00<\x14\xae\xc7>\x00\xf0\x14\xae\xc7?\x03\xe8\x00\x00\xd0@\x00\x00\x00\x00?\x00\x01\x00\x00\x00\x00\x00\xff\xff\xff\xff\xff\xff\x00\x01\x00x\x19\x00\x16<\x00\x08\xff\x01\x00\xfc\n\x00\x01\n\x15\t\x0c\x10'!\xff\xff\xff\xff\xff\xff\xff"
#   ^   ^   ^   ^   ^   ^   |arlm|calibration                                               |^   |alarm      |^   ^   ^   |zoom dispay   ||data save/read addr   |^   |reserve|^   |maxcpm|^^   ^   ^   ^   ^   ^   ^ ^   ^   ^ |save....................|
#   ^   ^   ^   ^   ^   idle title display mode                                              ^                ^   ^   ^   ^                                       ^            ^           ^^   ^   ^   ^   btry^   ^ ^   ^   ^
#   ^   ^   ^   ^   backlight timeout                                                        ^                ^   ^   ^                                           ^            ^           ^^   ^   ^   motion  ^   ^ ^   ^   reserved
#   ^   ^   ^   graphic                                                                      ^                ^   ^   swivel display                              ^            ^           ^^   ^   reverse     ^   ^ ^   led on/off
#   ^   ^   speaker                                                                          ^                ^   save data type                                  ^            ^           ^^   lcd backlight   ^   ^ graphic mode
#   ^   alarm                                                                                ^                alarm type                                          ^            constrast   ^large form mode     ^   reserved
#   power                                                                                    idle display mode                                                    power saving mode        reserve              baud rate

               #   0                   5             10               15               20                  25               30               35                  40                  45               50               55                60
DESIRED_CONFIG = b'\x00\x01\x00\x00\x1f\x00\x00d\x00<\x14\xae\xc7>\x00\xf0\x14\xae\xc7?\x03\xe8\x00\x00\xd0@\x03\x00\x00\x00?\x00\x01\x00\x00\x00\x00\x00\xff\xff\xff\xff\xff\xff\x01\x01\x00x\x19\xff\xff<\x00\x08\xff\x01\x00\xfc\n\x00\x01\n\x15\t\x0c\x11*$\xff\xff'
           # 012345678901234567890123456789012345678901234567890123456789012345678901234
           # 0         1         2         3         4         5         6         7
BYTE_MASK = "011111011000000000000000001000011111110000001000100011101001000000000000000"

class Converter:
  ADDRESS_CALIBRATE1_CPM = 0x08
  ADDRESS_CALIBRATE1_USVH = 0x0a
  ADDRESS_CALIBRATE2_CPM = 0x0e
  ADDRESS_CALIBRATE2_USVH = 0x10
  ADDRESS_CALIBRATE3_CPM = 0x14
  ADDRESS_CALIBRATE3_USVH = 0x16

  def __init__(self, cfg):
    # count is one endianness, float figure is another? weird
    self.c1_cpm, _           , self.c2_cpm, _,            self.c3_cpm, _            = struct.unpack(">HfHfHf", cfg[self.ADDRESS_CALIBRATE1_CPM:self.ADDRESS_CALIBRATE3_USVH+4])
    _,           self.c1_usvh, _,           self.c2_usvh, _,           self.c3_usvh = struct.unpack("<HfHfHf", cfg[self.ADDRESS_CALIBRATE1_CPM:self.ADDRESS_CALIBRATE3_USVH+4])

  def convert(self, cps):
    if cps > self.c3_cpm:
      cpm, usvh = self.c3_cpm, self.c3_usvh
    elif cps > self.c2_cpm:
      cpm, usvh = self.c2_cpm, self.c2_usvh
    else:
      cpm, usvh = self.c1_cpm, self.c1_usvh

    return (cps * usvh) / (cpm * 60)

class Serial:
  def __init__(self, path, baud):
    self.__fd = os.open(path, os.O_RDWR)

    (iflag, oflag, cflag, lflag, ispeed, ospeed, cc) = (0, 0, 0, 0, 0, 0, [0] * 32)
    iflag = termios.IGNBRK
    oflag = 0

    ispeed = ospeed = getattr(termios, "B%d" % baud)

    cflag = (termios.CREAD | termios.CLOCAL)
    cflag |= termios.CS8
    cflag |= ispeed

    cc[termios.VMIN] = 1
    cc[termios.VTIME] = 0

    termios.tcsetattr(self.__fd, termios.TCSANOW,  [iflag, oflag, cflag, lflag, ispeed, ospeed, cc])

  def write(self, b):
    return os.write(self.__fd, b)

  def read(self, l):
    buf = b""
    remaining = l
    while remaining > 0:
      data = os.read(self.__fd, remaining)
      if not data:
        return buf
      buf+=data
      remaining-=len(data)
    return buf

  def drain(self):
    termios.tcflush(self.__fd, termios.TCIFLUSH)

  def close(self):
    if self.__fd == -1:
      return
    try:
      os.close(self.__fd)
    finally:
      self.__fd = -1

class GMC300EPlus:
  def __init__(self, device, baud):
    s = self.__s = Serial(device, 57600)
    s.write(b"<HEARTBEAT0>>")
    time.sleep(1)
    s.drain()

    d = time.localtime()
    df = struct.pack(">BBBBBB", d.tm_year - 2000, d.tm_mon, d.tm_mday, d.tm_hour, d.tm_min, d.tm_sec)
    s.write(b"<SETDATETIME" + df + b">>")
    if s.read(1) != b"\xaa":
      raise Exception("bad data")

    s.write(b"<GETCFG>>")
    cfg = s.read(256)
    self.__conv = Converter(cfg)

    if cfg[0] != 0:
      s.write(b"<POWERON>>")

    config_update_needed = False
    for pos, (mask, actual_value, expected_value) in enumerate(zip(BYTE_MASK, cfg, DESIRED_CONFIG)):
      if mask == "0":
        continue
      if actual_value != expected_value:
        #print(pos, actual_value, expected_value)
        config_update_needed = True
        break

    if config_update_needed:
      s.write(b"<ECFG>>")
      for pos, (mask, actual_value, expected_value) in enumerate(zip(BYTE_MASK, cfg, DESIRED_CONFIG)):
        if mask == "0":
          value = actual_value
        else:
          value = expected_value

        s.write(b"<WCFG" + struct.pack(">BB", pos, expected_value) + b">>")
        if s.read(1) != b"\xaa":
          raise Exception("bad data")

      s.write(b"<CFGUPDATE>>")
      if s.read(1) != b"\xaa":
        raise Exception("bad data")
      s.write(b"<POWERON>>") ## otherwise backlight breaks

    s.write(b"<HEARTBEAT1>>")

  def __iter__(self):
    p = struct.Struct(">H").unpack_from
    per_minute = util.Collector(60)
    per_hour = util.Collector(3600)

    while True:
      buf = self.__s.read(2)
      if len(buf) != 2:
        raise Exception("EOF")

      cps = p(buf)[0] & 0x3FFF
      cpm = per_minute.record(cps, True)
      cph = per_hour.record(cps, True)
      usvh = self.__conv.convert(cph)

      yield cps, int(cpm), int(cph), usvh

  def close(self):
    self.__s.close()

