#! /bin/python

#https://raspberrypihq.com/use-a-push-button-with-raspberry-pi-gpio/

#https://github.com/ccrisan/motioneyeos/issues/842#issuecomment-414375686

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("PIR Sensor")
logger.setLevel(logging.DEBUG)

import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
import time
import threading
import pycurl
import cStringIO

PIR_GPIO=4
INTERNAL_RESISTOR=GPIO.PUD_DOWN; #PUD_OFF, PUD_DOWN, PID_UP
DELAY=2000 #ms

state={
  "ts": 0,
  "mode": "idle",
  "timer": None
}

prev_state=None



# Signal handler
import signal
def handle_signals(signum, stack):
  logger.debug("Received signal {signal}".format(signal=signum))
  if signum == signal.SIGTERM or signum == signal.SIGINT:
    exit_thread.set()


def callback_motion(channel):
  gpio_state = GPIO.input(PIR_GPIO)
  ts = time.time()
  
  if (state["timer"]):
    state["timer"].cancel();
    state["timer"]=None;

  state["ts"]=ts
  
  if (gpio_state):
    logger.info("Motion detected");
    rc = http_req(1)
    logger.debug(rc)
    
    state["mode"]="motion"
    # Stop video at least after 10 minutes
    state["timer"]=threading.Timer(15.0, callback_stopRecording)
    state["timer"].start()
  else:
    logger.info("No Motion detected");
    state["mode"]="nomotion"
    state["timer"]=threading.Timer(5.0, callback_stopRecording)
    state["timer"].start()


def callback_stopRecording():
  ts = time.time()
  logger.info("Recording stopped")
  rc = http_req(0)
  logger.debug(rc)

  state["mode"]="idle"
  state["ts"]=ts
  state["timer"]=None;



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


def run():
  signal.signal(signal.SIGTERM, handle_signals)
  signal.signal(signal.SIGINT, handle_signals)

  # Set-Up GPIO
  #GPIO.setwarnings(False) # Ignore warning for now
  #GPIO.setmode(GPIO.BOARD) # Use physical pin numbering
  GPIO.setmode(GPIO.BCM) # Use GPIO numbering

  GPIO.setup(PIR_GPIO, GPIO.IN, pull_up_down=INTERNAL_RESISTOR)
  GPIO.add_event_detect(PIR_GPIO,GPIO.BOTH,callback=callback_motion) 

  # Wait for exit
  signal.pause()
  
  GPIO.cleanup() # Clean up
  logger.debug("Bye")


if __name__ == "__main__":
  run()
