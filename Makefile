MPY_HOME = ~/micropython
MPY_CROSS = $(MPY_HOME)/mpy-cross/build/mpy-cross
OPT = -march=armv7emsp -X emit=native -v
MPREMOTE = $(MPY_HOME)tools/mpremote/mpremote.py

all: edukit_mp.mpy  ucontrol.mpy  uencoder.mpy  uL6474.mpy  urepl.mpy


edukit_mp.mpy: edukit_mp.py
	$(MPY_CROSS) $(OPT) -- $<

ucontrol.mpy: ucontrol.py
	$(MPY_CROSS) $(OPT) -- $<

uencoder.mpy: uencoder.py
	$(MPY_CROSS) $(OPT) -- $<

uL6474.mpy: uL6474.py
	$(MPY_CROSS) $(OPT) -- $<

urepl.mpy: urepl.py
	$(MPY_CROSS) $(OPT) -- $<

deploy:
	$(MPREMOTE) fs cp edukit_mp.mpy :/flash/
	$(MPREMOTE) fs cp ucontrol.mpy :/flash/
	$(MPREMOTE) fs cp uencoder.mpy :/flash/
	$(MPREMOTE) fs cp uL6474.mpy :/flash/
	$(MPREMOTE) fs cp urepl.mpy :/flash/

erase:
	$(MPREMOTE) fs rm :/flash/edukit_mp.mpy
	$(MPREMOTE) fs rm :/flash/ucontrol.mpy
	$(MPREMOTE) fs rm :/flash/uencoder.mpy
	$(MPREMOTE) fs rm :/flash/uL6474.mpy
	$(MPREMOTE) fs rm :/flash/urepl.mpy

clean:
	rm *.mpy
