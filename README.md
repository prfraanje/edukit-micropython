# Textual Micropython Edukit Pendulum for Dynamic Control
![User interface](textual_mpy_pendulum.png)
[Micropython](https://micropython.org), [Python](https://www.python.org) and [Textual](https://textual.textualize.io/) User Interface (TUI) based control framework for the [Edukit Rotary Inverted Pendulum Control System](https://sites.google.com/view/ucla-st-motor-control/home) developed by ST Microsystems and UCLA. The micropython code is written for the STMicrosystem [Nucleo-F401RE](https://www.st.com/en/evaluation-tools/nucleo-f401re.html) the STMicrosystem [X-Nucleo IHM01A1](https://www.st.com/en/ecosystems/x-nucleo-ihm01a1.html) stepper motor board based on the [L6474](https://www.st.com/en/motor-drivers/l6474.html) stepper motor driver, that comes with the [STEVAL-EDUKIT](https://www.st.com/en/evaluation-tools/steval-edukit01.html), but can be adapted for other hardware as well.

## Dependencies
- [Micropython](https://micropython.org) [firmware for Nucleo-F401RE](https://micropython.org/download/NUCLEO_F401RE/) and [mpy-cross](https://gitlab.com/alelec/mpy_cross) tool, tested with version 1.24.0, both should have same version!
- [Python](https://www.python.org), tested with version 3.12 and 3.13
- [Textual](https://textual.textualize.io/), tested with version 0.85.1
- [aioserial](https://pypi.org/project/aioserial/), tested with version 1.3.1 (needed for nonblocking asynchronous communication with the serial interface at the python side)
- [mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html), tested with verion 1.24.0

## Installation
- Download micropython 1.24.0 [firmware for the Nucleo-F401RE](https://micropython.org/download/NUCLEO_F401RE/), select the hex-file, because it can be programmed directly by the ST-Link programmer that is on-board of the Nucleo board. Note the version! If you select another version, you need to re-crosscompile the py-files into mpy-files with the `mpy-cross` tool, or stick to working with the less efficient py-files instead of the byte-compiled and optimized mpy-files.
- This step is only needed on Windows, for programming micropython on the Nucleo-board: Download and install the [STSW-LINK009](https://www.st.com/en/development-tools/stsw-link009.html) ST-LINK, ST-LINK/V2, ST-LINK/V2-1, STLINK-V3 USB driver signed for Windows7, Windows8, Windows10 from ST Microsystems.
- Connect the Nucleo-F401RE with embedded ST-Link programmer to your PC or laptop (in the following we say PC when laptop can be read as well) with the micro-usb cable. The Nucleo-F401RE device may directly be recognized as a USB mass storage device, and copy the firmware (hex-file!) to this USB mass storage device. Then the embedded ST-Link programmer will continue to program the Nucleo-F401RE, and it will reboot into micropython. You may also press the black reset button on the Nucleo board to reset the board manually.
- If you have difficulty on Windows to flash the micropython firmware on the Nucleo board, you may want to use [STM32CubeProg](https://www.st.com/en/development-tools/stm32cubeprog.html) STM32CubeProgrammer software for all STM32, to program the Nucleo board.

- If you have not installed Python on your PC install it, and make sure you have the commands `python` and `pip` available at the [command line](https://en.wikipedia.org/wiki/Command-line_interface) (cmd or powershell in Windows, bash or zsh in Linux or Mac). For Windows you may consult [this guide](https://docs.python.org/3/using/windows.html), and if you use the python distribution from (https://python.org) make sure you select the option to add the location of `python.exe` to your `PATH`. Note, you may also need to add the `%LOCALAPPDATA%\Roaming\Python\Python312\Scripts\` (or similar!) directory to your path, so you are able to run `rshell` from the command line (if you have difficulty determining the directory do a search on `rshell.exe` in the File Explorer). For help on adding directories to the `PATH` environment variable, see e.g. [StackOverflow on how to add a folder to path environment variable in windows](https://stackoverflow.com/questions/44272416/how-to-add-a-folder-to-path-environment-variable-in-windows-10-with-screensho).
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
- Install `rhsell` (`mpfshell` and mpremote can be installed similarly):
```
pip install --user rshell
```
On Windows you may want to remove the options `--user` so that the `rshell` is directly available at the command-line in `cmd`. 
- Power up the IHM01A1 shield by plugging the power-adapter.
- Power up the Nucleo-F401RE by making a connection with your PC using the micro-usb to USB-A cable.
- Verify the serial-device port (COM-port on Windows, ttyACMx or ttyUSBx on Linux), for use with `rshell` (default `rshell` uses the `ttyACM0` device, but you may need to change that, on Windows you may also first find out under what's the COM-port number of the serial device!). You may do this using `rshell` itself (see `rshell -h` for help!):
```
rshell -l
```
If you have problems, make sure the `rshell` script is known at the command line. You may need to add `%LOCALAPPDATA%\Roaming\Python\Python312\Scripts\` (or similar!) directory to your `PATH`, see a few points back. On windows, you also may suffer from the bug in `pyreadline`, see above under [Fix bug in pyreadline on Windows to be able to use rshell](README.md#fix-bug-in-pyreadline-on-windows-to-be-able-to-use-rshell).
- Clone or download the py- and mpy-files, at the command line go to the directory (or folder) where the files are stored and copy the mpy files to the `/flash` directory on the Nucleo-F401RE (e.g. on Linux, note you may need to specify the serial-port):
```
rshell -p /dev/ttyACM0 cp *.mpy /flash/
```
or on Windows
```
rshell -p COM4 cp *.mpy /flash/
```
Recall, you are encouraged to consult `rshell -h` for a short manual on how to use `rshell`.

## Usage
- After uploading the mpy- or py-files to the microcontroller, the code can be started on the microcontroller by `import edukit_mp` at the micropython prompt, but that command is given from the Python code [edukit_pc.py](edukit_pc.py) running on the PC. Note, when renaming [edukit_mp.mpy](edukit_mp.py) by `main.mpy`, the code will automatically run on the microcontroller which may, however, lead to big trouble when there are bugs in the serial interface communication, because after each reset the buggy code is started again and the serial interface may not be available by tools such as `rshell`, `mpremote` or `mpfshell` to copy good code and a full re-flashing of the firmware may even be needed. Also note, that micropython gives prevalence to py-files over mpy-files. So if you upload an mpy-file make sure you remove the py-file with the same name from the `/flash` directory in on the micropython board. 
- Before proceeding, open [edukit_pc.py](edukit_pc.py) (note the subscript `_pc` indicating it runs on the PC) and scroll downwards almost at the end of the file within the statement `if __name__ == "__main__"` and make sure the variable `serial_port` has the correct name of the serial-port of the microcontroller on your operating system (e.g. `COM4` on Windows, `/dev/ttyACM0` or `/dev/ttyUSB0` on Linux).
- After that, from the command line or from your Python IDE run the code [edukit_pc.py](edukit_pc.py):
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
Note, that only single line commands are allowed (the REPL is not a multi-line input REPL is the standard for Python REPL's), so you can enter
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
You can try, but you will get an exception. Exceptions are fed back to the user, but you can continue using the `-> ` REPL. If you really want to have a multi-line REPL, fork and adjust the code, e.g. by replacing the `ainput` function by the `prompt_async` function in the PromptSession class of [python-prompt-toolkit]https://github.com/prompt-toolkit/python-prompt-toolkit), see [asyncio-prompt.py](https://github.com/prompt-toolkit/python-prompt-toolkit/blob/master/examples/prompts/asyncio-prompt.py).

## Control
The edukit has two sensor values (see the function `get_both_sensors()` in [edukit_mp.py](edukit_mp.py) that are the input to the dynamic feedback controller. The first one is the number of microsteps of the stepper-motor (for details see the function `get_abs_pos_efficient` in the file [uL6474.py](uL6474.py)) and the encoder value that measures the angle of the pendulum (for details see the definition of the `Encoder` object `enc` in [edukit_mp.py](edukit_mp.py) and the definition of the `Encoder` class in [uencoder.py](uencoder.py)). You can obtain these values, e.g., by entering
```
mp get_abs_pos_efficient()
mp enc.value()
```
at the `-> ` Python prompt.

The class `PID2` defined in [ucontroller.py](ucontroller.py) provides two PID controllers labeled 1 for feedback of the stepper-motor microsteps and 2 for feedback of the pendulum encoder. To get the PID parameters of the edukit-controller, you can do
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

Because it is a bit tedious to give commands for each individual gain, the Python file [edukit_pc.py](edukit_pc.py) has defined some convenience functions: `get_pid` and `set_pid`. These functions, however, are so called asynchronous functions, because these are defined by `async def` rather than by just `def`. This is necessary, because these functions communicate with the serial-interface through the asynchronous function `ser_eval` that is non-blockingly called by "awaiting". Doing so, enables the Python interpreter to rapidly switch tasks between the plotter, the serial-interface and the REPL, so it looks like these are running in parallel (note, the real plotting is done in another process, the `plot_process` that really runs simultaneously, for more details see e.g. [Multiprocessing-vs-multithreading-vs-asyncio](https://stackoverflow.com/questions/27435284/multiprocessing-vs-multithreading-vs-asyncio) on StackOverflow). Therefore, to run `get_pid` and `set_pid` we also have to await them:
```
await get_pid()
await set_pid(0.001,0.0,0.0001,1)
```
Note, these functions are (initially) evaluated on the PC, though they lead to evaluations on the microcontroller, so do not prefix them with `mp `. See the definitions of the functions in [edukit_pc.py](edukit_pc.py) for more details on their operation.

## Introduction to the control code 
In the file [edukit_mp.py](edukit_mp.py) the controller object `pid` is defined (using the `PID2` class defined in [ucontroller.py](ucontroller.py)), which is given as an argument to the `control` task in the asynchronous function `main()`. The [control](https://github.com/prfraanje/edukit-micropython/blob/008c3d5f00a262ea5f277ed561225889d4ec3746/edukit_mp.py#L92C1-L92C1) function has `controller`, such as the `pid` in `main()`, as argument.

https://github.com/prfraanje/edukit-micropython/blob/a35ed6c27966aff251406618f62f111b2bf783a2/edukit_mp.py#L92-L109


In this function you see many references to the dictionary `supervisory` defined in the beginning of [edukit_mp.py](edukit_mp.py), that gives room for various supervisory control flags and data acquisition.

https://github.com/prfraanje/edukit-micropython/blob/a35ed6c27966aff251406618f62f111b2bf783a2/edukit_mp.py#L28-L46

The `lock` is currently not used, but can be used when there is a risk of two asynchronous tasks that inentendedly change values in the dictionary almost simultaneously. The 'counter' is a value increased every sampling instant, i.e., every iteration through the loop `while supervisory['control']` in the async function `control`. The value of `supervisory['control']` is a Boolean that is usually `True` but can be set to `False` to end the `control` task. For example this is done in the `repl` function in [urepl.py](urepl.py), when it receives the string `b'stop'` while reading streams from standard input.

## Brief explanation of the main flow of the code


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
