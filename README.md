# Edukit Micropython
[Micropython](https://micropython.org) and [Python](https://www.python.org) based control framework for the [Edukit Rotary Inverted Pendulum Control System](Edukit Rotary Inverted Pendulum Control System) developed by ST Microsystems and UCLA. The micropython code is written for the STMicrosystem [Nucleo-F401RE](https://www.st.com/en/evaluation-tools/nucleo-f401re.html) the STMicrosystem [X-Nucleo IHM01A1](https://www.st.com/en/ecosystems/x-nucleo-ihm01a1.html) stepper motor board based on the [L6474](https://www.st.com/en/motor-drivers/l6474.html) stepper motor driver, that come with the [STEVAL-EDUKIT](https://www.st.com/en/evaluation-tools/steval-edukit01.html), but can be adapter for other hardware as well.

## Dependencies
- [Micropython](https://micropython.org) [firmware for Nucleo-F401RE](https://micropython.org/download/NUCLEO_F401RE/) and [mpy-cross](https://gitlab.com/alelec/mpy_cross) tool, tested with version 1.20.0, both should have same version!
- [Python](https://www.python.org), tested with version 3.10
- [aioserial](https://pypi.org/project/aioserial/), tested with version 1.3.1 (needed for nonblocking asynchronous communication with the serial interface at the python side)
- [numpy](https://numpy.org/), tested with version 1.21.5, this dependency is not a strong one and may be replaced by lists or array.array objects.
- [matplotlib](https://numpy.org/), tested with version 3.5.1, this dependency is not a strong one and may be replaced by some other plotting tool such as [pyqtgraph](https://www.pyqtgraph.org).
- [rshell](https://github.com/dhylands/rshell) (Linux) or [mpfshell](https://github.com/wendlers/mpfshell) (Windows), for copying micropython code (py-script and/or mpy-bytecode) to microcontroller and basic debugging through a repl bypassing the serial interface to the Python code running on the PC / laptop. You may also try [mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html) the standard micropython tool for communicating with the micropyton device over a serial interface, but in my case it was not very stable in connecting with my Nucleo-F401RE board.

## Installation
- Download micropython 1.20.0 [firmware for the Nucleo-F401RE]((https://micropython.org/download/NUCLEO_F401RE/), note the version! If you select another version, you need to re-crosscompile the py-files into mpy-files with the `mpy-cross` tool, or stick to working with the less efficient py-files instead of the byte-compiled and optimized mpy-files. Connect the Nucleo-F401RE with embedded ST-Link programmer to your PC or laptop (in the following we say PC when laptop can be read as well) with the micro-usb cable. The Nucleo-F401RE device may directly be recognized as a USB mass storage device, and copy the firmware to this USB mass storage device. Then the embedded ST-Link programmer will continue to program the Nucleo-F401RE, and it will reboot into micropython. You may also press the black reset button on the Nucleo board to reset the board manually.
- If you have not installed Python on your PC install it, and make sure you have the commands `python` and `pip` available at the [command line](https://en.wikipedia.org/wiki/Command-line_interface) (cmd or powershell in Windows, bash or zsh in Linux or Mac). For Windows you may consult [this guide](https://docs.python.org/3/using/windows.html).
- At the command line (in the following we refer to command line when referring to cmd or powershell in Windows and a terminal running e.g. bash in Linux or Mac), and install aioserial for the current user with the following command:
'''
pip install --user aioserial
'''
- If numpy and matplotlib are not installed yet, install them by
'''
pip install --user numpy, matplotlib
'''
- Install rhsell on Linux or mpfshell on Windows using pip (mpfshell and mpremote can be installed similarly):
'''
pip install --user rshell
'''
- Clone or download the py- and mpy-files, at the command line go to the directory (or folder) where the files are stored and copy the mpy files to the `/flash` directory on the Nucleo-F401RE:
'''
rshell cp edukit_mp.mpy /flash
rshell cp ucontroller.mpy /flash
rshell cp uencoder.mpy /flash
rshell cp uL6474.mpy /flash
rshell cp urepl.mpy /flash
'''
on Linux  or use [mpfshell](https://github.com/wendlers/mpfshell) on Windows that may work similarly (need to find out this).


## Usage




