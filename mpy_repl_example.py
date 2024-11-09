import micropython
from micropython import const
#from machine import Pin
#from pyb import Timer, freq
#from time import sleep_ms, sleep_us, ticks_us
#from random import random
import gc
#import array

import asyncio

from urepl import repl

gc.threshold(50000) # total is about 61248

        
async def main():
    # Start other program tasks.

    # put repl_task at end, because it will cancel the other tasks on exit
    repl_task = asyncio.create_task(repl(globals(),[]))
    
    await asyncio.gather(repl_task)

asyncio.run(main())

    
