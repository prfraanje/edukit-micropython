MPY_HOME = ~/micropython
MPY_CROSS = $(MPY_HOME)/mpy-cross/build/mpy-cross
#OPT = -march=armv7emsp -O3 -X emit=native
OPT = -march=armv7emsp -O3 -X emit=bytecode
MPREMOTE = $(MPY_HOME)/tools/mpremote/mpremote.py
RSHELL = rshell -p /dev/ttyACM0 -b 115200 

all: mpy_edukit.mpy  ucontrol.mpy  uencoder.mpy  uL6474.mpy  urepl.mpy mpy_repl_example.mpy


mpy_edukit.mpy: mpy_edukit.py
	$(MPY_CROSS) $(OPT) -- $<

ucontrol.mpy: ucontrol.py
	$(MPY_CROSS) $(OPT) -- $<

uencoder.mpy: uencoder.py
	$(MPY_CROSS) $(OPT) -- $<

uL6474.mpy: uL6474.py
	$(MPY_CROSS) $(OPT) -- $<

urepl.mpy: urepl.py
	$(MPY_CROSS) $(OPT) -- $<

mpy_repl_example.mpy: mpy_repl_example.py
	$(MPY_CROSS) $(OPT) -- $<

deploy: 
#	$(MPREMOTE) fs cp edukit_mp.mpy :
#	$(MPREMOTE) fs cp ucontrol.mpy :
#	$(MPREMOTE) fs cp uencoder.mpy :
#	$(MPREMOTE) fs cp uL6474.mpy :
#	$(MPREMOTE) fs cp urepl.mpy :

	$(RSHELL) cp mpy_edukit.mpy /flash/
	$(RSHELL) cp ucontrol.mpy /flash/
	$(RSHELL) cp uencoder.mpy /flash/
	$(RSHELL) cp uL6474.mpy /flash/
	$(RSHELL) cp urepl.mpy /flash/


erase:
#	$(MPREMOTE) fs rm :edukit_mp.mpy
#	$(MPREMOTE) fs rm :ucontrol.mpy
#	$(MPREMOTE) fs rm :uencoder.mpy
#	$(MPREMOTE) fs rm :uL6474.mpy
#	$(MPREMOTE) fs rm :urepl.mpy

	$(RSHELL) rm /flash/mpy_edukit.mpy
	$(RSHELL) rm /flash/ucontrol.mpy
	$(RSHELL) rm /flash/uencoder.mpy
	$(RSHELL) rm /flash/uL6474.mpy
	$(RSHELL) rm /flash/urepl.mpy

erase_default:
#	$(MPREMOTE) fs rm :boot.mpy
#	$(MPREMOTE) fs rm :main.mpy

	$(RSHELL) rm /flash/boot.mpy
	$(RSHELL) rm /flash/main.mpy

pikchr: architecture.svg

architecture.svg: ./img/architecture.pikchr
	pikchr-cli ./img/architecture.pikchr > ./img/architecture.svg


clean:
	rm *.mpy
