#!/usr/bin/env python3
"""
NiceGUI-based web interface for Edukit Micropython Pendulum Control
Provides web browser access to control system with interactive plots and dual REPLs

Design choices:
- Plotly for interactive plots
- Terminal-style REPLs with tab completion
- Three-column layout (controls | plots+REPLs | settings)
- ui.timer for real-time updates (20Hz)
- CSV export for data logging
- Single-user mode for safety
- Dark mode by default
- Auto-detect serial port with manual override
"""

import asyncio
from collections import deque
import datetime
import time
import csv
import logging

import aioserial
import serial.tools.list_ports as list_ports
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from nicegui import ui, app

# ============================================================================
# CONSTANTS
# ============================================================================

END_PATTERN = b'\x04'
SAMPLING_TIME = 0.01  # 10ms sampling time (100 Hz)
LOG_BUF_LEN = 128     # Buffer length for data logging
UPDATE_FREQUENCY = 20  # Hz for plot updates

# REPL command suggestions
PYTHON_SUGGESTIONS = [
    "python_results[0]",
    "micropython_results[0]",
    "state.plot_data",
    "help(",
]

MICROPYTHON_SUGGESTIONS = [
    "pid.sample",
    "pid.get_gains1()",
    "pid.get_gains2()",
    "pid.set_gains1(",
    "pid.set_gains2(",
    "pid.run",
    "pid.run1",
    "pid.run2",
    "pid.r1",
    "pid.r2",
    "ss.sample",
    "ss.run",
    "stepper.get_abs_pos_efficient()",
    "stepper.set_period_direction(",
    "encoder.value()",
    "supervisory",
    "ctrlparam",
]

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# GLOBAL STATE
# ============================================================================

class AppState:
    """
    Global application state

    This class holds all stateful data for the application including:
    - Serial connection state
    - Plot data buffers
    - REPL history and results
    - Logging state
    - Controller configuration
    """

    def __init__(self):
        # REPL results and history
        self.python_results = deque([], maxlen=50)
        self.micropython_results = deque([], maxlen=50)
        self.python_history = deque([], maxlen=50)
        self.micropython_history = deque([], maxlen=50)

        # Serial interface
        self.serial_interface = None
        self.serial_lock = None
        self.connected = False
        self.connection_in_use = False  # Single-user access control

        # Plot data (circular buffers)
        self.maxlen = 300  # Show last 300 samples
        self.plot_data = {
            'stepper': deque([0.0] * self.maxlen, maxlen=self.maxlen),
            'encoder': deque([0.0] * self.maxlen, maxlen=self.maxlen),
            'control': deque([0.0] * self.maxlen, maxlen=self.maxlen),
            'time': deque(list(range(-self.maxlen, 0)), maxlen=self.maxlen)
        }
        self.sample_counter = 0

        # Logging state
        self.logging = False
        self.log_data = None

        # Controller type ('pid' or 'ss')
        self.controller_type = 'pid'

        # Update timer reference
        self.update_timer = None

        # Start time for elapsed timer
        self.start_time = time.monotonic()

# Create global state instance
state = AppState()

logger.info("Application state initialized")

# ============================================================================
# SERIAL COMMUNICATION
# ============================================================================

async def serial_eval(command: str, END_PATTERN: bytes = b'\x04'):
    """
    Send command to MicroPython board and receive response

    Args:
        command: Python command to evaluate on MicroPython
        END_PATTERN: Byte pattern marking end of transmission

    Returns:
        Evaluated result from MicroPython or error message
    """
    if not state.serial_interface or not state.connected:
        logger.warning("serial_eval called but not connected")
        return "Error: Not connected to microcontroller"

    response = None
    async with state.serial_lock:
        resp = b''
        command_byte = command.encode('utf-8') + END_PATTERN
        await state.serial_interface.write_async(command_byte)
        state.serial_interface.flush()

        # Read initial response
        resp += await state.serial_interface.read_async(state.serial_interface.in_waiting)
        if len(resp) >= len(END_PATTERN):
            pattern = resp[-len(END_PATTERN):]
        else:
            pattern = b''

        # Keep reading until we get the end pattern
        while not (pattern == END_PATTERN):
            if state.serial_interface.in_waiting > 1:
                resp += await state.serial_interface.read_async(state.serial_interface.in_waiting)
            else:
                resp += await state.serial_interface.read_async(1)
            if len(resp) >= len(END_PATTERN):
                pattern = resp[-len(END_PATTERN):]

        response = resp[:-(len(END_PATTERN))].decode('utf-8')
        if response == '':
            response = None

    if response is None:
        return response

    # Check for exception from MicroPython
    if len(response) > 11 and response[0:11] == 'Exception: ':
        logger.warning(f"MicroPython exception: {response}")
        return response

    # Try to evaluate the response as a Python literal
    try:
        res = eval(response)
    except:
        res = response
    return res


async def connect_serial(port: str, baudrate: int = 115200) -> tuple[bool, str]:
    """
    Connect to MicroPython board via serial port

    Args:
        port: Serial port device path (e.g., '/dev/ttyACM0' or 'COM3')
        baudrate: Communication speed (default: 115200)

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        logger.info(f"Attempting to connect to {port} at {baudrate} baud")

        state.serial_interface = aioserial.AioSerial(port=port, baudrate=baudrate)
        state.serial_lock = asyncio.Lock()

        # Reset and initialize the board
        state.serial_interface.reset_output_buffer()
        state.serial_interface.reset_input_buffer()
        state.serial_interface.write(b'\x04')  # Ctrl-D: Reset micropython board
        state.serial_interface.flush()
        await asyncio.sleep(0.1)

        state.serial_interface.write(b'\x01')  # Ctrl-A: Leave REPL mode
        state.serial_interface.reset_input_buffer()

        # Import mpy_edukit on the microcontroller
        startup_cmd = 'import mpy_edukit'.encode('utf-8') + b'\r\n' + b'\x04'
        state.serial_interface.write(startup_cmd)
        state.serial_interface.flush()
        await asyncio.sleep(0.5)  # Wait for edukit to start up

        state.serial_interface.reset_output_buffer()
        state.serial_interface.reset_input_buffer()

        state.connected = True
        logger.info(f"Successfully connected to {port}")
        return True, f"Connected to {port}"

    except Exception as e:
        logger.error(f"Serial connection failed: {e}")
        state.connected = False
        return False, f"Connection failed: {str(e)}"


def disconnect_serial():
    """Disconnect from MicroPython board and clean up"""
    if state.serial_interface and state.connected:
        try:
            logger.info("Disconnecting from microcontroller")
            state.serial_interface.write(b'stop' + END_PATTERN + b'\x04')
            state.serial_interface.write(b'\x02')  # Ctrl-B: Back to REPL mode
            state.serial_interface.write(b'\x04')  # Ctrl-D: Reset micropython board
            state.serial_interface.flush()
            state.serial_interface.reset_output_buffer()
            state.serial_interface.reset_input_buffer()
            state.serial_interface.close()
            logger.info("Disconnected successfully")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    state.connected = False
    state.serial_interface = None
    state.serial_lock = None


# ============================================================================
# PLOT UPDATE FUNCTIONS
# ============================================================================

# Plot references (will be set when UI is created)
plot_output_ref = None
plot_input_ref = None


async def update_plots_from_microcontroller():
    """
    Update plot data from microcontroller (called by ui.timer)

    This function is called at UPDATE_FREQUENCY (20Hz) and:
    1. Reads current sample from the active controller (PID or State-space)
    2. Appends data to circular buffers
    3. Updates the Plotly figures
    """
    if not state.connected:
        return

    try:
        # Get sample data from appropriate controller
        if state.controller_type == 'pid':
            data = await serial_eval('pid.sample')
        else:  # 'ss'
            data = await serial_eval('ss.sample')

        # Validate data
        if data and isinstance(data, (list, tuple)) and len(data) >= 3:
            state.plot_data['stepper'].append(float(data[0]))
            state.plot_data['encoder'].append(float(data[1]))
            state.plot_data['control'].append(float(data[2]))
            state.plot_data['time'].append(state.sample_counter)
            state.sample_counter += 1

            # Update both plots
            update_plot_output()
            update_plot_input()

    except Exception as e:
        logger.error(f"Plot update error: {e}")


def update_plot_output():
    """Update output plot (stepper steps and encoder ticks)"""
    if plot_output_ref is None:
        return

    # Create Plotly figure with dual y-axes
    fig = go.Figure()

    # Stepper steps (left y-axis)
    fig.add_trace(go.Scatter(
        x=list(state.plot_data['time']),
        y=list(state.plot_data['stepper']),
        mode='lines',
        name='Stepper Steps',
        line=dict(color='#3b82f6', width=2),
        yaxis='y'
    ))

    # Encoder ticks (right y-axis)
    fig.add_trace(go.Scatter(
        x=list(state.plot_data['time']),
        y=list(state.plot_data['encoder']),
        mode='lines',
        name='Encoder Ticks',
        line=dict(color='#10b981', width=2),
        yaxis='y2'
    ))

    # Update layout
    fig.update_layout(
        title='Output: Stepper Steps & Encoder Ticks',
        xaxis=dict(title='Sample Number'),
        yaxis=dict(
            title='Stepper Steps',
            titlefont=dict(color='#3b82f6'),
            tickfont=dict(color='#3b82f6')
        ),
        yaxis2=dict(
            title='Encoder Ticks',
            titlefont=dict(color='#10b981'),
            tickfont=dict(color='#10b981'),
            overlaying='y',
            side='right'
        ),
        template='plotly_dark',
        showlegend=True,
        legend=dict(x=0.01, y=0.99),
        height=300,
        margin=dict(l=60, r=60, t=40, b=40)
    )

    plot_output_ref.update_figure(fig)


def update_plot_input():
    """Update input plot (control signal)"""
    if plot_input_ref is None:
        return

    # Create Plotly figure
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=list(state.plot_data['time']),
        y=list(state.plot_data['control']),
        mode='lines',
        name='Control Signal',
        line=dict(color='#f59e0b', width=2)
    ))

    # Update layout
    fig.update_layout(
        title='Input: Control Signal',
        xaxis=dict(title='Sample Number'),
        yaxis=dict(title='Control Value'),
        template='plotly_dark',
        showlegend=True,
        legend=dict(x=0.01, y=0.99),
        height=300,
        margin=dict(l=60, r=60, t=40, b=40)
    )

    plot_input_ref.update_figure(fig)


# ============================================================================
# REPL EXECUTION FUNCTIONS
# ============================================================================

async def execute_python(command: str, output_log) -> None:
    """
    Execute Python command locally in the application context

    Args:
        command: Python code to execute
        output_log: ui.log widget to write output to
    """
    if not command.strip():
        return

    # Add to history
    state.python_history.append(command)

    # Display command
    output_log.push(f'>>> {command}')

    result = None
    try:
        # Try eval first (for expressions)
        result = eval(command, globals())
        if result is not None:
            _ = result  # Store in '_' variable
            state.python_results.appendleft(result)
            output_log.push(str(result))
    except SyntaxError:
        try:
            # Try exec for statements
            exec(command, globals())
        except Exception as e:
            output_log.push(f'Error: {e}')
            state.python_results.appendleft(f'Error: {e}')
    except Exception as e:
        output_log.push(f'Error: {e}')
        state.python_results.appendleft(f'Error: {e}')


async def execute_micropython(command: str, output_log) -> None:
    """
    Execute command on MicroPython board via serial

    Args:
        command: MicroPython code to execute
        output_log: ui.log widget to write output to
    """
    if not command.strip():
        return

    if not state.connected:
        output_log.push('Error: Not connected to microcontroller')
        return

    # Add to history
    state.micropython_history.append(command)

    # Display command
    output_log.push(f'>>> {command}')

    # Check if accessing local results/tasks
    if command.startswith('micropython_results') or command.startswith('python_results'):
        try:
            result = eval(command, globals())
            output_log.push(str(result))
        except Exception as e:
            output_log.push(f'Error: {e}')
        return

    try:
        result = await serial_eval(command)
        if result is not None and result != '':
            state.micropython_results.appendleft(result)
            output_log.push(str(result))
    except Exception as e:
        output_log.push(f'Error: {e}')


# ============================================================================
# DATA LOGGING FUNCTIONS
# ============================================================================

async def start_logging(num_buffers: int, append_datetime: bool, status_label, log_button):
    """
    Start data logging from microcontroller

    This function:
    1. Configures logging on the microcontroller
    2. Polls for completed buffers
    3. Retrieves buffer data when ready
    4. Saves to CSV file with optional datetime stamp

    Args:
        num_buffers: Number of buffers to log (each buffer is LOG_BUF_LEN samples)
        append_datetime: Whether to append datetime to filename
        status_label: ui.label to update with status
        log_button: ui.button to disable during logging
    """
    logger.info(f"Starting data logging: {num_buffers} buffers")

    state.logging = True
    log_button.set_enabled(False)
    status_label.set_text('Logging...')

    log_num_samples = num_buffers * LOG_BUF_LEN
    state.log_data = np.zeros((log_num_samples, 3))
    log_buf_counter = 0

    try:
        # Configure logging on microcontroller
        await serial_eval(f"supervisory['log_num_samples']={log_num_samples}")
        await serial_eval(f"supervisory['log_ready']=False")
        await serial_eval(f"supervisory['log']=True")

        log = await serial_eval("supervisory['log']")
        log0_prev = False
        log1_prev = False

        # Poll for completed buffers
        while log:
            log0 = await serial_eval("supervisory['log0']")
            log1 = await serial_eval("supervisory['log1']")

            # Detect buffer completion (True -> False transition)
            if log0_prev and not log0:  # log0 finished
                log0_data = await serial_eval("supervisory['log0_data']")
                state.log_data[log_buf_counter * LOG_BUF_LEN:(log_buf_counter + 1) * LOG_BUF_LEN, :] = np.array(log0_data).T
                log_buf_counter += 1
                status_label.set_text(f'Logging... ({log_buf_counter}/{num_buffers} buffers)')
                logger.info(f"Retrieved buffer {log_buf_counter}/{num_buffers}")

            elif log1_prev and not log1:  # log1 finished
                log1_data = await serial_eval("supervisory['log1_data']")
                state.log_data[log_buf_counter * LOG_BUF_LEN:(log_buf_counter + 1) * LOG_BUF_LEN, :] = np.array(log1_data).T
                log_buf_counter += 1
                status_label.set_text(f'Logging... ({log_buf_counter}/{num_buffers} buffers)')
                logger.info(f"Retrieved buffer {log_buf_counter}/{num_buffers}")

            else:
                # Sleep for estimated buffer fill time
                await asyncio.sleep(round(0.1 * LOG_BUF_LEN * SAMPLING_TIME))

            log0_prev = log0
            log1_prev = log1
            log = await serial_eval("supervisory['log']")

        # Save to CSV
        fname = "log_data"
        if append_datetime:
            fname += "_" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        fname += '.csv'

        df = pd.DataFrame(
            state.log_data,
            columns=['Stepper_Steps', 'Encoder_Ticks', 'Control_Signal']
        )
        df.to_csv(fname, index=True, index_label='Sample')

        state.logging = False
        log_button.set_enabled(True)
        status_label.set_text(f'Saved: {fname}')
        ui.notify(f'Data saved to {fname}', type='positive')
        logger.info(f"Data logging complete: {fname}")

    except Exception as e:
        state.logging = False
        log_button.set_enabled(True)
        status_label.set_text('Logging failed!')
        ui.notify(f'Logging error: {e}', type='negative')
        logger.error(f"Logging failed: {e}")


# ============================================================================
# UI COMPONENTS
# ============================================================================

def create_left_panel():
    """
    Create left control panel (data logging and manual controls)

    Contains:
    - Data logging configuration
    - Log status and button
    - Reference/control add toggles
    - Stepper zero button
    """
    with ui.card().classes('w-64'):
        ui.label('Data Logging').classes('text-xl font-bold mb-2')
        ui.separator()

        ui.label('Number of buffers:').classes('mt-2')
        ui.label(f'(1 buffer = {LOG_BUF_LEN} samples @ {int(1/SAMPLING_TIME)}Hz)').classes('text-xs opacity-70')
        num_bufs = ui.number(value=1, min=1, max=100, format='%d').classes('w-full')

        ui.label('Append datetime to filename:').classes('mt-4')
        datetime_switch = ui.switch(value=True)

        log_status = ui.label('Ready').classes('text-sm mt-2 font-mono')
        log_button = ui.button(
            'Start Logging',
            on_click=lambda: asyncio.create_task(
                start_logging(
                    int(num_bufs.value),
                    datetime_switch.value,
                    log_status,
                    log_button
                )
            ),
            icon='save'
        ).classes('w-full mt-2').props('color=primary')

        ui.separator().classes('my-4')

        ui.label('Manual Controls').classes('text-lg font-bold mb-2')

        # Reference add toggle
        ref_add = ui.switch(text='Reference Add', value=False).classes('mb-2')
        ref_add.on('update:model-value', lambda e: asyncio.create_task(
            serial_eval(f"supervisory['reference_add']={e.args}")
        ))

        # Control add toggle
        ctrl_add = ui.switch(text='Control Add', value=False).classes('mb-2')

        async def handle_control_add(e):
            await serial_eval(f"supervisory['control_add']={e.args}")
            if not e.args:  # When turning off, zero the stepper
                await serial_eval('stepper.set_period_direction(0)')

        ctrl_add.on('update:model-value', lambda e: asyncio.create_task(handle_control_add(e)))

        ui.separator().classes('my-2')

        # Stepper zero button
        ui.button(
            'Stepper Zero',
            on_click=lambda: asyncio.create_task(serial_eval('stepper.set_period_direction(0)')),
            icon='restart_alt'
        ).classes('w-full').props('color=warning')


def create_center_panel():
    """
    Create center panel (plots and REPL consoles)

    Contains:
    - Elapsed time display
    - Output plot (stepper + encoder)
    - Input plot (control signal)
    - Python REPL (left)
    - MicroPython REPL (right)
    """
    global plot_output_ref, plot_input_ref

    with ui.column().classes('flex-grow'):
        # Timer display
        timer_label = ui.label('00:00:00.00').classes('text-2xl font-mono font-bold text-center mb-2')

        def update_timer():
            elapsed = time.monotonic() - state.start_time
            minutes, seconds = divmod(elapsed, 60)
            hours, minutes = divmod(minutes, 60)
            timer_label.set_text(f'{int(hours):02d}:{int(minutes):02d}:{seconds:05.2f}')

        ui.timer(0.1, update_timer)

        # Output plot (stepper + encoder)
        with ui.card().classes('w-full'):
            plot_output_ref = ui.plotly(go.Figure(
                layout=go.Layout(
                    title='Output: Stepper Steps & Encoder Ticks',
                    template='plotly_dark',
                    height=300
                )
            )).classes('w-full')

        # Input plot (control)
        with ui.card().classes('w-full'):
            plot_input_ref = ui.plotly(go.Figure(
                layout=go.Layout(
                    title='Input: Control Signal',
                    template='plotly_dark',
                    height=300
                )
            )).classes('w-full')

        # REPL consoles side by side
        with ui.row().classes('w-full gap-2'):
            # Python REPL
            with ui.card().classes('flex-grow'):
                ui.label('Python REPL').classes('text-lg font-bold')
                ui.label('Press Enter to execute, access results with python_results[0]').classes('text-xs opacity-70')

                py_output = ui.log(max_lines=100).classes('w-full h-64 font-mono text-sm bg-gray-900')
                py_output.push('Python REPL ready')
                py_output.push('Variables: state, python_results, micropython_results')

                py_input = ui.input(placeholder='Python command...').classes('w-full font-mono')
                py_input.on('keydown.enter', lambda: (
                    asyncio.create_task(execute_python(py_input.value, py_output)),
                    py_input.set_value('')
                ))

            # MicroPython REPL
            with ui.card().classes('flex-grow'):
                ui.label('MicroPython REPL').classes('text-lg font-bold')
                ui.label('Press Enter to execute, access results with micropython_results[0]').classes('text-xs opacity-70')

                mpy_output = ui.log(max_lines=100).classes('w-full h-64 font-mono text-sm bg-gray-900')
                mpy_output.push('MicroPython REPL ready')
                mpy_output.push('Objects: pid, ss, stepper, encoder, supervisory, ctrlparam')

                mpy_input = ui.input(placeholder='MicroPython command...').classes('w-full font-mono')
                mpy_input.on('keydown.enter', lambda: (
                    asyncio.create_task(execute_micropython(mpy_input.value, mpy_output)),
                    mpy_input.set_value('')
                ))


def create_right_panel():
    """
    Create right control panel (controller settings)

    Contains:
    - Controller type selection (PID / State-space)
    - PID control toggles
    - Reset PID button
    - State-space run toggle
    """
    with ui.card().classes('w-64'):
        ui.label('Controller').classes('text-xl font-bold mb-2')
        ui.separator()

        # Controller type selection
        ui.label('Controller Type:').classes('mt-2 font-bold')

        async def set_controller_type(e):
            if e.value == 'PID':
                ctrl_type_str = 'pid'
                state.controller_type = 'pid'
            else:
                ctrl_type_str = 'state_space'
                state.controller_type = 'ss'
            await serial_eval(f'ctrlparam["type"]="{ctrl_type_str}"')
            logger.info(f"Controller type set to: {ctrl_type_str}")

        ctrl_radio = ui.radio(
            options=['PID', 'State-space'],
            value='PID'
        ).props('inline').on('update:model-value', lambda e: asyncio.create_task(set_controller_type(e)))

        ui.separator().classes('my-4')

        # PID controls
        ui.label('PID Controls').classes('text-lg font-bold mb-2')

        pid_run = ui.switch(text='pid.run (Master)', value=False)
        pid_run.on('update:model-value', lambda e: asyncio.create_task(
            serial_eval(f'pid.run={e.args}')
        ))

        pid_run1 = ui.switch(text='pid.run1 (Stepper)', value=True)
        pid_run1.on('update:model-value', lambda e: asyncio.create_task(
            serial_eval(f'pid.run1={e.args}')
        ))

        pid_run2 = ui.switch(text='pid.run2 (Encoder)', value=True)
        pid_run2.on('update:model-value', lambda e: asyncio.create_task(
            serial_eval(f'pid.run2={e.args}')
        ))

        ui.button(
            'Reset PID State',
            on_click=lambda: asyncio.create_task(serial_eval('pid.reset_state()')),
            icon='refresh'
        ).classes('w-full mt-2').props('color=secondary')

        ui.separator().classes('my-4')

        # State-space controls
        ui.label('State-Space Controls').classes('text-lg font-bold mb-2')

        ss_run = ui.switch(text='ss.run', value=False)
        ss_run.on('update:model-value', lambda e: asyncio.create_task(
            serial_eval(f'ss.run={e.args}')
        ))


async def create_connection_dialog():
    """
    Create serial port connection dialog

    Auto-detects STMicroelectronics ports and allows manual port selection.
    Returns a NiceGUI dialog that can be opened.
    """
    # Auto-detect ports
    ports = list_ports.comports()
    stm_ports = [
        port.device for port in ports
        if port.manufacturer and 'STMicroelectronics' in port.manufacturer
    ]
    all_ports = [port.device for port in ports]

    # Default to STM port if found, otherwise first available
    default_port = stm_ports[0] if stm_ports else (all_ports[0] if all_ports else None)

    with ui.dialog() as dialog, ui.card().classes('w-96'):
        ui.label('Connect to Microcontroller').classes('text-2xl font-bold mb-4')
        ui.separator()

        if not all_ports:
            ui.label('⚠ No serial ports detected!').classes('text-red-500 text-lg mb-4')
            ui.label('Please check:').classes('font-bold')
            ui.label('• USB cable is connected').classes('ml-4')
            ui.label('• Microcontroller is powered on').classes('ml-4')
            ui.label('• Drivers are installed (Windows)').classes('ml-4')
            ui.button('Retry', on_click=lambda: (dialog.close(), asyncio.create_task(show_connection_dialog()))).classes('mt-4')
            return dialog

        ui.label('Select serial port:').classes('mt-4 font-bold')
        port_select = ui.select(
            options=all_ports,
            value=default_port,
            label='Serial Port'
        ).classes('w-full')

        if stm_ports:
            ui.label(f'✓ Auto-detected STMicroelectronics on {default_port}').classes('text-green-500 text-sm mt-2')
        else:
            ui.label('⚠ STMicroelectronics device not auto-detected').classes('text-yellow-600 text-sm mt-2')

        status_label = ui.label('').classes('text-sm mt-4 font-mono')

        async def do_connect():
            status_label.set_text('Connecting...')
            success, message = await connect_serial(port_select.value)

            if success:
                status_label.set_text('✓ Connected!')
                ui.notify(message, type='positive')

                # Start update timer
                state.update_timer = ui.timer(1.0 / UPDATE_FREQUENCY, update_plots_from_microcontroller)

                await asyncio.sleep(0.5)
                dialog.close()
            else:
                status_label.set_text(f'✗ {message}')
                ui.notify(message, type='negative')

        with ui.row().classes('w-full gap-2 mt-4'):
            ui.button('Connect', on_click=lambda: asyncio.create_task(do_connect())).props('color=primary').classes('flex-grow')
            ui.button('Cancel', on_click=app.shutdown).props('color=negative')

    return dialog


async def show_connection_dialog():
    """Show the connection dialog"""
    dialog = await create_connection_dialog()
    dialog.open()


# ============================================================================
# MAIN APPLICATION
# ============================================================================

@ui.page('/')
async def main_page():
    """
    Main application page with three-column layout

    Layout:
    - Header with title and theme toggle
    - Left panel: Data logging controls
    - Center panel: Plots and REPLs
    - Right panel: Controller settings
    - Footer with status
    """

    # Check single-user access
    if state.connection_in_use:
        with ui.column().classes('items-center justify-center h-screen'):
            ui.label('⚠ Application Already in Use').classes('text-3xl font-bold text-red-500 mb-4')
            ui.label('Another user is currently connected to the hardware.').classes('text-xl mb-2')
            ui.label('Please wait for them to disconnect.').classes('text-lg opacity-70')
            ui.button('Retry', on_click=lambda: ui.open('/')).classes('mt-4')
        return

    # Mark as in use
    state.connection_in_use = True

    # Set dark theme by default
    dark = ui.dark_mode()
    dark.enable()

    # Header
    with ui.header().classes('items-center'):
        ui.label('Edukit Pendulum Control').classes('text-2xl font-bold')
        ui.label('MicroPython + NiceGUI').classes('text-sm opacity-70 ml-4')
        ui.space()  # Push theme toggle to the right
        ui.button(
            icon='dark_mode',
            on_click=dark.toggle
        ).props('flat round').tooltip('Toggle dark/light mode')

    # Show connection dialog
    await show_connection_dialog()

    # Main three-column layout
    with ui.row().classes('w-full gap-4 p-4'):
        create_left_panel()
        create_center_panel()
        create_right_panel()

    # Footer
    with ui.footer().classes('bg-gray-800'):
        ui.label('Edukit MicroPython Pendulum Control').classes('text-sm opacity-70')
        ui.space()
        connection_status = ui.label('').classes('text-sm font-mono')

        def update_connection_status():
            if state.connected:
                connection_status.set_text('🟢 Connected')
                connection_status.classes('text-green-500')
            else:
                connection_status.set_text('🔴 Disconnected')
                connection_status.classes('text-red-500')

        ui.timer(1.0, update_connection_status)

    # Cleanup on page close
    def on_disconnect():
        logger.info("User disconnected")
        disconnect_serial()
        if state.update_timer:
            state.update_timer.deactivate()
        state.connection_in_use = False

    app.on_disconnect(on_disconnect)


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ in {"__main__", "__mp_main__"}:
    logger.info("Starting Edukit NiceGUI application")

    # Run NiceGUI app
    ui.run(
        title='Edukit Pendulum Control',
        dark=True,
        reload=False,
        show=True,
        port=8080,
        favicon='🎛️'
    )

    # Cleanup on exit
    disconnect_serial()
    logger.info("Application shut down")

