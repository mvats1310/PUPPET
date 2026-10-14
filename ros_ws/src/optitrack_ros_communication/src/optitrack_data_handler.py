#! /usr/bin/env python3

import rospy
from geometry_msgs.msg import PoseStamped
from dataclasses import dataclass
import socket
import math
import numpy as np

@dataclass
class desired_output:
    x: float
    y: float
    z: float
    w: float

    def __init__(self):
        self.x = 0
        self.y = 0
        self.z = 0
        self.w = 0

    def create(self, data, euler: list):
        " Use this function to change transformations to the data"
        self.x = data.pose.position.x * 100
        self.y = data.pose.position.y * 100
        self.z = data.pose.position.z * 100
        self.w = euler[2]
        return self

sock = None
last_position = {'x': 0.0, 'y': 0.0, 'z': 0.0, 'w': 0.0}

def quaternion_to_euler(data: PoseStamped):
    # quaternion to euler z == the heading
    x = data.pose.orientation.x 
    y = data.pose.orientation.y  
    z = data.pose.orientation.z 
    w = data.pose.orientation.w 
    
    t0 = +2.0 * (w * x + y * z)
    t1 = +1.0 - 2.0 * (x * x + y * y)
    X = math.atan2(t0, t1)

    t2 = +2.0 * (w * y - z * x)
    t2 = +1.0 if t2 > +1.0 else t2
    t2 = -1.0 if t2 < -1.0 else t2
    Y = math.asin(t2)

    t3 = +2.0 * (w * z + x * y)
    t4 = +1.0 - 2.0 * (y * y + z * z)
    Z = math.atan2(t3, t4)

    return [X, Y, Z]

def send_udp_message(host, port, message, name):
    global sock
    if sock is None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(message.encode(), (host, port))
    # rospy.loginfo(f"{name} Pose sent to {host}:{port}: {message}")

def has_position_changed(new_position, threshold=0.001):
    global last_position
    for axis in ['x', 'y', 'z', 'w']:
        if last_position[axis] is not None:
            if abs(new_position[axis] - last_position[axis]) > threshold:
                return True
    return False

def update_position(new_position, data):
    global last_position
    last_position = new_position
    return data

def callback(data):
    #time.sleep(0.001)
    host = rospy.get_param('~host')
    port = rospy.get_param('~port')
    name = rospy.get_param('~body')

    new_position = {
        'x': round(data.pose.position.x,4),
        'y': round(data.pose.position.y,4),
        'z': round(data.pose.position.z,4),
        'w': round(data.pose.orientation.w,4)
    }

    if has_position_changed(new_position):
        data = update_position(new_position, data)
        desired_output_t = desired_output().create(data, quaternion_to_euler(data))
        message = f"[{desired_output_t.x},{desired_output_t.y},{desired_output_t.z},{desired_output_t.w}]"
        send_udp_message(host, port, message, name)

def listener():
    rospy.init_node('optitrack_data', anonymous=True)
    name = rospy.get_param('~body')
    namespace = rospy.get_param('~namespace')
    rospy.Rate(120)
    rospy.Subscriber(f"/{namespace}/{name}/pose", PoseStamped, callback)
    rospy.spin()
        
if __name__ == '__main__':
    try:
        listener()
    finally:
        if sock is not None:
            sock.close()
