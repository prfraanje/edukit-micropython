import micropython
from micropython import const
from machine import Pin
from pyb import Timer, freq
from time import sleep_ms, sleep_us, ticks_us
from random import random
import gc
import array

import asyncio

from uencoder import Encoder
from ucontrol import PID2
from uL6474 import *
from urepl import repl

gc.threshold(50000) # total is about 61248

ctrlparam = {}
ctrlparam['sampling_time_ms'] = 10
ctrlparam['Kp'] = 0.
ctrlparam['Ki'] = 0.
ctrlparam['Kd'] = 0.
ctrlparam['Kp1'] = 0.
ctrlparam['Ki1'] = 0.
ctrlparam['Kd1'] = 0.
ctrlparam['Kp2'] = 0.
ctrlparam['Ki2'] = 0.
ctrlparam['Kd2'] = 0.

supervisory = {}
s = supervisory # make alias for easier reference in repl
supervisory['lock'] = asyncio.Lock()
supervisory['counter'] = 0
supervisory['control'] = True # False to stop controller task
supervisory['record'] = False
supervisory['record_ready'] = False
supervisory['record_num_samples'] = 200
supervisory['record_counter'] = 0
#supervisory['record_data'] = [[0,0,0.] for _ in range(supervisory['record_num_samples'])]
supervisory['record_data'] = [
    array.array('i',[0 for _ in range(supervisory['record_num_samples'])]),
    array.array('i',[0 for _ in range(supervisory['record_num_samples'])]),
    array.array('f',[0. for _ in range(supervisory['record_num_samples'])]),
    ]
supervisory['reference_add'] = False
supervisory['reference_repeat'] = True
supervisory['reference_counter'] = 0
supervisory['reference_num_samples'] = supervisory['record_num_samples']
supervisory['reference_sequence'] = array.array('f',[0. for _ in range(supervisory['reference_num_samples'])])
supervisory['control_add'] = False
supervisory['control_repeat'] = True
supervisory['control_counter'] = 0
supervisory['control_num_samples'] = supervisory['record_num_samples']
supervisory['control_sequence'] = array.array('f',[0. for _ in range(supervisory['control_num_samples'])])


pid = PID2(get_both_sensors,set_period_direction,ctrlparam['sampling_time_ms'],ctrlparam['Kp1'],ctrlparam['Ki1'],ctrlparam['Kd1'],ctrlparam['Kp2'],ctrlparam['Ki2'],ctrlparam['Kd2'],0,0,0,0,0,0,2**16,2**16,False,True,True,supervisory)



def set_control_sequence(std_noise=0.,height1=0.,height2=0.,duration=100):
    for i in range(supervisory['control_num_samples']):
        if i < duration:
            supervisory['control_sequence'][i] = 1.*height1 + std_noise*random()
        else:
            supervisory['control_sequence'][i] = 1.*height2 + std_noise*random()

def set_reference_sequence(std_noise=0.,height1=0.,height2=0.,duration=100):
    for i in range(supervisory['reference_num_samples']):
        if i < duration:
            supervisory['reference_sequence'][i] = 1.*height1 + std_noise*random()
        else:
            supervisory['reference_sequence'][i] = 1.*height2 + std_noise*random()

            
async def control(controller):
    while supervisory['control']:
        await controller.control()
        #async with supervisory['lock']:
        supervisory['counter'] += 1
        if supervisory['record']:
            if supervisory['record_counter'] >= supervisory['record_num_samples']:
                supervisory['record'] = False
                supervisory['record_counter'] = 0
                supervisory['record_ready'] = True
            else:
                supervisory['record_ready'] = False
                supervisory['record_data'][0][supervisory['record_counter']] = controller.sample[0]
                supervisory['record_data'][1][supervisory['record_counter']] = controller.sample[1]
                supervisory['record_data'][2][supervisory['record_counter']] = controller.sample[2]
                supervisory['record_counter'] += 1

        await asyncio.sleep_ms(controller.sampling_time_ms)

def get_both_sensors():
    steps = get_abs_pos_efficient() #get_param()
    enc_value = enc.value()
    return [steps, enc_value]

        
async def main():
    control_task = asyncio.create_task(control(pid))
    # put repl_task at end, because it will cancel the other tasks on exit
    repl_task = asyncio.create_task(repl(globals(),[control_task]))
    await asyncio.gather(control_task, repl_task)
    
    
# D4 en D5
Encoder_A_pin = 'D5' # pin 6 on CN5 = PB4 STM pin, pin 27 on CN10, 
Encoder_B_pin = 'D4' # pin 5 on CN5 = PB5 STM pin, pin 29 on CN10
enc_A = Pin(Encoder_A_pin,Pin.IN,Pin.PULL_UP)
enc_B = Pin(Encoder_B_pin,Pin.IN,Pin.PULL_UP)
enc = Encoder(enc_A,enc_B)

set_control_sequence(1.,10.,-10.,100)
set_reference_sequence(0.,20.,-20.,100)

# initialize L6474:
set_default()
# enable L6474
enable()
set_period_direction(0)
# run tasks
asyncio.run(main())

# clean up
disable()
    
