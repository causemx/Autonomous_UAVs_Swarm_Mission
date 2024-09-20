# This is the main function for follower drone.
import builtins
import time
import yaml
from datetime import datetime
import netifaces as ni
from dronekit import connect
import threading
import os
import sys

sys.path.append(os.getcwd())
from formation_function import start_SERVER_service, CHECK_network_connection, arm_no_RC

# Read config.yaml
with open('config.yaml', 'r') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

# Get local host IP.
local_host = ni.ifaddresses(config['WLAN_INTERFACE'])[2][0]['addr']
host_specifier = local_host[-1]

# Set log.

flight_log_bufsize = 1  # 0 means unbuffered, 1 means line buffered.
flight_log_filename = (
    "FlightLog_iris"
    + host_specifier
    + "_"
    + "{:%Y%m%d_%H-%M-%S}".format(datetime.now())
    + ".txt"
)
flight_log_path = "/home/pi/log/"
flight_log_path_filename = flight_log_path + flight_log_filename
flight_log = open(flight_log_path_filename, "w", flight_log_bufsize)
sys.stdout = flight_log


# Specify whether a leader or a follower.
is_leader = False
if is_leader:
    print("{} - This is a leader drone.".format(time.ctime()))
else:
    print("{} - This is a follower drone.".format(time.ctime()))

print("{} - local_host = {}.".format(time.ctime(), local_host))
print("{} - This drone is iris{}".format(time.ctime(), host_specifier))

# Create global variable to indicate follower status.
builtins.status_waitForCommand = False

# Reserved port.
# The port number should be exactly the same as that in leader drone.
builtins.port_gps = 60001
builtins.port_status = 60002
builtins.port_immediate_command = 60003
builtins.port_heading = 60004

# Connect to the Vehicle
print("{} - Connecting to vehicle...".format(time.ctime()))
vehicle_temp = connect("/dev/ttyAMA0", baud=57600, wait_ready=True)
while "vehicle_temp" not in locals():
    print("{} - Waiting for vehicle connection...".format(time.ctime()))
    time.sleep(1)
builtins.vehicle = vehicle_temp
print("{} - Vehicle is connected!".format(time.ctime()))
# Enable safety switch(take effect after reboot pixhawk).
builtins.vehicle.parameters["BRD_SAFETYENABLE"] = 1  # Enable
# vehicle.parameters['BRD_SAFETYENABLE'] = 0 # Disable

# Start server services.
start_SERVER_service(vehicle_temp, is_leader, local_host)

# Start connection checker. Drone will return home once lost connection.
router_host = config['ROUTER_HOST']
threading.Thread(
    target=CHECK_network_connection, args=(vehicle_temp, router_host,), kwargs={"wait_time": 10}
).start()

# Self arm.
print("{} - Self arming...".format(time.ctime()))
arm_no_RC(vehicle_temp)  # Blocking call.
# Once armed, change status_waitForCommand to True.
builtins.status_waitForCommand = True
print(
    "{} - __builtin__.status_waitForCommand = {}".format(
        time.ctime(), builtins.status_waitForCommand
    )
)
print("{} - Follower is armed!".format(time.ctime()))
