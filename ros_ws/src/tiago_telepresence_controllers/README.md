# tiago_telepresence_controllers

Joint controllers for telepresence applications on TIAGo and TIAGo++.

## Dependencies

This project depends on the [ros_tcp_endpoint](https://github.com/Unity-Technologies/ROS-TCP-Endpoint) package. On the VR headset side (tested: Meta Quest 2), you will need to install the [tiago-unity-vr](https://github.com/roboticslab-uc3m/tiago-unity-vr) project.

## Running in simulation

We recommend [rocker](https://github.com/osrf/rocker) and a NVIDIA GPU. It is assumed that you have cloned this repository inside your current working directory (along with ros_tcp_endpoint).

Since the TIAGo++ image also contains packages for the single-arm TIAGo, we recommend pulling the former:

```
rocker --port 10000:10000 --port 5005:5005 \
       --nvidia --x11 --privileged \
       --volume $PWD/tiago_telepresence_controllers:/tiago_dual_public_ws/src/tiago_telepresence_controllers \
       --volume $PWD/ROS-TCP-Endpoint:/tiago_dual_public_ws/src/ROS-TCP-Endpoint \
       -- palroboticssl/tiago_dual_tutorials:noetic
```

If you wish to preserve the container, which is most useful for developing, the `--nocleanup` option must be added to the `rocker` command. However, the second run won't be successful if temporary files are not reused. To achieve that, they need to be persisted in a non-temporary directory and shared with the container.

The invocation would change to:

```
mkdir -p $HOME/.tmp-tiago && TMPDIR=$HOME/.tmp-tiago \
rocker --nocleanup \
       --port 10000:10000 --port 5005:5005 \
       --nvidia --x11 --privileged \
       --env TMPDIR=/tmp-tiago \
       --volume $PWD/tiago_telepresence_controllers:/tiago_dual_public_ws/src/tiago_telepresence_controllers \
       --volume $PWD/ROS-TCP-Endpoint:/tiago_dual_public_ws/src/ROS-TCP-Endpoint \
       --volume $HOME/.tmp-tiago:/tmp-tiago \
       -- palroboticssl/tiago_dual_tutorials:noetic
```

To build the package: `catkin build tiago_spnav_telepresence`.

### For single-arm TIAGo

```
roslaunch tiago_spnav_telepresence tiago_gazebo.launch
```

### For dual-arm TIAGo++

```
roslaunch tiago_spnav_telepresence tiago_dual_gazebo.launch
```

## Running on the real robot

Upload the project to your active workspace and build it using the `deploy.py` script (but without deploying it yet):

```
rosrun pal_deploy deploy.py -u pal -p tiago_telepresence_controllers $(hostname)
```

Press `n` when asked to rsync, then copy the command displayed at the bottom, replace `pal` with `root`, and run it. Make sure to reboot the robot at least once in order to let ROS find the plugin library at the next start.

### For single-arm TIAGo

After you `ssh` into the robot:

```
roslaunch tiago_telepresence_controllers tiago_real.launch
```

### For dual-arm TIAGo++

After you `ssh` into the robot:

```
roslaunch tiago_telepresence_controllers tiago_dual_real.launch
```

## Citation

If you found this project useful, please consider citing the following work:

Łukawski, B., et al, "Towards the development of telepresence applications with TIAGo and TIAGo++ using a virtual reality headset," in IEEE Int. Conf. on Autonomous Robot Systems and Competitions (ICARSC), 2025.

```bibtex
@inproceedings{lukawski2025icarsc,
    author={Łukawski, Bartek and Montesino, Ignacio and Oña, Edwin Daniel and Victores, Juan G. and Balaguer, Carlos and Jardón, Alberto},
    title={{Towards the development of telepresence applications with TIAGo and TIAGo++ using a virtual reality headset}},
    booktitle={Int. Conf. on Autonomous Robot Systems and Competitions (ICARSC)},
    year={2025},
    organization={IEEE},
    doi={10.1109/ICARSC65809.2025.10970173}
}
```

## See also

- [demo presentation (YouTube)](https://youtu.be/fTSV94tmdCE)
- [roboticslab-uc3m/tiago-unity-vr](https://github.com/roboticslab-uc3m/tiago-unity-vr)
- [roboticslab-uc3m/tiago_spnav_teleop](https://github.com/roboticslab-uc3m/tiago_spnav_teleop)
