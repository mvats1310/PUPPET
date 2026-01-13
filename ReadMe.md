# PUPPET 🧠🤖🎮  
**PUPPET = a cyber-physical VR lab that lets you control TIAGo from Unity, collect data, and run repeatable experiments (VR ↔ ROS ↔ Robot / Gazebo).**

This README is written **ultra-step-by-step** (the “I can do this half-asleep” edition). It includes **terminal commands, launch flow, networking gotchas, and run modes**.

---

## Table of contents
- [What PUPPET is](#what-puppet-is)
- [What you need](#what-you-need)
- [Repo layout (what each folder is)](#repo-layout-what-each-folder-is)
- [Big picture architecture](#big-picture-architecture)
- [Machines + network](#machines--network)
- [Install & setup](#install--setup)
  - [ROS Noetic workspace setup](#ros-noetic-workspace-setup)
  - [Unity setup](#unity-setup)
  - [Quest / Android build setup](#quest--android-build-setup)
- [How to run (3 modes)](#how-to-run-3-modes)
  - [Mode A: Gazebo (simulation)](#mode-a-gazebo-simulation)
  - [Mode B: Real TIAGo + Unity Teleop](#mode-b-real-tiago--unity-teleop)
  - [Mode C: Offline analysis (thesis / logs)](#mode-c-offline-analysis-thesis--logs)
- [Launch file flow (what starts what)](#launch-file-flow-what-starts-what)
- [Controllers: why they “swap” (and when)](#controllers-why-they-swap-and-when)
- [Common checks (copy-paste friendly)](#common-checks-copy-paste-friendly)
- [Troubleshooting cheatsheet](#troubleshooting-cheatsheet)
- [Safety notes (don’t bonk the robot)](#safety-notes-dont-bonk-the-robot)
- [FAQ](#faq)

---

## What PUPPET is
PUPPET is a **VR ↔ Robotics bridge**:
- You see/control a TIAGo **digital twin in Unity**
- Unity sends commands to ROS (via **ROS–TCP–Connector**)
- ROS drives either:
  - **Gazebo simulation**, or
  - **Real TIAGo**
- You log data for experiments (timings, errors, personalization clicks, trajectories, etc.)

Think: **“VR remote lab”** + **repeatable experiments** + **teleoperation**.

---

## What you need

### Hardware (typical)
- **Quest 2/3** (or PCVR headset)
- A computer running **Unity**
- A computer running **ROS Noetic** (often a lab mini-PC)
- Optional: Real **PAL Robotics TIAGo**

### Software (typical)
- **Ubuntu 20.04 + ROS Noetic** (recommended for TIAGo stacks)
- **Unity 2022.3 LTS** (URP)
- Unity packages:
  - **ROS–TCP–Connector**
  - XR plugins (OpenXR)
- Tools you’ll use all the time:
  - `git`
  - `catkin_tools` (`catkin build`)
  - `roslaunch`, `rostopic`, `rosnode`, `rqt_graph`

---

## Repo layout (what each folder is)
> Your repo may differ, but PUPPET typically looks like this:

