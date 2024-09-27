# This is the main function for leader drone.
# Version 2.1

import threading
import time
import yaml
import builtins
from datetime import datetime
import netifaces as ni
from dronekit import connect
import os
import sys

sys.path.append(os.getcwd())
from formation_function import (
    start_SERVER_service,
    CHECK_network_connection,
    arm_no_RC,
    wait_for_follower_ready,
    takeoff_and_hover,
    CLIENT_send_immediate_command,
    new_gps_coord_after_offset_inBodyFrame,
    goto_gps_location_relative,
    distance_between_two_gps_coord,
    air_break,
    return_to_launch,
)


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
is_leader = True
if is_leader:
    print("{} - This is a leader drone.".format(time.ctime()))
    leader_host = local_host
else:
    print("{} - This is a follower drone.".format(time.ctime()))

# Get local host IP.
# local_host = ni.ifaddresses("wlan0")[2][0]["addr"]
local_host = ni.ifaddresses(config['WLAN_INTERFACE'])[2][0]['addr']
print("{} - local_host = {}.".format(time.ctime(), local_host))
host_specifier = local_host[-1]
print("{} - This drone is iris{}".format(time.ctime(), host_specifier))

# Reserved port.
# The port number should be exactly the same as that in follower drone.
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
start_SERVER_service(is_leader, local_host)

# Start connection checker. Drone will return home once lost connection.
router_host = config['ROUTER_HOST']
threading.Thread(
    target=CHECK_network_connection, args=(router_host,), kwargs={"wait_time": 10}
).start()

# Arm drone without RC.
arm_no_RC()

# IP list:
iris1_host = config['host1']
iris2_host = config['host2']
iris3_host = config['host3']

follower1 = iris2_host
follower2 = iris3_host
follower_host_tuple = (
    follower1,
    follower2,
)

# Wait untill all followers are ready(armed).
wait_for_follower_ready(follower_host_tuple)  # This is a blocking call.

# Get GPS coordinate of leader's launch location.
leader_gps_home = builtins.vehicle.location.global_relative_frame
leader_lat_home = leader_gps_home.lat
leader_lon_home = leader_gps_home.lon
leader_alt_home = leader_gps_home.alt
print("{} - Home GPS coordinate :".format(time.ctime()))
print("     leader_lat_home = {}".format(leader_lat_home))
print("     leader_lon_home = {}".format(leader_lon_home))
print("     leader_alt_home = {} (relative)".format(leader_alt_home))

# DOUBLE CHECK the following 4 parameters before each flight mission.
leader_hover_height = 5  # In meter.
leader_fly_distance = 10  # In meters.
leader_aim_heading_direction = (
    builtins.vehicle.heading
)  # (use current) # In degree, 0~360. 90=East

# Fixed parameters.
# fly_follow() parameters for follower1.
follower1_followee = "'" + leader_host + "'"  # The string must contain ''.
follower1_frame_to_followee = "'" + "body" + "'"  # 'body' or 'local'.
# fly_follow() parameters for follower2.
follower2_followee = follower1_followee
follower2_frame_to_followee = follower1_frame_to_followee


# ===================== Formation 1 (Horizontal) =====================
# When taking off, drones are already in this formation.
# Follower 1.
follower1_hover_height = 5  # In meter.
follower1_distance_to_followee = 7  # In meter.
follower1_azimuth_to_followee = (
    90  # In degree. 'body' frame: 0=Forwar, 90=Right; 'local' frame: 0=North, 90=East.
)
# Follower 2.
follower2_hover_height = 5  # In meter.
follower2_distance_to_followee = 8  # In meter.
follower2_azimuth_to_followee = (
    180  # In degree. 'body' frame: 0=Forwar, 90=Right; 'local' frame: 0=North, 90=East.
)


# When all members are ready.
# Leader takeoff and hover (in square shape).
threading.Thread(target=takeoff_and_hover, args=(leader_hover_height,)).start()
# Send takeoff command to all followers.
# Immediate command must be in string type.
print("{} - Sending immediate command to : {}.".format(time.ctime(), follower1))
CLIENT_send_immediate_command(
    follower1, "takeoff_and_hover({})".format(follower1_hover_height)
)
print("{} - Sending immediate command to : {}.".format(time.ctime(), follower2))
CLIENT_send_immediate_command(
    follower2, "takeoff_and_hover({})".format(follower2_hover_height)
)

# Wait for follower ready. Blocking function.
wait_for_follower_ready(follower_host_tuple)

# Get leader current location.
leader_current_gps = builtins.vehicle.location.global_relative_frame
leader_current_lat = leader_current_gps.lat
leader_current_lon = leader_current_gps.lon
leader_current_alt = leader_current_gps.alt
print(
    "{} - After taking off and hover, Leader's GPS coordinate : lat={}, lon={}, alt_relative={}".format(
        time.ctime(), leader_current_lat, leader_current_lon, leader_current_alt
    )
)
# Get leader current heading.
leader_current_heading = builtins.vehicle.heading
print(
    "{} - Leader current heading is {} degree.".format(
        time.ctime(), leader_current_heading
    )
)

# Generate a point, leader will fly to this point.
pointA = new_gps_coord_after_offset_inBodyFrame(
    (leader_current_lat, leader_current_lon),
    leader_fly_distance,
    leader_current_heading,
    0,
)  # 0=Forward, 90=Right, 180=Backward, 270=Left.
print("{} - Leader is going to pointA : {}".format(time.ctime(), pointA))

# Leader go to new location. Followers fly follow in square shape.
threading.Thread(
    target=goto_gps_location_relative,
    args=(
        pointA[0],
        pointA[1],
        leader_hover_height,
    ),
    kwargs={"groundspeed": 1},
).start()
# When leader is not at destination location, keep sending follow fly command to followers.
# You can use threading to reduce the delay.
# Function prototype : fly_follow(followee_host, frame, height, radius_2D, azimuth)
while (
    distance_between_two_gps_coord(
        (
            builtins.vehicle.location.global_relative_frame.lat,
            builtins.vehicle.location.global_relative_frame.lon,
        ),
        (pointA[0], pointA[1]),
    )
    > 0.5
) or (
    abs(builtins.vehicle.location.global_relative_frame.alt - leader_hover_height) > 0.3
):
    print("{} - Sending command fly_follow() to follower1.".format(time.ctime()))
    CLIENT_send_immediate_command(
        follower1,
        "fly_follow({}, {}, {}, {}, {})".format(
            follower1_followee,
            follower1_frame_to_followee,
            follower1_hover_height,
            follower1_distance_to_followee,
            follower1_azimuth_to_followee,
        ),
    )
    print("{} - Sending command fly_follow() to follower2.".format(time.ctime()))
    CLIENT_send_immediate_command(
        follower2,
        "fly_follow({}, {}, {}, {}, {})".format(
            follower2_followee,
            follower2_frame_to_followee,
            follower2_hover_height,
            follower2_distance_to_followee,
            follower2_azimuth_to_followee,
        ),
    )
    time.sleep(0.5)

# When leader has reached destination, execute air_break().
# At the same time, send air_break command to all followers immediately.
threading.Thread(target=air_break, args=()).start()
for iter_follower in follower_host_tuple:
    print(iter_follower)
    CLIENT_send_immediate_command(iter_follower, "air_break()")


# ===================== Formation 2 (square) =====================
time.sleep(3)
# Shape 2 definition(Diamond).
# Follower 1.
follower1_hover_height = 5  # In meter.
follower1_distance_to_followee = 7  # In meter.
follower1_azimuth_to_followee = (
    270  # In degree. 'body' frame: 0=Forwar, 90=Right; 'local' frame: 0=North, 90=East.
)
# Follower 2.
follower2_hover_height = 5  # In meter.
follower2_distance_to_followee = 7  # In meter.
follower2_azimuth_to_followee = (
    225  # In degree. 'body' frame: 0=Forwar, 90=Right; 'local' frame: 0=North, 90=East.
)


# Change formation.
# 1) move follower2.
print("{} - Sending command fly_follow() to follower2.".format(time.ctime()))
CLIENT_send_immediate_command(
    follower2,
    "fly_follow({}, {}, {}, {}, {})".format(
        follower2_followee,
        follower2_frame_to_followee,
        follower2_hover_height,
        follower2_distance_to_followee,
        follower2_azimuth_to_followee,
    ),
)
time.sleep(5)  # Give drone 5 seconds to get to its position.
# 2) move follower1.
print("{} - Sending command fly_follow() to follower1.".format(time.ctime()))
CLIENT_send_immediate_command(
    follower1,
    "fly_follow({}, {}, {}, {}, {})".format(
        follower1_followee,
        follower1_frame_to_followee,
        follower1_hover_height,
        follower1_distance_to_followee,
        follower1_azimuth_to_followee,
    ),
)
time.sleep(5)  # Give drone 5 seconds to get to its position.

# Get leader current location.
leader_current_gps = builtins.vehicle.location.global_relative_frame
leader_current_lat = leader_current_gps.lat
leader_current_lon = leader_current_gps.lon
leader_current_alt = leader_current_gps.alt
print(
    "{} - In formation 2 (diamond), leader's GPS coordinate : lat={}, lon={}, alt_relative={}".format(
        time.ctime(), leader_current_lat, leader_current_lon, leader_current_alt
    )
)
# Get leader current heading.
leader_current_heading = builtins.vehicle.heading
print(
    "{} - Leader current heading is {} degree.".format(
        time.ctime(), leader_current_heading
    )
)

# Generate a point, leader will fly to this point.
pointA = new_gps_coord_after_offset_inBodyFrame(
    (leader_current_lat, leader_current_lon),
    leader_fly_distance,
    leader_current_heading,
    0,
)  # 0=Forward, 90=Right, 180=Backward, 270=Left.
print("{} - Leader is going to pointA : {}".format(time.ctime(), pointA))

# Leader go to new location.
threading.Thread(
    target=goto_gps_location_relative,
    args=(
        pointA[0],
        pointA[1],
        leader_hover_height,
    ),
    kwargs={"groundspeed": 1},
).start()
# When leader is not at destination location, keep sending follow fly command to followers.
# You can use threading to reduce the delay.
# Function prototype : fly_follow(followee_host, frame, height, radius_2D, azimuth)
while (
    distance_between_two_gps_coord(
        (
            builtins.vehicle.location.global_relative_frame.lat,
            builtins.vehicle.location.global_relative_frame.lon,
        ),
        (pointA[0], pointA[1]),
    )
    > 0.5
) or (
    abs(builtins.vehicle.location.global_relative_frame.alt - leader_hover_height) > 0.3
):
    print("{} - Sending command fly_follow() to follower1.".format(time.ctime()))
    CLIENT_send_immediate_command(
        follower1,
        "fly_follow({}, {}, {}, {}, {})".format(
            follower1_followee,
            follower1_frame_to_followee,
            follower1_hover_height,
            follower1_distance_to_followee,
            follower1_azimuth_to_followee,
        ),
    )
    print("{} - Sending command fly_follow() to follower2.".format(time.ctime()))
    CLIENT_send_immediate_command(
        follower2,
        "fly_follow({}, {}, {}, {}, {})".format(
            follower2_followee,
            follower2_frame_to_followee,
            follower2_hover_height,
            follower2_distance_to_followee,
            follower2_azimuth_to_followee,
        ),
    )
    time.sleep(0.5)

# When leader has reached destination, execute air_break().
# At the same time, send air_break command to all followers immediately.
threading.Thread(target=air_break, args=()).start()
for iter_follower in follower_host_tuple:
    CLIENT_send_immediate_command(iter_follower, "air_break()")

# ===================== Formation 3 (vertical) =====================
time.sleep(3)
# Shape 3 (triangle).
# Follower 1.
follower1_hover_height = 5  # In meter.
follower1_distance_to_followee = 8  # In meter.
follower1_azimuth_to_followee = (
    0  # In degree. 'body' frame: 0=Forwar, 90=Right; 'local' frame: 0=North, 90=East.
)
# Follower 2.
follower2_hover_height = 5  # In meter.
follower2_distance_to_followee = 7  # In meter.
follower2_azimuth_to_followee = (
    360  # In degree. 'body' frame: 0=Forwar, 90=Right; 'local' frame: 0=North, 90=East.
)


# 1) move follower1.
print("{} - Sending command fly_follow() to follower1.".format(time.ctime()))
CLIENT_send_immediate_command(
    follower1,
    "fly_follow({}, {}, {}, {}, {})".format(
        follower1_followee,
        follower1_frame_to_followee,
        follower1_hover_height,
        follower1_distance_to_followee,
        follower1_azimuth_to_followee,
    ),
)
time.sleep(5)  # Give drone 5 seconds to get to its position.
# 2) move follower2.
print("{} - Sending command fly_follow() to follower2.".format(time.ctime()))
CLIENT_send_immediate_command(
    follower2,
    "fly_follow({}, {}, {}, {}, {})".format(
        follower2_followee,
        follower2_frame_to_followee,
        follower2_hover_height,
        follower2_distance_to_followee,
        follower2_azimuth_to_followee,
    ),
)
time.sleep(5)  # Give drone 5 seconds to get to its position.


# Get leader current location.
leader_current_gps = builtins.vehicle.location.global_relative_frame
leader_current_lat = leader_current_gps.lat
leader_current_lon = leader_current_gps.lon
leader_current_alt = leader_current_gps.alt
print(
    "{} - In formation 3 (triangle), leader's GPS coordinate : lat={}, lon={}, alt_relative={}".format(
        time.ctime(), leader_current_lat, leader_current_lon, leader_current_alt
    )
)
# Get leader current heading.
leader_current_heading = builtins.vehicle.heading
print(
    "{} - Leader current heading is {} degree.".format(
        time.ctime(), leader_current_heading
    )
)

# Generate a point, leader will fly to this point.
pointA = new_gps_coord_after_offset_inBodyFrame(
    (leader_current_lat, leader_current_lon),
    leader_fly_distance,
    leader_current_heading,
    0,
)  # 0=Forward, 90=Right, 180=Backward, 270=Left.
print("{} - Leader is going to pointA : {}".format(time.ctime(), pointA))

# Leader go to new location.
threading.Thread(
    target=goto_gps_location_relative,
    args=(
        pointA[0],
        pointA[1],
        leader_hover_height,
    ),
    kwargs={"groundspeed": 1},
).start()
# When leader is not at destination location, keep sending follow fly command to followers.
# You can use threading to reduce the delay.
# Function prototype : fly_follow(followee_host, frame, height, radius_2D, azimuth)
while (
    distance_between_two_gps_coord(
        (
            builtins.vehicle.location.global_relative_frame.lat,
            builtins.vehicle.location.global_relative_frame.lon,
        ),
        (pointA[0], pointA[1]),
    )
    > 0.5
) or (
    abs(builtins.vehicle.location.global_relative_frame.alt - leader_hover_height) > 0.3
):
    print("{} - Sending command fly_follow() to follower1.".format(time.ctime()))
    CLIENT_send_immediate_command(
        follower1,
        "fly_follow({}, {}, {}, {}, {})".format(
            follower1_followee,
            follower1_frame_to_followee,
            follower1_hover_height,
            follower1_distance_to_followee,
            follower1_azimuth_to_followee,
        ),
    )
    print("{} - Sending command fly_follow() to follower2.".format(time.ctime()))
    CLIENT_send_immediate_command(
        follower2,
        "fly_follow({}, {}, {}, {}, {})".format(
            follower2_followee,
            follower2_frame_to_followee,
            follower2_hover_height,
            follower2_distance_to_followee,
            follower2_azimuth_to_followee,
        ),
    )
    time.sleep(0.5)

# When leader has reached destination, execute air_break().
# At the same time, send air_break command to all followers immediately.
threading.Thread(target=air_break, args=()).start()
for iter_follower in follower_host_tuple:
    CLIENT_send_immediate_command(iter_follower, "air_break()")

# ===================== Mission completed, leader and followers go home =====================
# Wait for follower ready.
"""
time.sleep(10)
wait_for_follower_ready(follower_host_tuple)
print("{} - Mission completed. Return home.".format(time.ctime()))

# Follower2 go home.
print("{} - Command follower2 return home.".format(time.ctime()))
CLIENT_send_immediate_command(follower2, "return_to_launch()")
time.sleep(2)

# Follower1 go home.
print("{} - Command follower1 return home.".format(time.ctime()))
CLIENT_send_immediate_command(follower1, "return_to_launch()")
time.sleep(2)

# Leader drone go home.
print("{} - Followers have returned home, Leader is returning...".format(time.ctime()))
return_to_launch()
print("{} - Leader has returned home.".format(time.ctime()))
"""