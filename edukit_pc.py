import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
import aioserial
from multiprocessing import Process, Queue, queues
import matplotlib.pyplot as plt
import numpy as np
import rlcompleter
import readline
readline.parse_and_bind("tab: complete")

end_pattern = b'\r\n<-> '

class Sentinel():
    """Sentinel class for sending stop signal over e.g. a queue.
       Use isinstance(obj,Sentinel) to determine if obj is the sentinel.
       Just create the sentinel by calling: Sentinel().
    """

    # fast cyclic fifo buffer class for storing signal data
# (writes samples 2 times, so its double length,
# sacrificing some memory to prevent time-consuming memory shifting)
class CyclicBuffer(object):
    """Implementation of a fast cyclic FIFO (first in first out) buffer."""
    def __init__(self,length=1,dims_sample=(1,)):
        """Create the cyclic buffer for length (integer) samples, where dims_sample is a 
           tuple specifying the dimensions of each sample. So when a sample is an array
           of 4 elements dims_sample=(4,), but also higher dimensional data structures such
           as matrices (dims_sample has 2 elements) and tensors (dims_sample more than 
           2 elements) are allowed."""
        self._length = length
        self._dims_sample = dims_sample
        self._buffer = np.zeros((2*self._length,*self._dims_sample))
        self._last = 0
        
    def get(self):
        """Return the length samples in the numpy array buffer. """
        return self._buffer[self._last:self._last+self._length]
    
    def update(self,sample):
        """Update the cyclic buffer with the sample. Sample is a list or a numpy array
        which dimensions should match with dims_sample set by the __init__ method."""
        last = self._last     # pointer to new place
        length = self._length
        # store sample at position last and last-length:
        self._buffer[last] = self._buffer[last+length] = sample
        self._last = (last + 1) % length

    def __call__(self):
        """Rather than buffer.get() you can get the buffer by buffer() as well."""
        return self.get()

    
async def plotter(ser,namespace,plot_queue,async_sleep_time_for_CTS=0.01):
    last_sample = np.zeros((3,))
    command = "pid.sample"
    while namespace['plotter_conf']['do_plotter'] == True:
        try:
            resp = await ser_eval(ser,command,async_sleep_time_for_CTS)
            last_sample[:] = np.float64(eval(resp))                    
            try:
                #plot_queue.put_nowait(last_sample)
                plot_queue.put(last_sample) # block until there is space in the queue, no reason to proceed if queue is full
            except queues.Full:
                #print('plot_queue full')
                pass
        except:
            pass
        await asyncio.sleep(0.1) # get data 10 times per sec
        
    plot_queue.put(Sentinel()) # send the sentinel to inform plot_process to stop
    print('Stopping plotter')

def plot_process(plot_queue):
    """plot_process listens to the plot_queue and plots the data received."""
    buffer_size = 100
    dims_sample = (3,)
    plot_buffer = CyclicBuffer(buffer_size,dims_sample)
    
    plt.ioff()  # do not make the plot interactive, else plot not updated correctly
                # or it takes the focus from the prompt to the figure which is quite annoying.
    fig,axes = plt.subplots(3,1)
    plt.show(block=False)
    plot_counter = 0
    while True:
        plot_counter += 1
        sample = None
        try:
            sample = plot_queue.get(timeout=0.1)
        except:
            pass
        if sample is not None:
            if isinstance(sample,Sentinel):
                break  # jump out of while-loop to close figure and stop plot_process
            plot_buffer.update(sample)
        if plot_counter >= 4:
            data = plot_buffer.get()
            [axes[i].cla() for i in range(3)]  # clear all axes
            axes[0].plot(data[:,0])
            axes[0].set_ylabel('y_1')
            axes[1].plot(data[:,1])
            axes[1].set_ylabel('y_2')
            axes[2].plot(data[:,2])
            axes[2].set_ylabel('u')
            fig.canvas.draw()         # this and following line to 
            fig.canvas.flush_events() # update figure
            plot_counter = 0
        time.sleep(0.01)
    plt.close(fig)

    
async def ser_eval(ser,command,async_sleep_time_for_CTS=0.01):
    resp = b''
    async with ser.lock:
        ser.reset_output_buffer()
        ser.reset_input_buffer()
        #ser.setRTS(True) # does not work on Windows
        command_byte = (command+'\r\n').encode('utf-8') # extend with C-n)
        #while not ser.getCTS(): # does not work on Windows
        #    await asyncio.sleep(async_sleep_time_for_CTS)
        await ser.write_async(command_byte)
        ser.flush()
        #print('after flush')
        resp += await ser.read_async(ser.in_waiting)
        #print('received resp = ',resp.decode('utf-8'))
        if len(resp)>=len(end_pattern):
            pattern = resp[-len(end_pattern):]
        else:
            pattern = b''
        while not (pattern == end_pattern):
            if ser.in_waiting > 1:
                resp += await ser.read_async(ser.in_waiting)
            else:
                resp += await ser.read_async(1)
            if len(resp)>=len(end_pattern):
                pattern = resp[-len(end_pattern):]
    return resp[:-len(end_pattern)].decode('utf-8').lstrip()


# non-blocking keyboard input, from https://gist.github.com/delivrance/675a4295ce7dc70f0ce0b164fcdbd798
async def ainput(prompt: str = "") -> str:
    with ThreadPoolExecutor(1, "AsyncInput") as executor:
        return await asyncio.get_event_loop().run_in_executor(executor, input, prompt)

def edukit_help():
    print("""
Help on edukit-micropython
==========================
To be written
    """)
    
async def repl(ser,namespace):
    do_repl = True
    print("""
Enter "stop" to exit.
Prefix command with "mp " to evaluate on micropython.
NB: The asynchronous serial communication is not always reliable, commands may be lost!
Note, that the microcontroller has limited memory, and uses garbage control to free memory. Especially with large objects such as lists and arrays this can be problematic.
Arrow-up can be used to go back in the history of previous input. Tab-completion is supported, but (unfortunately) not for "mp " prefixed code.
Enter "edukit_help()" for further help and examples.
""")
    global _
    while do_repl:
        command = await ainput('-> ')
        if command == 'stop':
            do_repl = False
            namespace['plotter_conf']['do_plotter'] = False # stop plotter
            result = await ser_eval(ser,'stop')
            print('stopping mp return:',result)
            break
        elif command[0:3] == 'mp ':
            result = await ser_eval(ser,command[3:])
            result = result.rstrip() # rstrip to remove white space such as \r, \n
            if not (result == 'None'):
                if (result[0:9] == "Exception"): # Exceptions should not be evaluated as in _ = eval(result) below
                    print('mp return:',result[9:])
                else:
                    print('mp return:',result)
                    #try:
                    #    _ = eval(result)
                    #    print("result available in _")
                    #except:
                    #    pass
        elif command[0:6] == "await ":
            try:
                result = await eval(command[6:],namespace)
                if result is not None:
                    _ = result
                    print(result)
            except Exception as e:
                print(str(e))
        else:
            try:
                result = eval(command,namespace)
                if result is not None:
                    _ = result
                    print(result)
            except SyntaxError:
                try:
                    result = exec(command,namespace)
                    if result is not None:
                        _ = result
                        print(result)
                except Exception as e:
                    print(str(e))
            except Exception as e:
                print(str(e))


# all main coroutine tasks should be gathered here:
async def main(ser,namespace,plot_queue):
    repl_eval_task = asyncio.create_task(repl(ser,namespace))
    plotter_task = asyncio.create_task(plotter(ser,namespace,plot_queue))
    await asyncio.gather(repl_eval_task,plotter_task)

# convenience functions:
async def set_pid(Kp,Ki,Kd):
    command = f"pid.set_gains({1.0*Kp}, {1.0*Ki}, {1.0*Kd})"
    return await ser_eval(ser,command)

async def get_pid(channel=None):
    if channel is None:
        command = "pid.Kp, pid.Ki, pid.Kd"
    elif channel == 1:
        command = "pid.Kp1, pid.Ki1, pid.Kd1"
    elif channel == 2:
        command = "pid.Kp2, pid.Ki2, pid.Kd2"
    else:
        print("get_pid: Unknown channel")
        return
    return await ser_eval(ser,command) # note string is given back!

async def set_pid(Kp,Ki,Kd,channel=None):
    if channel is None:
        command = f"pid.set_gains({1.0*Kp}, {1.0*Ki}, {1.0*Kd})"        
    elif channel == 1:
        command = f"pid.set_gains1({1.0*Kp}, {1.0*Ki}, {1.0*Kd})"
    elif channel == 2:
        command = f"pid.set_gains2({1.0*Kp}, {1.0*Ki}, {1.0*Kd})"
    else:
        print("set_pid: Unknown channel")
        return
    return await ser_eval(ser,command)

    

if __name__ == "__main__":
    serial_port = "/dev/ttyACM0"
    baudrate    = 115200
    #timeout     = 0.1
    _ = None
    plotter_conf = {'do_plotter': True}
    plot_queue = Queue(maxsize=20)
    plot_p = Process(target=plot_process,args=(plot_queue,))
    #ser = aioserial.AioSerial(port=serial_port,baudrate=baudrate,timeout=timeout)
    ser = aioserial.AioSerial(port=serial_port,baudrate=baudrate)
    ser.lock = asyncio.Lock() # add a lock to serial port, to prevent multiple processes communicate with serial interface at same time
    ser.reset_output_buffer()
    ser.reset_input_buffer()
    ser.write(b'\x04\r\n') # reset micropython board
    ser.flush()
    time.sleep(2) # wait for time up after reset
    startup_cmd = 'import edukit_mp'.encode('utf-8') + b'\r\n'  # note it is imported, rather than executed by exec, because its a mpy file
    ser.write(startup_cmd)                   # run edukit program on micropython board
    ser.flush()
    time.sleep(2) # wait for edukit to start up
    ser.write(b'enc.value(0)\r\n')
    ser.flush()
    ser.reset_output_buffer()
    ser.reset_input_buffer()
    plot_p.start() # start plotter process
    asyncio.run(main(ser,globals(),plot_queue)) # start async tasks
    ser.write(b'\x04\r\n') # after completing tasks, reset micropython board
    ser.flush()
    ser.reset_output_buffer()
    ser.reset_input_buffer()
    ser.close()
    plot_p.join()
    plot_queue.close()
    print('All done')

