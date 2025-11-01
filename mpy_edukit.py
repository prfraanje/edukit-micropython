
import micropython
from micropython import const
from machine import Pin
from pyb import Timer, freq
from time import sleep_ms, sleep_us, ticks_us, ticks_diff, ticks_ms
from random import random
import gc
import array

import asyncio

from uencoder import Encoder
from ucontrol import PID, StateSpace
from uL6474 import L6474
from urepl import repl

MEMORY_THRESHOLD = const(50000) # total is about 61248

gc.threshold(MEMORY_THRESHOLD)

LOG_BUF_LEN = const(128)

stepper = L6474()

# D4 en D5
Encoder_A_pin = 'D5' # pin 6 on CN5 = PB4 STM pin, pin 27 on CN10, 
Encoder_B_pin = 'D4' # pin 5 on CN5 = PB5 STM pin, pin 29 on CN10
enc_A = Pin(Encoder_A_pin,Pin.IN,Pin.PULL_UP)
enc_B = Pin(Encoder_B_pin,Pin.IN,Pin.PULL_UP)
encoder = Encoder(enc_A,enc_B)


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
ctrlparam['A'] = [[0.,0.],[0.,0.]]
ctrlparam['B'] = [0.,0.]
ctrlparam['C'] = [0.,0.]
ctrlparam['type'] = 'pid' # can also be state_space

supervisory = {}
s = supervisory # make alias for easier reference in repl
supervisory['lock'] = asyncio.Lock()
supervisory['counter'] = 0
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
supervisory['log'] = False
supervisory['log_ready'] = True
supervisory['log_num_samples'] = 0
supervisory['log_counter'] = 0
supervisory['log0'] = False
supervisory['log1'] = False
supervisory['log0_data'] = [
    array.array('i',[0  for _ in range(LOG_BUF_LEN)]),
    array.array('i',[0  for _ in range(LOG_BUF_LEN)]),
    array.array('f',[0. for _ in range(LOG_BUF_LEN)]),
    ]
supervisory['log1_data'] = [
    array.array('i',[0  for _ in range(LOG_BUF_LEN)]),
    array.array('i',[0  for _ in range(LOG_BUF_LEN)]),
    array.array('f',[0. for _ in range(LOG_BUF_LEN)]),
    ]
supervisory['log_state'] = ''


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


@micropython.native
def get_both_sensors(stepper,encoder):
    # bind the functions
    steps_fun = stepper.get_abs_pos_efficient #get_param()
    enc_fun = encoder.value
    def fun():
        steps = steps_fun()
        enc_value = enc_fun()
        return [steps, enc_value]
    return fun


@micropython.native
async def control(controller1,controller2):
    ctrlp = ctrlparam
    supervis = supervisory
    while True:
        t0_ms = ticks_ms()
        
        if ctrlp['type'] == 'pid':
            controller = controller1
        elif ctrlp['type'] == 'state_space':
            controller = controller2
        else:
            controller = controller1 # default to pid
            
        await controller.control()
        #async with supervis['lock']:
        supervis['counter'] += 1
        if supervis['record']:
            if supervis['record_counter'] >= supervis['record_num_samples']:
                supervis['record'] = False
                supervis['record_counter'] = 0
                supervis['record_ready'] = True
            else:
                supervis['record_ready'] = False
                counter = supervis['record_counter']
                supervis['record_data'][0][counter] = controller.sample[0]
                supervis['record_data'][1][counter] = controller.sample[1]
                supervis['record_data'][2][counter] = controller.sample[2]
                supervis['record_counter'] = counter + 1

        if supervis['log']:
            log_counter = supervis['log_counter']            
            if log_counter >= supervis['log_num_samples']:
                supervis['log'] = False
                supervis['log0'] = False
                supervis['log1'] = False                
                supervis['log_counter'] = 0
                supervis['log_ready'] = True
            else:
                supervis['log_ready'] = False

                # following 2 if statements guarantee that log0 is active 0 ... LOG_BUF_LEN and log1 from LOG_BUF_LEN + 1 ... 2 * LOG_BUF_LEN
                if log_counter % LOG_BUF_LEN == 0:
                    if log_counter % (2*LOG_BUF_LEN) == 0:
                        supervis['log0'] = True
                        supervis['log1'] = False
                    else:    
                        supervis['log0'] = False
                        supervis['log1'] = True

                counter = log_counter % LOG_BUF_LEN 
                if supervis['log0']: # log buffer 0                    
                    supervis['log0_data'][0][counter] = controller.sample[0]
                    supervis['log0_data'][1][counter] = controller.sample[1]
                    supervis['log0_data'][2][counter] = controller.sample[2]                    
                elif supervis['log1']: # log buffer 1
                    supervis['log1_data'][0][counter] = controller.sample[0]
                    supervis['log1_data'][1][counter] = controller.sample[1]
                    supervis['log1_data'][2][counter] = controller.sample[2]                    
                else:
                    supervis['log_state'] = 'error: cannot log0 and log1'
                    
                supervis['log_counter'] += 1
        remaining_time = controller.sampling_time_ms - ticks_diff(ticks_ms(),t0_ms)
        if remaining_time>0:
            controller.log = 0
            await asyncio.sleep_ms(remaining_time)
        else:
            controller.log = remaining_time


pid = PID(get_both_sensors(stepper,encoder),stepper.set_period_direction,ctrlparam['sampling_time_ms'],ctrlparam['Kp1'],ctrlparam['Ki1'],ctrlparam['Kd1'],ctrlparam['Kp2'],ctrlparam['Ki2'],ctrlparam['Kd2'],0,0,0,0,0,0,2**16,2**16,False,True,True,supervisory)

ss = StateSpace(get_both_sensors(stepper,encoder),stepper.set_period_direction,ctrlparam['sampling_time_ms'],ctrlparam['A'],ctrlparam['B'],ctrlparam['C'],False,supervisory)


@micropython.native
async def garbage_control(sleep_ms):
    while True:
        gc.collect()
        gc.threshold((gc.mem_free() + gc.mem_alloc()) // 4)
        await asyncio.sleep_ms(sleep_ms)
    

async def main():
    garbage_task = asyncio.create_task(garbage_control(1000))
    control_task = asyncio.create_task(control(pid,ss))
    repl_task = asyncio.create_task(repl(globals()))

    await repl_task
    # if repl is stopped, also stop the other tasks:
    control_task.cancel()
    garbage_task.cancel()
    #await asyncio.gather(control_task, repl_task)
        

set_control_sequence(5.,40.,-40.,100)
set_reference_sequence(0.,20.,-20.,100)

# initialize L6474:
stepper.set_default()
# enable L6474
stepper.enable()
stepper.set_period_direction(0)
# run tasks
asyncio.run(main())

# clean up
stepper.disable()
    
