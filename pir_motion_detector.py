#! /bin/python

# Script to activate video recording using a PIR sensor
# This script is heavily based on the initial code on https://github.com/ccrisan/motioneyeos/issues/842#issuecomment-414375686 by jasaw

############################
# Configuration parameters #
############################
PIR_GPIO = 4 # GPIO numbering
#PIR_PIN = 7 # Alternatively set the physical pin number

INTERNAL_RESISTOR="off"; # off for PIR sensor, pull-down for button connected to 3.3V
STOP_DELAY=10.0 # (seconds) Delayed stop after recording
MAX_LENGTH=3600.0 # (seconds) Maximum length of clips
BACKGROUND=True # Run script in background as daemon


# If you have suggestions or improvements for the code below,
# consider opening an issue or pull request at
# https://github.com/avanc/motioneye-pir

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("PIR Sensor")
logger.setLevel(logging.DEBUG)

import RPi.GPIO as GPIO
import time
import threading
import pycurl
import cStringIO

if (INTERNAL_RESISTOR=="pull-down"):
  INTERNAL_RESISTOR=GPIO.PUD_DOWN
elif (INTERNAL_RESISTOR=="pull-up"):
  INTERNAL_RESISTOR=GPIO.PUD_UP
else:
  INTERNAL_RESISTOR=GPIO.PUD_OFF


class MotionWrapper:
  def __init__(self):
    self.mode="idle"
    self.timer=None
  
  def cleanup(self):
    if (self.timer):
      self.timer.cancel();
      self.timer=None;
    if (self.mode!="idle"):
      logger.debug("Cancel recording")
      self.recording_stop();

  def detected(self, motion):
    if (self.timer):
      self.timer.cancel();
      self.timer=None;

    if (motion):
      logger.info("Motion detected");
      self.mode="motion"
      self.recording_start()
    
      # Stop video at least after MAX_LENGTH seconds
      self.timer=threading.Timer(MAX_LENGTH, self.recording_stop)
      self.timer.start()
    else:
      logger.info("No Motion detected");
      self.mode="nomotion"
      self.timer=threading.Timer(STOP_DELAY, self.recording_stop)
      self.timer.start()

  def recording_start(self):
    rc = http_req(1)
    logger.debug(rc)
    
  def recording_stop(self):
    logger.info("Stop recording")
    if (self.timer):
      self.timer.cancel();
    self.timer=None;

    rc = http_req(0)
    logger.debug(rc)
    self.mode="idle"

motion=MotionWrapper()


# Signal handler
import signal
def handle_signals(signum, stack):
  logger.debug("Received signal {signal}".format(signal=signum))

# GPIO event callback
def callback_motion(channel):
  gpio_state = GPIO.input(PIR_GPIO)
  
  if (gpio_state):
    motion.detected(True)
  else:
    motion.detected(False)

# HTTP request to communicate with motion
prev_state=None
def http_req(motion):
  global prev_state
  if (prev_state!=motion):
    url="http://localhost:7999/1/config/set?emulate_motion={mode}".format(mode=motion)
    curl = pycurl.Curl()
    curl.setopt(pycurl.URL, url)
    response = cStringIO.StringIO()
    curl.setopt(pycurl.WRITEFUNCTION, response.write)
    response_headers = []
    curl.setopt(pycurl.HEADERFUNCTION, response_headers.append)
    try:
        curl.perform()
    except pycurl.error, e:
        print str(e)
    response_code = curl.getinfo(pycurl.RESPONSE_CODE)
    response_type = curl.getinfo(pycurl.CONTENT_TYPE)
    curl.close()
    response_data = response.getvalue()
    response.close()

    prev_state=motion
    return response_code


import os
def createDaemon():
    UMASK = 0
    WORKDIR = "/"
    MAXFD = 1024
    REDIRECT_TO = "/dev/null"
    if (hasattr(os, "devnull")):
        REDIRECT_TO = os.devnull

    try:
        pid = os.fork()
    except OSError, e:
        raise Exception, "%s [%d]" % (e.strerror, e.errno)
    if (pid == 0):
        os.setsid()
        try:
            pid = os.fork()
        except OSError, e:
            raise Exception, "%s [%d]" % (e.strerror, e.errno)

        if (pid == 0):
            os.chdir(WORKDIR)
            os.umask(UMASK)
            logger.info("Daemon started with PID {pid}".format(pid=os.getpid()))
        else:
            os._exit(0)
    else:
        os._exit(0)

    import resource
    maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if (maxfd == resource.RLIM_INFINITY):
        maxfd = MAXFD
    for fd in range(0, maxfd):
        try:
            os.close(fd)
        except OSError:
            pass
    os.open(REDIRECT_TO, os.O_RDWR)
    os.dup2(0, 1)
    os.dup2(0, 2)
    return(0)


def run():
  signal.signal(signal.SIGTERM, handle_signals)
  signal.signal(signal.SIGINT, handle_signals)

  if (BACKGROUND):
    createDaemon()

  
  try:
    PIR_PIN
  except NameError:
    GPIO.setmode(GPIO.BCM) # Use GPIO numbering
    GPIO.setup(PIR_GPIO, GPIO.IN, pull_up_down=INTERNAL_RESISTOR)
  else:
    GPIO.setmode(GPIO.BOARD) # Use physical pin numbering
    GPIO.setup(PIR_PIN, GPIO.IN, pull_up_down=INTERNAL_RESISTOR)

  GPIO.add_event_detect(PIR_GPIO,GPIO.BOTH,callback=callback_motion) 

  # Wait for exit
  signal.pause()
  
  global motion
  motion.cleanup()
  GPIO.cleanup()
  logger.debug("Bye")


if __name__ == "__main__":
  run()
