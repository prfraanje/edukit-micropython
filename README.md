# Edukit Micropython
[Micropython](https://micropython.org) and [Python](https://www.python.org) based control framework for the [Edukit Rotary Inverted Pendulum Control System](https://sites.google.com/view/ucla-st-motor-control/home) developed by ST Microsystems and UCLA. The micropython code is written for the STMicrosystem [Nucleo-F401RE](https://www.st.com/en/evaluation-tools/nucleo-f401re.html) the STMicrosystem [X-Nucleo IHM01A1](https://www.st.com/en/ecosystems/x-nucleo-ihm01a1.html) stepper motor board based on the [L6474](https://www.st.com/en/motor-drivers/l6474.html) stepper motor driver, that comes with the [STEVAL-EDUKIT](https://www.st.com/en/evaluation-tools/steval-edukit01.html), but can be adapted for other hardware as well.

## Dependencies
- [Micropython](https://micropython.org) [firmware for Nucleo-F401RE](https://micropython.org/download/NUCLEO_F401RE/) and [mpy-cross](https://gitlab.com/alelec/mpy_cross) tool, tested with version 1.20.0, both should have same version!
- [Python](https://www.python.org), tested with version 3.10
- [aioserial](https://pypi.org/project/aioserial/), tested with version 1.3.1 (needed for nonblocking asynchronous communication with the serial interface at the python side)
- [numpy](https://numpy.org/), tested with version 1.21.5, this dependency is not a strong one and may be replaced by lists or array.array objects.
- [matplotlib](https://numpy.org/), tested with version 3.5.1, this dependency is not a strong one and may be replaced by some other plotting tool such as [pyqtgraph](https://www.pyqtgraph.org).
- [rshell](https://github.com/dhylands/rshell) (Linux and Windows, on Windows you have to correct a bug in the `pyreadline`, see below!). We need this tool for copying micropython code (py-script and/or mpy-bytecode) to microcontroller and basic debugging through a repl bypassing the serial interface to the Python code running on the PC / laptop. You may also try [mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html) the standard micropython tool for communicating with the micropyton device over a serial interface, but in my case it was not very stable in connecting with my Nucleo-F401RE board. You may also try [mpfshell](https://github.com/wendlers/mpfshell), or one of the many other tools for serial interfacing and file transfer over serial interfaces.

## Fix bug in pyreadline on Windows to be able to use rshell
`rshell` relies on the `readline` module for keyboard command input. However on Windows you may get the `AttributeError: module 'collections' has no attribute 'Callable'`. The reason is that the `Callable` module is moved from `collections` to `collections.abc`. On the Windows distribution of `pyreadline` this is not updated yet. You can correct it manually in `pyreadline` by opening the file (assuming you work with Python 3.12, or adjust accordingly):
```
%LOCALAPPDATA%\Programs\Python\Python312\Lib\site-packages\pyreadline\py3k_compat.py
```
and change `collections.Callable` on line 8 into `collections.abc.Callable`. Also see the [post](https://stackoverflow.com/questions/69515086/error-attributeerror-collections-has-no-attribute-callable-using-beautifu) on StackOverflow.

## Installation
- Download micropython 1.20.0 [firmware for the Nucleo-F401RE](https://micropython.org/download/NUCLEO_F401RE/), note the version! If you select another version, you need to re-crosscompile the py-files into mpy-files with the `mpy-cross` tool, or stick to working with the less efficient py-files instead of the byte-compiled and optimized mpy-files. Connect the Nucleo-F401RE with embedded ST-Link programmer to your PC or laptop (in the following we say PC when laptop can be read as well) with the micro-usb cable. The Nucleo-F401RE device may directly be recognized as a USB mass storage device, and copy the firmware to this USB mass storage device. Then the embedded ST-Link programmer will continue to program the Nucleo-F401RE, and it will reboot into micropython. You may also press the black reset button on the Nucleo board to reset the board manually.
- If you have not installed Python on your PC install it, and make sure you have the commands `python` and `pip` available at the [command line](https://en.wikipedia.org/wiki/Command-line_interface) (cmd or powershell in Windows, bash or zsh in Linux or Mac). For Windows you may consult [this guide](https://docs.python.org/3/using/windows.html), and if you use the python distribution from (https://python.org) make sure you select the option to add the location of `python.exe` to your `PATH`.
- At the command line (in the following we refer to command line when referring to cmd or powershell in Windows and a terminal running e.g. bash in Linux or Mac), and install aioserial for the current user with the following command:
```
pip install --user aioserial
```
The module `aioserial` is needed to enable non-blocking serial communication between the PC and micropython, while also the plotter and the repl are continueing their operation.
- If numpy and matplotlib are not installed yet, install them by
```
pip install --user numpy
pip install --user matplotlib
```
- Install rhsell (mpfshell and mpremote can be installed similarly):
```
pip install --user rshell
```
On Windows you may want to remove the options `--user` so that the `rshell` is directly available at the command-line in `cmd`.
- Power up the IHM01A1 shield by plugging the power-adapter.
- Power up the Nucleo-F401RE by making a connection with your PC using the micro-usb to USB-A cable.
- Verify the serial-device port (COM-port on Windows, ttyACMx or ttyUSBx on Linux), for use with `rshell` (default `rshell` uses the `ttyACM0` device, but you may need to change that, on Windows you may also first find out under what's the COM-port number of the serial device!)
- Clone or download the py- and mpy-files, at the command line go to the directory (or folder) where the files are stored and copy the mpy files to the `/flash` directory on the Nucleo-F401RE:
```
rshell cp edukit_mp.mpy /flash
rshell cp ucontroller.mpy /flash
rshell cp uencoder.mpy /flash
rshell cp uL6474.mpy /flash
rshell cp urepl.mpy /flash
```
Note, if this is not working, you may need to specify the serial port, e.g. by
```
rshell -p COM4 cp edukit_mp.mpy /flash
rshell -p COM4 cp ucontroller.mpy /flash
rshell -p COM4 cp uencoder.mpy /flash
rshell -p COM4 cp uL6474.mpy /flash
rshell -p COM4 cp urepl.mpy /flash
```
Also see `rshell -h` for a short manual on how to use `rshell`.

## Usage
- After uploading the mpy- or py-files to the microcontroller, the code can be started on the microcontroller by `import edukit_mp` at the micropython prompt, but that command is given from the Python code (edukit_pc.py) running on the PC. Note, when renaming `edukit_mp.mpy` by `main.mpy`, the code will automatically run on the microcontroller which may, however, lead to big trouble when there are bugs in the serial interface communication, because after each reset the buggy code is started again and the serial interface may not be available by tools such as `rshell`, `mpremote` or `mpfshell` to copy good code and a full re-flashing of the firmware may even be needed. Also note, that micropython gives prevalence to py-files over mpy-files. So if you upload an mpy-file make sure you remove the py-file with the same name from the `/flash` directory in on the micropython board. 
- Before proceeding, open `edukit_pc.py` (note the subscript `_pc` indicating it runs on the PC) and scroll downwards almost at the end of the file within the statement `if __name__ == "__main__"` and make sure the variable `serial_port` has the correct name of the serial-port of the microcontroller on your operating system (e.g. `COM4` on Windows, `/dev/ttyACM0` or `/dev/ttyUSB0` on Linux).
- After that, from the command line or from your Python IDE run the code `edukit_pc.py:
```
python edukit_pc.py
```
Note, within python you may also execute:
```
exec(open("edukit_pc.py").read())
```
- If all installations and configurations went fine, you should see a `matplotlib` figure with three axes that show plots with signals running in time: the first one of the stepper motor microsteps value, the second one of the pendulum encoder value and the last one shows the control signal, that is proportional to the PWM frequency driving the pulses to microstep the stepper-motor.
- Also, the standard Python prompt is replaced by an alternative REPL (Read Eval Print Loop), indicated by `-> `, in which you can enter Python code that will be evaluated on the PC, but also you can, by prefixing your code with `mp `, to enter code to be run by micropython on the microcontroller:
```
# run on PC:
from math import *
atan2(3,4)
# run on micropython:
mp from math import *
mp atan2(3,4)
```
Note, that only single line commands are allowed, so you can enter
```
for _ in range(10): print("Hello, from Python on PC!')
mp for _ in range(10): print("Hello, from Micropython on the microcontroller!')
```
but this is not allowed:
```
for _ in range(10):
    print("Hello, from Python on PC!')
mp for _ in range(10):
mp    print("Hello, from Micropython on the microcontroller!')
```
You can try, but you will get an exception. Exceptions are fed back to the user, but you can continue using the `-> ` REPL.

## Control
The edukit has two sensor values (see the function `get_both_sensors()` in `edukit_mp.py` that are the input to the dynamic feedback controller. The first one is the number of microsteps of the stepper-motor (for details see the function `get_abs_pos_efficient` in the file `uL6474.py`) and the encoder value that measures the angle of the pendulum (for details see the definition of the `Encoder` object `enc` in `edukit_mp.py` and the definition of the `Encoder` class in `uencoder.py`). You can obtain these values, e.g., by entering
```
mp get_abs_pos_efficient()
mp enc.value()
```
at the `-> ` Python prompt.

The class `PID2` defined in `ucontroller.py` provides two PID controllers labeled 1 for feedback of the stepper-motor microsteps and 2 for feedback of the pendulum encoder. To get the PID parameters of the edukit-controller, you can do
```
mp pid.Kp1
mp pid.Ki1
mp pid.Kd1
mp pid.Kp2
mp pid.Ki2
mp pid.Kd2
```
and of course, you can easily adjust them by (try rather small values, these do not very much):
```
mp pid.Kp1 = 0.001
mp pid.Ki1 = 0.0
mp pid.Kd1 = 0.0001
mp pid.Kp2 = 0.001
mp pid.Ki2 = 0.
mp pid.Kd2 = 0.0001
```
Don't forget to prefix with `mp `!
For other values (like `pid.sample` and `pid.run1` and `pid.run2`) consult the `PID2` class in `ucontrol.py`.

Because it is a bit tedious to give commands for each individual gain, the Python file `edukit_pc.py` has defined some convenience functions: `get_pid` and `set_pid`. These functions, however, are so called asynchronous functions, because these are defined by `async def` rather than by just `def`. This is necessary, because these functions communicate with the serial-interface through the asynchronous function `ser_eval` that is non-blockingly called by "awaiting". Doing so, enables the Python interpreter to rapidly switch tasks between the plotter, the serial-interface and the REPL, so it looks like these are running in parallel (note, the real plotting is done in another process, the `plot_process` that really runs simultaneously, for more details see e.g. [Multiprocessing-vs-multithreading-vs-asyncio](https://stackoverflow.com/questions/27435284/multiprocessing-vs-multithreading-vs-asyncio) on StackOverflow). Therefore, to run `get_pid` and `set_pid` we also have to await them:
```
await get_pid()
await set_pid(0.001,0.0,0.0001,1)
```
Note, these functions are (initially) evaluated on the PC, though they lead to evaluations on the microcontroller, so do not prefix them with `mp `. See the definitions of the functions in `edukit_pc.py` for more details on their operation.

## Control
In the file `

## Brief explanation of the main flow of the code


## Changing the micropython code

