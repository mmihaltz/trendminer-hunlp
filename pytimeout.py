import signal
import subprocess


class Timeout:
  """Timeout class using ALARM signal.
     source: http://stackoverflow.com/questions/8464391/what-should-i-do-if-socket-setdefaulttimeout-is-not-working
     Usage example:
     try:
       with Timeout(3):
         # some statments that may time out
     except Timeout.Timeout:
       print "Timeout!"
  """
  class Timeout(Exception): pass

  def __init__(self, sec):
    self.sec = sec

  def __enter__(self):
    signal.signal(signal.SIGALRM, self.raise_timeout)
    signal.alarm(self.sec)

  def __exit__(self, *args):
    signal.alarm(0) # disable alarm

  def raise_timeout(self, *args):
    raise Timeout.Timeout()
