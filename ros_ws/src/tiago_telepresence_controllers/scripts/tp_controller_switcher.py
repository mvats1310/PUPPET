#!/usr/bin/env python

import rospy
from sensor_msgs.msg import JointState
from controller_manager_msgs.srv import ListControllers, SwitchController, SwitchControllerRequest

def do_switch_controllers(start_controllers, stop_controllers, strictness):
  rospy.loginfo("Switching controllers...")
  response = switch_controllers(start_controllers=start_controllers,
                                stop_controllers=stop_controllers,
                                strictness=strictness)

  if not response.ok:
    rospy.logerror("Failed to switch controllers")
  else:
    rospy.loginfo("...done.")

def initialize():
  cs = list_controllers().controller
  start_controllers = [c.name for c in cs if c.name in tp_controllers and c.state == "stopped"]
  stop_controllers = [c.name for c in cs if c.name.replace("_controller", "_tp_controller") in tp_controllers and c.state == "running"]
  do_switch_controllers(start_controllers, stop_controllers, SwitchControllerRequest.STRICT)

def shutdown():
  cs = list_controllers().controller
  start_controllers = [c.name for c in cs if c.name.replace("_controller", "_tp_controller") in tp_controllers and c.state == "stopped"]
  stop_controllers = [c.name for c in cs if c.name in tp_controllers and c.state == "running"]
  do_switch_controllers(start_controllers, stop_controllers, SwitchControllerRequest.BEST_EFFORT)

if __name__ == "__main__":
  rospy.init_node("tp_controller_switcher")

  rospy.wait_for_message("/joint_states", JointState)
  rospy.sleep(3.0)

  rospy.wait_for_service("/controller_manager/list_controllers")
  rospy.wait_for_service("/controller_manager/switch_controller")

  list_controllers = rospy.ServiceProxy("/controller_manager/list_controllers", ListControllers)
  switch_controllers = rospy.ServiceProxy("/controller_manager/switch_controller", SwitchController)

  tp_controllers = [c.name for c in list_controllers().controller if c.name.endswith("_tp_controller")]

  initialize()
  rospy.on_shutdown(shutdown)
  rospy.spin()
