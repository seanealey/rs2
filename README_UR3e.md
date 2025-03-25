# UR3e Robot Control with ROS 2 and MoveIt

This guide explains how to set up and control a Universal Robots UR3e using ROS 2 Humble and MoveIt.

## System Requirements

- Ubuntu 22.04
- ROS 2 Humble

## 1. Install Required Packages

Install the necessary packages from the provided links:
```bash
https://github.com/UniversalRobots/Universal_Robots_ROS2_Driver
https://github.com/UniversalRobots/Universal_Robots_ROS2_GZ_Simulation
https://moveit.picknik.ai/humble/doc/tutorials/getting_started/getting_started.html
https://github.com/ros-controls/gz_ros2_control/tree/humble
```

## 2. Set up Workspaces

### Create and Build UR Workspace

```bash
# Create the workspace
mkdir -p ~/ur_ws/src

# Clone the repositories
cd ~/ur_ws/src
git clone .... provided links above

# Build the workspace
cd ~/ur_ws
colcon build

# Source the workspace
source install/setup.bash
```


## 3. Connect to a Real UR3e Robot

### Step 1: Launch the UR Robot Driver

This command connects to the actual UR3e robot hardware:

```bash
source ~/ur_ws/install/setup.bash
ros2 launch ur_robot_driver ur_control.launch.py ur_type:=ur3e robot_ip:=192.168.0.250 launch_rviz:=false
```

Replace `192.168.0.250` with your robot's actual IP address.

### Step 2: Launch MoveIt to Control the Robot

In a new terminal:

```bash
ros2 launch ur_moveit_config ur_moveit.launch.py ur_type:=ur3e robot_ip:=192.168.0.250
```

## 4. Simulation

If you want to test without a real robot, you can use Gazebo simulation:

```bash
# Install simulation packages above

# Clone simulation repository
cd ~/ur_ws/src
git clone -b humble https://github.com/UniversalRobots/Universal_Robots_ROS2_GZ_Simulation.git

# Rebuild workspace
cd ~/ur_ws
colcon build
source install/setup.bash

# Launch simulation
ros2 launch ur_simulation_gz ur_sim_control.launch.py ur_type:=ur3e launch_rviz:=false
```

Then launch MoveIt with the simulation flag:

```bash
ros2 launch ur_moveit_config ur_moveit.launch.py ur_type:=ur3e use_sim_time:=true




ros2 launch ur_simulation_gz ur_sim_control.launch.py ur_type:=ur3e launch_rviz:=false
ros2 launch ur_moveit_config ur_moveit.launch.py ur_type:=ur3e use_sim_time:=true
ros2 run ur3e_cpp_demo ur3e_simple_control
```

## 5. Controlling the Robot

### Using RViz Interface

1. In the RViz window, find the Motion Planning panel
2. Use the interactive markers (colored arrows and rings) to position the robot's end-effector
3. Click "Plan" to generate a motion plan
4. Click "Execute" to move the robot


## 6. Useful Commands

### Check Topic Information

```bash
# List all topics
ros2 topic list

# See details of a specific topic
ros2 topic echo /joint_states

# Check topic publishing rate
ros2 topic hz /joint_states
```

### Check Robot Status

```bash
# See current controller status
ros2 control list_controllers

# Check robot state
ros2 topic echo /controller_manager/status
```

## 7. Common Issues and Solutions

### Robot Not Connecting
- Verify the robot IP address
- Check if the robot is powered on and in Remote Control mode
- Ping the robot: `ping 192.168.0.250`

### Move Group Not Planning
- Check if the robot is in an error state
- Verify joint states are being published: `ros2 topic echo /joint_states`
- Check for collisions in the planning scene

### ExtractIKSolutions iksolver cannot be constructed
- Confirm you specified the right `ur_type` parameter (ur3e)
- Ensure MoveIt and the robot driver are correctly installed

## 8. Additional Resources

- [Universal Robots ROS2 Driver GitHub](https://github.com/UniversalRobots/Universal_Robots_ROS2_Driver)
- [MoveIt Documentation](https://moveit.picknik.ai/humble/index.html)
- [ROS 2 Control Documentation](https://control.ros.org/humble/index.html)
