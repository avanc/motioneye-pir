#!/usr/bin/python

# Script to activate and deactivate external light (e.g. IR illumination) based on connections to port 80 (www)
# The parsing of /proc is based on https://github.com/da667/netstat

############################
# Configuration parameters #
############################
LIGHT_GPIO=23
BACKGROUND=True # Run script in background as daemon


# If you have suggestions or improvements for the code below,
# consider opening an issue or pull request at
# https://github.com/avanc/motioneye-pir

# netstat -apt to compare results

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("Light Activation")
logger.setLevel(logging.DEBUG)


import pwd
import os
import re
import glob

PROC_TCP4 = "/proc/net/tcp"
TCP_STATE = {
        '01':'ESTABLISHED',
        '02':'SYN_SENT',
        '03':'SYN_RECV',
        '04':'FIN_WAIT1',
        '05':'FIN_WAIT2',
        '06':'TIME_WAIT',
        '07':'CLOSE',
        '08':'CLOSE_WAIT',
        '09':'LAST_ACK',
        '0A':'LISTEN',
        '0B':'CLOSING'
        }

def _tcp4load():
    ''' Read the table of tcp connections & remove the header  '''
    with open(PROC_TCP4,'r') as f:
        content = f.readlines()
        content.pop(0)
    return content
  
def _hex2dec(s):
    return int(s,16)
  
def _ip(s):
    ip = [str(_hex2dec(s[6:8])),str(_hex2dec(s[4:6])),str(_hex2dec(s[2:4])),str(_hex2dec(s[0:2]))]
    return '.'.join(ip)

def _remove_empty(array):
    return [x for x in array if x !='']

def _convert_ipv4_port(array):
    host,port = array.split(':')
    return _ip(host),_hex2dec(port)



def netstat_tcp4():
    '''
    Function to return a list with status of tcp connections on Linux systems.
    Please note that in order to return the pid of of a network process running on the
    system, this script must be ran as root.
    '''

    tcpcontent =_tcp4load()
    tcpresults = []
    for line in tcpcontent:
      tcpresult={}
      
      line_array = _remove_empty(line.split(' '))  # Split lines and remove empty spaces.

      tcpresult["local"]={}
      tcpresult["local"]["host"],tcpresult["local"]["port"] = _convert_ipv4_port(line_array[1])

      tcpresult["remote"]={}
      tcpresult["remote"]["host"],tcpresult["remote"]["port"] = _convert_ipv4_port(line_array[2])

      tcpresult["id"] = line_array[0]

      tcpresult["state"] = TCP_STATE[line_array[3]]

      tcpresult["uid"] = pwd.getpwuid(int(line_array[7]))[0]       # Get user from UID.

      tcpresult["inode"] = line_array[9]                           # Need the inode to get process pid.
      
      # Do not resolve pid as this causes a lot of overhead
      #tcpresult["pid"] = _get_pid_of_inode(tcpresult["inode"])                  # Get pid prom inode.
      #try:                                            # try read the process name.
      #    tcpresult["process"] = os.readlink('/proc/'+tcpresult["pid"]+'/exe')
      #except:
      #    pass

      tcpresults.append(tcpresult)
    return tcpresults


def _get_pid_of_inode(inode):
    '''
    To retrieve the process pid, check every running process and look for one using
    the given inode.
    '''
    for item in glob.glob('/proc/[0-9]*/fd/[0-9]*'):
        try:
            if re.search(inode,os.readlink(item)):
                return item.split('/')[2]
        except:
            pass
    return None

running=True

# Signal handler
import signal
def handle_signals(signum, stack):
  logger.debug("Received signal {signal}".format(signal=signum))
  global running
  if signum == signal.SIGTERM or signum == signal.SIGINT:
        running = False

def getConnections(port=80, state="ESTABLISHED"):
  result=[]
  connections=netstat_tcp4()
  for connection in connections:
    #logger.debug(connection)
    if (connection["local"]["port"]==port):
      if (connection["state"]==state):
        result.append(connection)

  return result


import RPi.GPIO as GPIO

def light(state):
  logger.debug("Switch light {state}".format(state="on" if state else "off"))
  if (state):
    GPIO.output(LIGHT_GPIO, GPIO.HIGH)
  else:
    GPIO.output(LIGHT_GPIO, GPIO.LOW)


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

import time
from datetime import datetime

def run():
  signal.signal(signal.SIGTERM, handle_signals)
  signal.signal(signal.SIGINT, handle_signals)

  if (BACKGROUND):
    createDaemon()

  try:
    LIGHT_PIN
  except NameError:
    GPIO.setmode(GPIO.BCM) # Use GPIO numbering
    GPIO.setup(LIGHT_GPIO, GPIO.OUT)
  else:
    GPIO.setmode(GPIO.BOARD) # Use physical pin numbering
    GPIO.setup(LIGHT_PIN, GPIO.OUT)

  
  
  while (running):
    connections=getConnections()
    light( len(connections)>0 )
      
    
    print("[{time}] Established connections to port 80 (www):".format(time=datetime.now().isoformat()))
    for connection in connections:
      print("IP: {ip}, Inode: {inode}".format(ip=connection["remote"]["host"], inode=connection["inode"]))
      
    time.sleep(1)


if __name__ == '__main__':
  run()
