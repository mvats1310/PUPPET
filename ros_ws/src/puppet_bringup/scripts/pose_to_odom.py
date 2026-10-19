#!/usr/bin/env python3
import rospy
import math
import numpy as np

from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from tf.transformations import euler_from_quaternion, quaternion_from_euler


class PoseToOdom:
    def __init__(self):
        rospy.init_node('optitrack_pose_to_odom')

        # Topics (overridable from the launch file, defaults unchanged)
        self.input_topic = rospy.get_param(
            "~input_topic", "/natnet_ros/umh_tiago_base/pose"
        )
        self.output_topic = rospy.get_param("~output_topic", "/odom_mocap")

        self.pose_sub = rospy.Subscriber(
            self.input_topic,
            PoseStamped,
            self.pose_callback
        )

        self.odom_pub = rospy.Publisher(
            self.output_topic,
            Odometry,
            queue_size=1
        )

        # State
        self.fixed_height = None
        self.initialized = False
        self.initial_yaw = 0.0

        # Yaw smoothing buffer
        self.yaw_buffer = []

        # Fixed world-space offset if needed
        # Keep these at 0 if the marker is centered on the base
        self.offset_x = rospy.get_param("~offset_x", 0.0)
        self.offset_y = rospy.get_param("~offset_y", 0.0)

        rospy.loginfo("optitrack_pose_to_odom node started")
        rospy.loginfo("Subscribing to: %s", self.input_topic)
        rospy.loginfo("Publishing to: %s", self.output_topic)

    def pose_callback(self, msg):
        # ---------------- POSITION ----------------
        marker_x = msg.pose.position.x
        marker_y = msg.pose.position.y
        marker_z = msg.pose.position.z

        if self.fixed_height is None:
            self.fixed_height = marker_z
            rospy.loginfo(
                "Locked fixed height at %.4f",
                self.fixed_height
            )

        base_x = marker_x - self.offset_x
        base_y = marker_y - self.offset_y
        base_z = self.fixed_height

        # ---------------- ROTATION ----------------
        q = msg.pose.orientation
        quat = [q.x, q.y, q.z, q.w]

        _, _, raw_yaw = euler_from_quaternion(quat)

        # Smooth yaw slightly
        self.yaw_buffer.append(raw_yaw)

        if len(self.yaw_buffer) > 10:
            self.yaw_buffer.pop(0)

        unwrapped = np.unwrap(
            np.array(self.yaw_buffer)
        )

        smooth_yaw = float(
            np.median(unwrapped)
        )

        # Initialize reference yaw once
        if not self.initialized:
            self.initial_yaw = smooth_yaw
            self.initialized = True

            rospy.loginfo(
                "Initialized starting yaw at %.2f deg",
                math.degrees(self.initial_yaw)
            )

            return

        # Relative yaw from startup
        relative_yaw = (
            smooth_yaw -
            self.initial_yaw
        )

        relative_yaw = math.atan2(
            math.sin(relative_yaw),
            math.cos(relative_yaw)
        )

        q_out = quaternion_from_euler(
            0.0,
            0.0,
            relative_yaw
        )

        # ---------------- PUBLISH ----------------
        odom = Odometry()

        odom.header.stamp = rospy.Time.now()
        odom.header.frame_id = "odom"
        odom.child_frame_id = "base_link"

        odom.pose.pose.position.x = base_x
        odom.pose.pose.position.y = base_y
        odom.pose.pose.position.z = base_z

        odom.pose.pose.orientation.x = q_out[0]
        odom.pose.pose.orientation.y = q_out[1]
        odom.pose.pose.orientation.z = q_out[2]
        odom.pose.pose.orientation.w = q_out[3]

        self.odom_pub.publish(odom)


if __name__ == "__main__":
    try:
        PoseToOdom()
        rospy.spin()

    except rospy.ROSInterruptException:
        pass