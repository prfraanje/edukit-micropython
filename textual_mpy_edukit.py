#!/bin/env python3

import asyncio
from collections import deque
import re
import serial.tools.list_ports as list_ports
import sys
import time

import logging
logging.getLogger("asyncio").setLevel(logging.WARNING)

import aioserial

from textual.app import App, ComposeResult
from textual import on
from textual.screen import Screen
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Header, Footer, Static, Button, Label, Input, RichLog, RadioButton
from textual.suggester import SuggestFromList

from textual_plotext import PlotextPlot

import math

END_PATTERN = b'\x04'
#END_PATTERN = b'<->\r\n '

completions = ["micropython_results", "python_results", "micropython_tasks", "python_tasks",]


class TimeDisplay(Static):
    """A widget to display elapsed time."""
    time = reactive(0.0)

    def __init__(self,*args,**kwargs):
        global app
        self.start_time = time.monotonic()
        MAXLEN=300
        self.plots_history = [deque([0.]*MAXLEN,maxlen=MAXLEN),deque([0.]*MAXLEN,maxlen=MAXLEN)]
        super(TimeDisplay,self).__init__(*args,**kwargs)
    
    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        #self.plots = [app.query_one('#plot1'), app.query_one('#plot2')]
        self.plots = [app.query_one('#plot')]
        self.update_timer = self.set_interval(1 / 20, self.update_time)

    async def update_time(self) -> None:
        """Method to update the time to the current time."""
        self.time = (time.monotonic() - self.start_time)
        await self.update_plots()

    async def update_plots(self):
        global micropython_serial_interface
        #resp = await serial_eval(micropython_serial_interface,'sample')
        resp = None
        data = [math.sin(2*math.pi*.25*self.time), math.sin(2*math.pi*.5*self.time)]
        if resp is not None:
            if len(resp)>11:
                if resp[0:11] != 'Exception: ':
                    data = resp
            else:
                data = resp
            
        for i in range(2): self.plots_history[i].append(data[i])
        self.plots[0].plt.clear_data()
        self.plots[0].plt.scatter(self.plots_history[0],yside='left',label='plot1',marker='fhd')
        self.plots[0].plt.scatter(self.plots_history[1],yside='right',label='plot2',marker='fhd')
        self.plots[0].refresh()
        

    def watch_time(self, time: float) -> None:
        """Called when the time attribute changes."""
        minutes, seconds = divmod(time, 60)
        hours, minutes = divmod(minutes, 60)
        self.update(f"{hours:02,.0f}:{minutes:02.0f}:{seconds:05.2f}")



class IDE(App):
    TITLE = "My Python IDE"
    SUB_TITLE = "Experiment"
    CSS_PATH = "my_python_ide.css"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("p", "toggle_update_plots","Toggle update plots"),
        Binding("ctrl+z", "suspend_process")
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        with Horizontal():
            with Vertical(id='left_bar'): # left bar, python buttons
                yield Button('')
            with Vertical(id='middle_bar'): # middle bar, plots and repl's
                #yield Label("Press Ctrl+Z tot suspend.")
                yield TimeDisplay(id='timer_plots')
                yield PlotextPlot(id='plot')
                with Horizontal():
                    with Vertical():
                        yield RichLog(highlight=True,markup=True,auto_scroll=True,max_lines=1000,id="python_output")
                        yield Input(placeholder="Python prompt",id="python_input",suggester=SuggestFromList(completions))

                    with Vertical():
                        yield RichLog(highlight=True,markup=True,auto_scroll=True,max_lines=1000,id="micropython_output")
                        yield Input(placeholder="MicroPython prompt",id="micropython_input",suggester=SuggestFromList(completions))
            with Vertical(id='right_bar'): # right bar, micropython buttons
                yield RadioButton('pid2.run')
                yield RadioButton('pid2.run1')
                yield RadioButton('pid2.run2')                                
                

    def on_mount(self):
        self.query_one("#python_output").can_focus=False
        self.query_one("#micropython_output").can_focus=False

        plt = self.query_one('#plot').plt
        plt.title("Plot") # to apply a title
        #plt2 = self.query_one('#plot2').plt
        #plt2.title("Plot2") # to apply a title


    @on(Input.Submitted,"#python_input")
    async def handle_python_input(self, event: Input.Submitted) -> None:
        global python_tasks, python_results
        #app.query_one('#python_input').suggester._suggestions.append(event.value) # does not work??
        app.query_one('#python_input').suggester._suggestions.append(event.value) # does not work??        
            
        self.query_one("#python_input").clear()

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
        self.query_one("#micropython_input").clear()
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


    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_toggle_update_plots(self) -> None:
        """Action to pause and resume the TimeDisplay and thus the plot update."""
        timer = self.query_one('#timer_plots').update_timer
        if timer._active.is_set():
            timer.pause()
        else:
            timer.resume()
            
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
    print('response = ',response)
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
    startup_cmd = 'import mymp'.encode('utf-8') + b'\r\n' + b'\x04'  # note it is imported, rather than executed by exec, because its a mpy file
    ser.write(startup_cmd)                   # run edukit program on micropython board
    ser.flush()
    time.sleep(0.5) # wait for edukit to start up
    serial_eval(ser,'enc.value(0)')
    
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
    



    
