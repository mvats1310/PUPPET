#!/usr/bin/env python3

import math

import numpy as np
import rospy

from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from tf.transformations import (
    euler_from_quaternion,
    quaternion_from_euler,
)


class PuckPoseToOdom:
    def __init__(self):
        rospy.init_node("puck_pose_to_odom")

        # Set ~input_topic to the puck's exact OptiTrack topic
        # (check `rostopic list | grep natnet_ros`).
        self.input_topic = rospy.get_param(
            "~input_topic", "/natnet_ros/umh_object_mahika/pose"
        )
        self.output_topic = rospy.get_param("~output_topic", "/puck_mocap")

        self.pose_sub = rospy.Subscriber(
            self.input_topic,
            PoseStamped,
            self.pose_callback,
            queue_size=1,
        )

        self.odom_pub = rospy.Publisher(
            self.output_topic,
            Odometry,
            queue_size=1,
        )

        # Puck position offset, if the marker is not centered.
        self.offset_x = rospy.get_param("~offset_x", 0.0)
        self.offset_y = rospy.get_param("~offset_y", 0.0)
        self.offset_z = rospy.get_param("~offset_z", 0.0)

        # Rotation state.
        self.initialized = False
        self.initial_yaw = 0.0
        self.yaw_buffer = []

        rospy.loginfo("puck_pose_to_odom node started")
        rospy.loginfo(
            "Subscribing to: %s",
            self.input_topic
        )

        rospy.loginfo(
            "Publishing to: %s",
            self.output_topic
        )

    def pose_callback(self, msg):
        # ---------------- POSITION ----------------
        marker_x = msg.pose.position.x
        marker_y = msg.pose.position.y
        marker_z = msg.pose.position.z

        puck_x = marker_x - self.offset_x
        puck_y = marker_y - self.offset_y

        # Do not lock the height.
        # This allows the puck to move upward when TIAGo lifts it.
        puck_z = marker_z - self.offset_z

        # ---------------- ROTATION ----------------
        q = msg.pose.orientation
        quat = [q.x, q.y, q.z, q.w]

        _, _, raw_yaw = euler_from_quaternion(
            quat
        )

        # Smooth yaw.
        self.yaw_buffer.append(
            raw_yaw
        )

        if len(self.yaw_buffer) > 10:
            self.yaw_buffer.pop(0)

        unwrapped_yaw = np.unwrap(
            np.array(self.yaw_buffer)
        )

        smooth_yaw = float(
            np.median(unwrapped_yaw)
        )

        # Use the starting orientation as the zero reference.
        if not self.initialized:
            self.initial_yaw = smooth_yaw
            self.initialized = True

            rospy.loginfo(
                "Initialized puck yaw at %.2f degrees",
                math.degrees(
                    self.initial_yaw
                ),
            )

            return

        relative_yaw = (
            smooth_yaw -
            self.initial_yaw
        )

        relative_yaw = math.atan2(
            math.sin(relative_yaw),
            math.cos(relative_yaw),
        )

        q_out = quaternion_from_euler(
            0.0,
            0.0,
            relative_yaw,
        )

        # ---------------- PUBLISH ----------------
        odom = Odometry()

        odom.header.stamp = rospy.Time.now()
        odom.header.frame_id = "odom"
        odom.child_frame_id = "puck"

        odom.pose.pose.position.x = puck_x
        odom.pose.pose.position.y = puck_y
        odom.pose.pose.position.z = puck_z

        odom.pose.pose.orientation.x = q_out[0]
        odom.pose.pose.orientation.y = q_out[1]
        odom.pose.pose.orientation.z = q_out[2]
        odom.pose.pose.orientation.w = q_out[3]

        self.odom_pub.publish(odom)


if __name__ == "__main__":
    try:
        PuckPoseToOdom()
        rospy.spin()

    except rospy.ROSInterruptException:
        pass