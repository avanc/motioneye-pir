PIR motion detection
====================

This is a short script to control [motionEye](https://github.com/ccrisan/motioneye/wiki) (or just plain [motion](https://motion-project.github.io/)) using a PIR motion sensor connected via GPIO to a Raspberry Pi.

Installation
------------

[MotionEyeOS](https://github.com/ccrisan/motioneyeos/wiki) is taken as base for this description. However, it should be straight forward to apply these steps also on another installation.

On the camera, the root filesystem has to be mounte Read/Write to install the script

    [root@cam1 ~]# mount -o remount,rw /
    
Download the script

    [root@cam1 ~]# mkdir /data/pir
    [root@cam1 ~]# curl -o /data/pir/pir_motion_detector.py https://raw.githubusercontent.com/avanc/motioneye-pir/master/pir_motion_detector.py

and make your config changes

    [root@cam1 ~]# vi /data/pir/pir_motion_detector.py
    
At least change the GPIO (PIR_GPIO) according your hardware setup. Alternatively, you can also set the physical pin number (PIR_PIN).

Most PIR sensors have defined logic values (0V and 3.3V). However, if you are not using a PIR sensor and want to connect a switch for manually start recording (e.g. for testing), connect the switch between the pin and 3.3V and activate the internal pull-down resistor (INTERNAL_RESISTOR=GPIO.PUD_DOWN).

Activate script on boot within /data/etc/userinit.sh

    .
    .
    .
    python /data/pir/pir_motion_detector.py
    .
    .
    .    

