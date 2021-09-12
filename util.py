import collections
import os

class Collector:
  def __init__(self, points):
    self.points = points
    self.buckets = collections.deque()
    self.cum_sum = 0

  def record(self, value, scale_up_result):
    self.cum_sum += value
    self.buckets.append(value)
    while len(self.buckets) > self.points:
      self.cum_sum -= self.buckets.popleft()

    if scale_up_result:
      return (self.cum_sum * self.points) / len(self.buckets)

    return self.cum_sum, len(self.buckets), self.points

def atomic_write(fn, data, fsync=True):
  tmp = fn + ".tmp"
  fd = os.open(tmp, os.O_WRONLY|os.O_CREAT|os.O_TRUNC)
  try:
    os.write(fd, data)
    if fsync:
      os.fsync(fd)
  finally:
    os.close(fd)
  os.rename(tmp, fn)
