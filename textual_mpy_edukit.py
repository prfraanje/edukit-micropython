#!/bin/env python3

from array import array
import asyncio
from collections import deque
import datetime
import logging
logging.getLogger("asyncio").setLevel(logging.WARNING)
import math
import pickle
import re
import serial.tools.list_ports as list_ports
import sys
import time


import aioserial

import numpy as np
import matplotlib.pyplot as plt
#plt.ion() # enable automatic drawing mode

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual import on
from textual.screen import Screen
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Header, Footer, Static, Button, Label, Input, Placeholder, RichLog, RadioButton, RadioSet, Switch, Rule

from textual_plotext import PlotextPlot

from textual_customizations import CustomSuggester, CustomInput

END_PATTERN = b'\x04'
SAMPLING_TIME = 0.01
LOG_BUF_LEN = 128
log_data = np.zeros((3*LOG_BUF_LEN,3))

suggestions = ["micropython_results", "python_results", "micropython_tasks", "python_tasks",
               "log_data", 
               ]
mpy_suggestions = ["micropythonn_results","micropython_tasks",
                   "pid.", "pid.get_gains1()", "pid.get_gains2()", "pid.set_gains1()","pid.pid_set_gains2()",
                   "encoder.", "stepper.","supervisory", "supervisory['reference_add']",
               ]


class TimeDisplay(Static):
    """A widget to display elapsed time."""
    time = reactive(0.0)

    def __init__(self,*args,**kwargs):
        global app
        self.start_time = time.monotonic()
        MAXLEN=300
        self.plot_history = [deque([0.]*MAXLEN,maxlen=MAXLEN),deque([0.]*MAXLEN,maxlen=MAXLEN),deque([0.]*MAXLEN,maxlen=MAXLEN)]
        super(TimeDisplay,self).__init__(*args,**kwargs)
    
    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        #self.plots = [app.query_one('#plot1'), app.query_one('#plot2')]
        self.plot_output = [app.query_one('#plot_output')]
        self.plot_input = [app.query_one('#plot_input')]        
        self.update_timer = self.set_interval(1 / 20, self.update_time)

    async def update_time(self) -> None:
        """Method to update the time to the current time."""
        self.time = (time.monotonic() - self.start_time)
        await self.update_plots()

    async def update_plots(self):
        global micropython_serial_interface
        resp = await serial_eval(micropython_serial_interface,'pid.sample')
        data = resp
            
        for i in range(len(data)): self.plot_history[i].append(data[i])
        self.plot_output[0].plt.clear_data()
        self.plot_output[0].plt.scatter(self.plot_history[0],yside='left',label='stepper steps',marker='fhd')
        self.plot_output[0].plt.scatter(self.plot_history[1],yside='right',label='encoder ticks',marker='fhd')
        self.plot_output[0].refresh()
        self.plot_input[0].plt.clear_data()
        self.plot_input[0].plt.scatter(self.plot_history[2],yside='left',label='control',marker='fhd')
        self.plot_input[0].refresh()
        

    def watch_time(self, time: float) -> None:
        """Called when the time attribute changes."""
        minutes, seconds = divmod(time, 60)
        hours, minutes = divmod(minutes, 60)
        self.update(f"{hours:02,.0f}:{minutes:02.0f}:{seconds:05.2f}")

        
class IDE(App):
    TITLE = "Edukit Pendulum Control"
    SUB_TITLE = "with micropython and textual"
    CSS_PATH = "textual_mpy_edukit.css"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("p", "toggle_update_plots","Toggle update plots"),
        Binding("ctrl+z", "suspend_process")
    ]

    logtext = reactive("Not logging",init=False)

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        with Horizontal():
            with Vertical(id='left_bar'): # left bar, python buttons
                # tekst input for number of buffers
                # label output for number of samples
                # checkbox for datetime appending of output
                yield Static(f"Number of buffers: ")
                yield Static(f"(One buffer is {LOG_BUF_LEN} samples.)")                
                yield Input(type="integer",value='1',id='num_bufs_input')
                yield Static("Append datetime: ")
                yield Switch(value=True,animate=False,id='datetimeswitch')
                yield Label(self.logtext,id='loglabel')
                yield Button('Log Data',id='log_data_button')
                yield Rule(line_style="ascii")
                yield RadioButton('reference_add',value=False,id='reference_add')
                yield RadioButton('control_add',value=False,id='control_add')
                yield Button('Stepper Zero',id='stepper_zero_button')
            with Vertical(id='middle_bar'): # middle bar, plots and repl's
                #yield Label("Press Ctrl+Z tot suspend.")
                yield TimeDisplay(id='timer_plots')
                yield PlotextPlot(id='plot_output')
                yield PlotextPlot(id='plot_input')
                with Horizontal():
                    with Vertical():
                        yield RichLog(highlight=True,markup=True,auto_scroll=True,max_lines=1000,id="python_output")
                        yield CustomInput(placeholder="Python prompt",id="python_input",suggester=CustomSuggester(suggestions))

                    with Vertical():
                        yield RichLog(highlight=True,markup=True,auto_scroll=True,max_lines=1000,id="micropython_output")
                        yield CustomInput(placeholder="MicroPython prompt",id="micropython_input",suggester=CustomSuggester(mpy_suggestions))
            with Vertical(id='right_bar'): # right bar, micropython buttons
                # RadioSet choice for pid vs state-space
                # input fields for pid gains (optional)
                yield Label("Select controller type:")
                with RadioSet(id='control_type'):
                    yield RadioButton("PID",value=True)
                    yield RadioButton("State-space")
                yield Rule(line_style="ascii")
                yield Label("PID:")
                yield RadioButton('pid.run',value=False,id='pid_run')
                yield RadioButton('pid.run1',value=True,id='pid_run1')
                yield RadioButton('pid.run2',value=True,id='pid_run2')
                yield Rule(line_style="ascii")
                yield RadioButton('ss.run',value=False,id='ss_run')

    def on_mount(self):
        global log_data
        python_output = self.query_one("#python_output")
        python_output.can_focus=False
        python_output.write("""
        At the [bold red]Python REPL[/bold red] you can use:
          [deep_sky_blue3]up/down arrows[/deep_sky_blue3] to scroll backward/forward through past inputs,
          [deep_sky_blue3]right arrow[/deep_sky_blue3] to select suggestion or go right
        Also see [magenta]https://textual.textualize.io/widgets/input/[/magenta]
        Note past results from python and micropython can be accessed through:
        [green]python_results[/green]
        [green]micropython_results[/green]
        where [italic]i = 0, 1, ...[/italic] refers to the last output, the one before, etc.
        """)
        micropython_output = self.query_one("#micropython_output")
        micropython_output.can_focus=False
        micropython_output.write("""
        At the [bold red]Micropython REPL[/bold red] you can use:
          [deep_sky_blue3]up/down arrows[/deep_sky_blue3] to scroll backward/forward through past inputs,
          [deep_sky_blue3]right arrow[/deep_sky_blue3] to select suggestion or go right
        Also see [magenta]https://textual.textualize.io/widgets/input/ [/magenta]       
        """)

        plt1 = self.query_one('#plot_output').plt
        plt1.title("Plot output (stepper steps and encoder ticks)") # to apply a title
        plt2 = self.query_one('#plot_input').plt
        plt2.title("Plot input (control)") # to apply a title
        

    @on(Button.Pressed,'#log_data_button')
    async def handle_log_data(self, event: Button.Pressed) -> None:
        log_task = asyncio.create_task(self.data_logger())

    @on(Button.Pressed,'#stepper_zero_button')
    async def handle_stepper_zero_button(self, event: Button.Pressed) -> None:
        await serial_eval(micropython_serial_interface,'stepper.set_period_direction(0)')
        
    @on(RadioSet.Changed,'#control_type')
    async def handle_radioset_control_type(self, event: RadioSet.Changed) -> None:
        if str(event.pressed.label) == "PID":
            ctrl_type = 'pid'
        elif str(event.pressed.label) == "State-space":
            ctrl_type = 'state_space'
        else:
            ctrl_type = 'pid'
        await serial_eval(micropython_serial_interface, f'ctrlparam["type"]=\"{ctrl_type}\"')
        
    @on(RadioButton.Changed)
    async def handle_radiobuttons(self, event: RadioButton.Changed) -> None:
        global micropython_serial_interface
        button_id = event.radio_button.id
        if button_id == 'pid_run':
            button = 'pid.run'
        elif button_id == 'pid_run1':
            button = 'pid.run1'
        elif button_id == 'pid_run2':
            button = 'pid.run2'
        elif button_id == 'ss_run':
            button = 'state_space.run'
        elif button_id == 'reference_add':
            button = 'supervisory["reference_add"]'
        elif button_id == 'control_add':
            button = 'supervisory["control_add"]'
        else:
            return None
            
        if event.value == True:
            val = "True"
        else:
            val = "False"
        await serial_eval(micropython_serial_interface, button + '='+val)
        # send zero to stepper when control_add is stopped:
        if (button_id == 'control_add') and (event.value == False):
            await serial_eval(micropython_serial_interface, 'stepper.set_period_direction(0)')

        

    @on(Input.Submitted,"#python_input")
    async def handle_python_input(self, event: Input.Submitted) -> None:
        global python_tasks, python_results
        input = event.input
        input.suggester.add_suggestion(event.value)
        input.backward_forward_index = None
        input.clear()
 
        result=None
        if event.value[0:6] == 'await ':
            task = asyncio.create_task(eval(event.value[6:]))
            waited_time = 0.
            while True:
                await asyncio.sleep(1e-2) # sleep for 10 ms to check whether task is done
                waited_time += 1e-2
                if task.done():
                    result = task.result()
                    break
                elif waited_time >= 0.2:
                    # put task in python_tasks queue:
                    python_tasks.appendleft(task)
                    result = None
                    break                   
        else:
            try:
                result = eval(event.value,globals())
                if result is not None:
                    _ = result
            except SyntaxError:
                try:
                    result = exec(event.value,globals())
                    if result is not None:
                        _ = result
                except Exception as e:
                    result = e
            except Exception as e:
                result = e
        if result is not None:
            python_results.appendleft(result)
            self.query_one("#python_output").write(result)


    @on(Input.Submitted,"#micropython_input")
    async def handle_micropython_input(self, event: Input.Submitted) -> None:
        global micropython_tasks, micropython_results, micropython_serial_interface
        input = event.input
        input.suggester.add_suggestion(event.value)
        input.backward_forward_index = None
        input.clear()
                     
        result = None
        if event.value[0:17] == 'micropython_tasks':
            result = eval(event.value,globals())
        elif event.value[0:19] == 'micropython_results':
            result = eval(event.value,globals())
        else:
            task = asyncio.create_task(serial_eval(micropython_serial_interface,event.value))
            waited_time = 0.
            while True:
                await asyncio.sleep(1e-2) # sleep for 10 ms to check whether task is done
                waited_time += 1e-2
                if task.done():
                    result = task.result()
                    break
                elif waited_time >= 1:
                    # put task in python_tasks queue:
                    micropython_tasks.appendleft(task)
                    result = None
                    break

        if (result is not None) and (result != ''):
            micropython_results.appendleft(result)
            self.query_one("#micropython_output").write(result)


    def watch_logtext(self, text: str) -> None:
        self.query_one('#loglabel').update(text)
    

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_toggle_update_plots(self) -> None:
        """Action to pause and resume the TimeDisplay and thus the plot update."""
        if self.logtext == 'Not logging':
            timer = self.query_one('#timer_plots').update_timer
            if timer._active.is_set():
                timer.pause()
            else:
                timer.resume()

    async def data_logger(self):
        global log_data
        log = True
        self.logtext = 'Logging'
        log0_prev = False
        log1_prev = False
        log0 = True
        log1 = True
        log_ready = False
        log_num_buf = int(self.query_one('#num_bufs_input').value)
        log_num_samples = log_num_buf * LOG_BUF_LEN
        log_buf_counter = 0
        log_data = np.zeros((log_num_samples,3))

        # stop updating plots not to overload serial interface
        timer = self.query_one('#timer_plots').update_timer
        timer.pause()

        await serial_eval(micropython_serial_interface,f"supervisory['log_num_samples']={log_num_samples}")
        await serial_eval(micropython_serial_interface,f"supervisory['log_ready']={log_ready}")
        await serial_eval(micropython_serial_interface,f"supervisory['log']={log}")
        log = await serial_eval(micropython_serial_interface,"supervisory['log']")            
        log0 = await serial_eval(micropython_serial_interface,"supervisory['log0']")
        log1 = await serial_eval(micropython_serial_interface,"supervisory['log1']")
        while log:
            log0_prev = log0
            log1_prev = log1
            log = await serial_eval(micropython_serial_interface,"supervisory['log']")            
            log0 = await serial_eval(micropython_serial_interface,"supervisory['log0']")
            log1 = await serial_eval(micropython_serial_interface,"supervisory['log1']")
            # detect True -> False changes:
            if (log0_prev == True) and (log0 == False): # log0 is finished
                log0_data = await serial_eval(micropython_serial_interface,f"supervisory['log0_data']")
                log_data[log_buf_counter*LOG_BUF_LEN:(log_buf_counter+1)*LOG_BUF_LEN,:] = np.array(log0_data).T
                log_buf_counter += 1                
            elif  (log1_prev == True) and (log1 == False): # log1 is finished
                log1_data = await serial_eval(micropython_serial_interface,f"supervisory['log1_data']")
                log_data[log_buf_counter*LOG_BUF_LEN:(log_buf_counter+1)*LOG_BUF_LEN,:] = np.array(log1_data).T
                log_buf_counter += 1
            else:
                await asyncio.sleep(round(0.1*LOG_BUF_LEN*SAMPLING_TIME))

        self.logtext = 'Not logging'
        # resume updating of plots
        timer.resume()
        fname="log_data"
        if self.query_one('#datetimeswitch').value == True:
            fname += "_" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        fname += '.pickle'
        with open(fname,'wb') as handle:
            pickle.dump(log_data,handle,protocol=pickle.HIGHEST_PROTOCOL)

            
async def serial_eval(serial_interface,command,END_PATTERN=b'\x04'):
    response = None
    async with serial_interface.lock:
        resp = b''
        #ser.reset_output_buffer()
        #ser.reset_input_buffer()
        command_byte = (command).encode('utf-8')+END_PATTERN
        await ser.write_async(command_byte)
        ser.flush()
        resp += await ser.read_async(ser.in_waiting)
        if len(resp)>=len(END_PATTERN):
            pattern = resp[-len(END_PATTERN):]
        else:
            pattern = b''
        while not (pattern == END_PATTERN):
            if ser.in_waiting > 1:
                resp += await ser.read_async(ser.in_waiting)
            else:
                resp += await ser.read_async(1)
            if len(resp)>=len(END_PATTERN):
                pattern = resp[-len(END_PATTERN):]
        response = resp[:-(len(END_PATTERN))].decode('utf-8')
        if response == '':
            response = None
    if (response is None):
        return response
    if len(response)>11:
        if response[0:11] == 'Exception: ':
            return response
    try:
        res = eval(response)
    except:
        res = response
    return res
        
if __name__ == '__main__':
    python_tasks = deque([],maxlen=10)
    python_results = deque([],maxlen=50)
    micropython_tasks = deque([],maxlen=10)
    micropython_results = deque([],maxlen=50)

    ports_avail = list_ports.comports()
    serial_port = [port.device for port in ports_avail if port.manufacturer=='STMicroelectronics'][0]
    baudrate    = 115200
    ser = aioserial.AioSerial(port=serial_port,baudrate=baudrate)
    micropython_serial_interface = ser
    ser.lock = asyncio.Lock() # add a lock to serial port, to prevent multiple processes communicate with serial interface at same time
    ser.reset_output_buffer()
    ser.reset_input_buffer()
    ser.write(b'\x04') # reset micropython board
    ser.flush()
    ser.write(b'\x01') # Ctrl-A leave repl mode
    ser.reset_input_buffer()
    startup_cmd = 'import mpy_edukit'.encode('utf-8') + b'\r\n' + b'\x04'  # note it is imported, rather than executed by exec, because its a mpy file
    ser.write(startup_cmd)                   # run edukit program on micropython board
    ser.flush()
    time.sleep(0.5) # wait for edukit to start up
    
    ser.reset_output_buffer()
    ser.reset_input_buffer()

    app = IDE()
    app.run()

    ser.write(b'stop'+END_PATTERN+b'\x04')
    ser.write(b'\x02') # Ctrl-B back to repl mode
    ser.write(b'\x04') # after completing tasks, reset micropython board
    ser.flush()
    ser.reset_output_buffer()
    ser.reset_input_buffer()
    ser.close()
    print('All done')
    



    
