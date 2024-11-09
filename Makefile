MPY_HOME = ~/micropython
MPY_CROSS = $(MPY_HOME)/mpy-cross/build/mpy-cross
OPT = -march=armv7emsp -O3 -X emit=native
MPREMOTE = $(MPY_HOME)/tools/mpremote/mpremote.py

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
	$(MPREMOTE) fs cp edukit_mp.mpy :
	$(MPREMOTE) fs cp ucontrol.mpy :
	$(MPREMOTE) fs cp uencoder.mpy :
	$(MPREMOTE) fs cp uL6474.mpy :
	$(MPREMOTE) fs cp urepl.mpy :

erase:
	$(MPREMOTE) fs rm :edukit_mp.mpy
	$(MPREMOTE) fs rm :ucontrol.mpy
	$(MPREMOTE) fs rm :uencoder.mpy
	$(MPREMOTE) fs rm :uL6474.mpy
	$(MPREMOTE) fs rm :urepl.mpy

clean:
	rm *.mpy
