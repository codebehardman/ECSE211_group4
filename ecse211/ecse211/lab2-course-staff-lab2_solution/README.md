# Lab 2 - Sensors and Testing

_Read this entire document before doing anything._

In this lab, we will test the robot sensors to learn how they can be used in an
application, eg, a musical instrument.
For lab objectives, demo and report requirements, submission instructions, and
deadlines, see detailed instructions on MyCourses.

If you need help, please post on the discussion board or contact your
mentor TA.

## Updates and corrections

We will post any updates, corrections, and
clarifications to the starter code or these instructions on
[this page](https://mcgill-dpm.github.io/website/Corrections).
Please check it regularly.

## Setup

As mentioned in class, you will have two options for developing code for the robot:

- **Option 1: Simple Setup.** With this option, you will work on the robot directly,
using NoMachine and Thonny.
This is the recommended approach for beginners since the setup is simpler.
  
  <!-- TODO Course Staff: update the MyCourses link each semester. -->
  Setup instructions for using NoMachine are provided in the
  [Getting Started Guide](https://mcgill-dpm.github.io/website/GettingStarted-F21#connecting-to-the-brick).
  Once you have connected to the robot, use a private browsing window to go to
  [MyCourses](https://mycourses2.mcgill.ca/d2l/home/556943) and download
  the zip file containing the starter code to the `ecse211` folder.
  Right-click on the zip file and select "Extract Here".

  When you are ready to submit your code, right-click on the `Lab2` folder
  and select "Compress" and pick a location to save the zip file.
  Upload the zip file to the Lab 2 submission folder on MyCourses.

- **Option 2: Flexible Setup.** With this option, you develop your code in an advanced
IDE such as VS Code on your computers and send it to the robot.
This is recommended for more experienced students as it offers greater flexibility,
since all three members can work on the lab in parallel.
Setup details for this option are provided [here](flexible-setup.md).

If you are unsure which option to choose, pick Option 1.
If you have issues with NoMachine, contact your mentor TA for assistance, and
consider Option 2 as a backup option.

___

**In both cases, also do the following:**

**On the brick:** Double-click `robot_setup.sh` and select "Run in terminal"
to install the simpleaudio library.

**On your computer:** Run this command in the terminal to install
matplotlib, a library for plotting graphs:

```
python3 -m pip install matplotlib
```

___

## Project Organization

In this section, we go over the files and folders included in this lab,
listed in alphabetical order.
The files you need to modify are shown in **bold**.

- `data_analysis`
  - [`us_sensor_cont_visualization.py`](data_analysis/us_sensor_cont_visualization.py):
  visualize the distance measurements
  collected by the ultrasonic sensor. Run this on your computer.
  You are allowed to modify this file, eg, to change the plot color,
  but you are not required to.
  - [`color_sensor_visualization.py`](data_analysis/color_sensor_visualization.py):
  visualize the color measurements collected by the color sensor as
  RGB intensity Gaussian distributions, as shown in class. Run this on your computer.
- `lib`: contains the simpleaudio sound library.
- `project`: all Python files in this folder run on the robot.
  - [`doc`](project/doc): documentation for the brick API
  (Application Programming Interface), ie, the classes and functions
  you can use to work with the robot.
  - [`utils`](project/utils): brick-related utilities for this project.
  See the other project files to see examples of how to use these modules.
    - `brick.py`: the main module for interacting with the brick hardware.
    - `sound.py`: module that allows you to play sounds.
    It depends on the simpleaudio library.
  - [**`collect_color_sensor_data.py`**](project/collect_color_sensor_data.py):
  a script to collect data from the color sensor.
  **Complete the function definition in this file.**
  - [**`collect_us_sensor_data.py`**](project/collect_us_sensor_data.py):
  a script to collect data from the ultrasonic sensor.
  **Just use this file to collect data. It is complete.**
  - [**`speaker_button.py`**](project/speaker_button.py):
  a script to play music when the speaker button is pressed.
  **Complete the function definition in this file.**
- `scripts`:
  - `reset_brick.py`: If your program does not exit correctly, eg,
  if you are stuck in an infinite loop, run this script on the brick to reset it.
- `deploy_to_robot.py`: a script to deploy the code to the robot from your computer.
  It offers the following options:
  - Deploy DPM Project on Robot without running:
  copy the `lab2` folder to the robot.
  - Deploy and run DPM Project on Robot:
  copy the `lab2` folder to the robot and run the file specified
  in `project_info.json`.
  - Reset Robot: reset the robot.
- **`project_info.json`**: a file containing information about the project.
- `robot_setup.sh`: a script to install the simpleaudio library on
the brick as described above.

