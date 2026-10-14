# OptiTrack to ROS Communication
This repository provides a package that allows for data communication between OptiTrack System (Motive software), ROS, and UDP  

![rosgraph](https://github.com/user-attachments/assets/b8a1ce2b-b5f6-453a-87f6-8c94bd874b68)  
*Example: ROSGraph of nodes and topics after launching `optitrack_nodes.launch`*

## Introduction
There are currently two protocol options available for using this package with Motive 3.1 software: 
### [VRPN](http://wiki.ros.org/vrpn_client_ros)
 - Easier set-up and launch
 - Fewer options/configuration
 - Avg. publishing rate: 50hz

### [NatNet](https://raw.githubusercontent.com/L2S-lab/natnet_ros_cpp)
 - Harder set-up and launch
 - More options/configuration
 - Avg. publishing rate: 120hz
 - Unicast, Multicast, and Boardcast (WIP: Multicast/Broadcast doesn't work)

Addtionally, this package contains UDP transmission capabilities (the ROS topics created will expose UDP Sockets which can be accessed by an external server).

## Set-up Option 1. NatNet:
1. Install the requirements by running the following command in your terminal:
```bash
sudo apt install -y ros-$ROS_DISTRO-tf2* wget
```
2. Clone both the `natnet_ros_cpp` and `optitrack_ros_communication` packages into your catkin workspace and build it (**NOTE**: Replace `CATKIN_WORKSPACE_NAME` with your catkin workspace directory name):
```bash
cd CATKIN_WORKSPACE_NAME/src
git clone https://github.com/L2S-lab/natnet_ros_cpp
git clone https://github.com/IE-Robotics-Lab/optitrack_ros_communication.git
cd ..
catkin_make OR catkin build
```
**NOTE**: Follow [NatNet ROS Repository](https://github.com/L2S-lab/natnet_ros_cpp) for additional guide for Motive Software settings and launch options.  

<img width="309" alt="Screenshot 2024-10-04 at 18 13 22" src="https://github.com/user-attachments/assets/a8227800-214d-4bb6-ba14-a37462b78feb">  

*Example: Motive settings for unicast connection publishing only rigid bodies*

## Set-up Option 2. VRPN:
1. Install VRPN Package into the ROS environment by running the following command in your terminal:
```bash
sudo apt install ros-$(rosversion -d)-vrpn-client-ros
```
2. Clone the `optitrack_ros_communication` package into your catkin workspace and build it (Note: Replace `CATKIN_WORKSPACE_NAME` with your catkin workspace directory name):
```bash
cd CATKIN_WORKSPACE_NAME/src
git clone https://github.com/IE-Robotics-Lab/optitrack_ros_communication.git
cd ..
catkin_make OR catkin build
```

## Run
Once the set-up is completed, simply launch the file `optitrack_nodes.launch` using the `roslaunch` command with the desired parameters (or modify the default values in the launch file). The default protocol is NatNet, but can be changed to VRPN by setting the `namespace` parameter to `optitrack`. Some examples are provided below:
```bash
# NatNet and UDP clients (default values)
roslaunch optitrack_ros_communication optitrack_nodes.launch

# VRPN and UDP clients with 10 nodes
roslaunch optitrack_ros_communication optitrack_nodes.launch number_of_nodes:=10 namespace:=optitrack

# NatNet and UDP clients with different network parameters
roslaunch optitrack_ros_communication optitrack_nodes.launch serverIP:=10.205.3.3 number_of_nodes:=2 udp_server_ip:=10.205.3.224
```
**NOTE**: The number of nodes refers to the number of rigid bodies you want to transmit via UDP.

### Additional Options
If UDP transmition is not required, you can simply disable it by setting `udp_client` to `false`:
```bash
roslaunch optitrack_ros_communication optitrack_nodes.launch udp_client:=false
```

OR launch the desired client `natnet_client.launch` or `vrpn_client.launch`:
```bash
roslaunch optitrack_ros_communication natnet_client.launch
 
roslaunch optitrack_ros_communication vrpn_client.launch
```

Inversely, if only UDP transmition is required, you can simply launch the file `udp_client.launch`:
```bash
roslaunch optitrack_ros_communication udp_client.launch
```

