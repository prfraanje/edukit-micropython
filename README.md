# Textual Micropython Edukit Pendulum for Dynamic Control
![User interface](./img/textual_mpy_edukit.png)
[Micropython](https://micropython.org), [Python](https://www.python.org) and [Textual](https://textual.textualize.io/) User Interface (TUI) based control framework for the [Edukit Rotary Inverted Pendulum Control System](https://sites.google.com/view/ucla-st-motor-control/home) developed by ST Microsystems and UCLA. The micropython code is written for the STMicrosystem [Nucleo-F401RE](https://www.st.com/en/evaluation-tools/nucleo-f401re.html) the STMicrosystem [X-Nucleo IHM01A1](https://www.st.com/en/ecosystems/x-nucleo-ihm01a1.html) stepper motor board based on the [L6474](https://www.st.com/en/motor-drivers/l6474.html) stepper motor driver, that comes with the [STEVAL-EDUKIT](https://www.st.com/en/evaluation-tools/steval-edukit01.html), but can be adapted for other hardware as well.


## Installation
1. Clone the repository by the following command in the terminal (e.g. Windows: `Win-r` then enter `cmd` or `Win-x` and select Terminal; Ubuntu: `Ctl-Alt-t`):
   ```
   git clone https://github.com/prfraanje/edukit-micropython
   ```
   or download the zip-file from the green `<> Code` button on the github repository.

2. If you have not installed Python on your PC install it, and make sure you have the commands `python` and `pip` available at the [command line](https://en.wikipedia.org/wiki/Command-line_interface) (cmd or powershell in Windows, bash or zsh in Linux or Mac). For Windows you may consult [this guide](https://docs.python.org/3/using/windows.html), and if you use the python distribution from (https://python.org) make sure you select the option to add the location of `python.exe` to your `PATH`. Note, you may also need to add the `%LOCALAPPDATA%\Roaming\Python\Python312\Scripts\` (or similar!) directory to your path, so you are able to run `rshell` from the command line (if you have difficulty determining the directory do a search on `rshell.exe` in the File Explorer). For help on adding directories to the `PATH` environment variable, see e.g. [StackOverflow on how to add a folder to path environment variable in windows](https://stackoverflow.com/questions/44272416/how-to-add-a-folder-to-path-environment-variable-in-windows-10-with-screensho).

3. Install the dependencies by the following command in the terminal (in the following we leave out "in the terminal", because the terminal will be used all over again):
   ``` 
   pip install -r requirements.txt
   ```
   this installs the python modules that are necessary on the PC side.

4. On Windows it may be needed to install the [STSW-LINK009](https://www.st.com/en/development-tools/stsw-link009.html) ST-LINK, ST-LINK/V2, ST-LINK/V2-1, STLINK-V3 USB driver signed for Windows7, Windows8, Windows10 from ST Microsystems.

5. On the microcontroller Micropython (we used v1.24), see [Micropython for NUCLEO_F401RE](https://micropython.org/download/NUCLEO_F401RE/), should be flashed (this can be done easily by copying the `hex`-file to the usb-drive that appears when connecting the microcontroller with the PC, alternatives are using the python IDE [Thonny](https://thonny.org), compiling micropython from source, etc.).

6. Copy the files
   ```
   uL6474.py
   uencoder.py
   ucontrol.py
   urepl.py
   mpy_edukit.py
   ```
   or preferably their compiled (`mpy`) versions (see below)
   ```
   uL6474.mpy
   uencoder.mpy
   ucontrol.mpy
   urepl.mpy
   mpy_edukit.mpy
   ```
   to the `/flash` folder on the microcontroller. There are several tools to do this: `mpremote`, `rshell`, etc. Under Windows I was not able to run these tools succesfully, and one better uses  [Thonny](https://thonny.org), in which one can copy files from and to the microcontroller. Under Linux (or WSL), one simply does
   ``` 
   make deploy
   ```

7. Make sure the files `boot.py` and `main.py` are removed from the microcontroller, on Linux:
   ``` 
   make erase_default
   ```

8. Run the Textual Micropython Edukit Dynamic Pendulum Control user interface with
   ``` 
   python textual_mpy_edukit.py
   ```

## Usage
1. If everything is fine, you should see the screen similar as the picture above, and repeated here:
![User interface](./img/textual_mpy_edukit.png)
You may need to increase your terminal size. Since  [Textual](https://textual.textualize.io/) makes use of Unicode (UTF-8) characters on Windows 10 and older versions not all characters are displayed correctly. One may try to evaluate the command `chcp 650100` before running `python textual_mpy_edukit.py`, or just live with the imperfection.

2. In the center you see two plot windows. The upper one shows the sensors: 
   * the steps of the stepper motor in blue, that is retrieved in micropython by evaluating `stepper.get_abs_pos_efficient()`
   * the ticks of the encoder in green, that is retrieved in micropython  by `encoder.value()`).
  
   The lower plot shows the control value, which is proportional to the frequency of the pulses send to the stepper motor by the L6474 stepper driver. In micropython this is the variable `pid.u` for the PID controller or `state_space.u` for the state-space controller, and is send to the L6474 stepper motor driver by evaluating e.g. `stepper.set_period_direction(pid.u)` (for PID).

   The samples are all stored in `pid.sample` or `state_space.sample`, and retrieved at a frequency of 20 Hz in the function `update_plots` in the class `TimeDisplay` in `textual_mpy_edukit.py` (also c.f. the attribute `self.update_timer = self.set_interval(1 / 20, self.update_time`), with the state-ment
   ``` 
   resp = await serial_eval(micropython_serial_interface,'pid.sample')
   ```
   In fact all (serial) communication between the PC and the microcontroller is handled by this function `serial_eval` in `textual_mpy_edukit.py`.

3. Below the plots there is a left and a right field: the left field contains a python prompt (bottom) and above a region that shows the output of the python interpreter. The right field is similar, but commands at the prompt are send to the microcontroller and the response is printed again above. So at the micropython prompt, e.g. one can type
   ``` 
   pid.sample
   ```
   to see the current value of respectively the stepper steps, encoder ticks and the control value. You may also inspect the other attributes of the object `pid` with
   ```
   dir(pid)
   ```
   And, note that you may get the stepper motor steps and encoder ticks by typing the following lines in the micropython prompts:
   ```
   stepper.get_abs_pos_efficient()
   encoder.value()
   ```
   Also the PID controller gains can be returned, for the feedback from the stepper steps:
   ``` 
   pid.Kp1
   pid.Ki1
   pid.Kd1
   ```
   and for PID controller feeding back the encoder ticks
   ``` 
   pid.Kp2
   pid.Ki2
   pid.Kd2
   ```
4. At the micropython prompt one can also set these parameters, e.g. by
   ```
   pid.Kp1 = 1
   ```
5. For quicker getting and setting the PID controller gains, one can use these the following get- and set-functions as well:
   ``` 
   pid.get_gains1()
   pid.get_gains2()
   pid.set_gains1(0.1,0.0001,0.001
   pid.set_gains2(0.1,0.0001,0.001
   ```
6. The reference (setpoint) value for the feedback from the stepper motor is stored in
   ```
   pid.r1
   ```
   and for the feedback from the encoder ticks, the reference is
   ``` 
   pid.r2
   ```
   So if one wants to move the stepper-motor to an angle corresponding with step value 100, one sets (besides the gains of the controller and the run-flags, see shortly below):
   ```
   pid.r1 = 100
   ```
7. Note that the prompts only allow single line input.
8. The results returned by python as well as micropython are stored in python (left field) in the variables `python_results` and `micropython_results`, so they can be accessed later when needed.
9. The vertical bar on the right contains a number of settings (radiobuttons) that are directly connected to variables on the microcontroller, e.g. to switch between PID and state-space control, to turn on/off the PID controller (`pid.run`), and to turn off/on the PID controller for the stepper motor (`pid.run1`) and the encoder (`pid.run2`).
10. The vertical bar on the left is for logging. Logging is done with two buffers on the microcontroller, that are subsequently filled 


## Introduction to the control code 

![Architecture](./img/architecture.svg)
In the file [edukit_mp.py](edukit_mp.py) the controller object `pid` is defined (using the `PID2` class defined in [ucontroller.py](ucontroller.py)), which is given as an argument to the `control` task in the asynchronous function `main()`. The [control](https://github.com/prfraanje/edukit-micropython/blob/008c3d5f00a262ea5f277ed561225889d4ec3746/edukit_mp.py#L92C1-L92C1) function has `controller`, such as the `pid` in `main()`, as argument.

https://github.com/prfraanje/edukit-micropython/blob/a35ed6c27966aff251406618f62f111b2bf783a2/edukit_mp.py#L92-L109


In this function you see many references to the dictionary `supervisory` defined in the beginning of [edukit_mp.py](edukit_mp.py), that gives room for various supervisory control flags and data acquisition.

https://github.com/prfraanje/edukit-micropython/blob/a35ed6c27966aff251406618f62f111b2bf783a2/edukit_mp.py#L28-L46

The `lock` is currently not used, but can be used when there is a risk of two asynchronous tasks that inentendedly change values in the dictionary almost simultaneously. The 'counter' is a value increased every sampling instant, i.e., every iteration through the loop `while supervisory['control']` in the async function `control`. The value of `supervisory['control']` is a Boolean that is usually `True` but can be set to `False` to end the `control` task. For example this is done in the `repl` function in [urepl.py](urepl.py), when it receives the string `b'stop'` while reading streams from standard input.

## Brief explanation of the main flow of the code


## Dependencies
- [Micropython](https://micropython.org) [firmware for Nucleo-F401RE](https://micropython.org/download/NUCLEO_F401RE/) and [mpy-cross](https://gitlab.com/alelec/mpy_cross) tool, tested with version 1.24.0, both should have same version!
- [Python](https://www.python.org), tested with version 3.12 and 3.13
- [Textual](https://textual.textualize.io/), tested with version 0.85.1
- [aioserial](https://pypi.org/project/aioserial/), tested with version 1.3.1 (needed for nonblocking asynchronous communication with the serial interface at the python side)
- [mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html), tested with verion 1.24.0


## Changing and cross-compiling the micropython code
If you change the code for the microcontroller, you should recompile the corresponding `mpy` file. You can do this with the tool `mpy-cross`. Install it with `pip`:
```
pip install --user mpy-cross
```
Then, e.g. if you change `ucontrol.py` regenerate the byte-code in `ucontrol.mpy` with, executing at the command line
```
mpy-cross -march=armv7emsp ucontrol.py
```
If you have multiple files that need to be compiled, execute the command for every file separately. You may also add optimization flags such as `-O2` or `-O3`, at the expense of the loss of informative feedback of errors. For more information, see the help: `mpy-cross --help` and online documentation such as [MicroPython .mpy files](https://docs.micropython.org/en/latest/reference/mpyfiles.html#).

Do not forget  to upload the new `.mpy` files to the microcontroller, e.g. by
```
rshell -p COM4 cp ucontrol.mpy /flash/
```
Note, that if you go for advanced stuff in maximizing for speed using the "Native" or "Viper" code emitters, as explained [here](https://docs.micropython.org/en/latest/reference/speed_python.html) you may need to compile `mpy-cross` and `micropython` yourself, such that they completely corresponds with the same version and microcontroller architecture. For more information see e.g. [MicroPython port to STM32 MCUs](https://github.com/micropython/micropython/tree/master/ports/stm32) at the micropython github. 
