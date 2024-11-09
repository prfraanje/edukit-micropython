import asyncio
import sys
import micropython
import gc


# simplified version of aiorepl by https://github.com/micropython/micropython-lib/blob/master/micropython/aiorepl/aiorepl.py
async def repl(namespace=None,tasks_to_cancel_on_stop=[]):
    END_PATTERN = const(b'\x04') #const(b'$@')
    END_PATTERN_LEN = len(END_PATTERN)
    #BUF_SIZE=const(64)
    
    if namespace is None:
        namespace == __import__("__main__").__dict__
        
    stream_in = asyncio.StreamReader(sys.stdin)
    stream_out = asyncio.StreamWriter(sys.stdout)
    micropython.kbd_intr(-1) # disable C-c
    while True:
        resp = b''
        b = await stream_in.read(END_PATTERN_LEN)
        resp += b
        pattern = resp[-END_PATTERN_LEN:]
        while not (pattern == END_PATTERN):
            b = await stream_in.read(1)
            resp += b
            pattern = resp[-END_PATTERN_LEN:]
        cmd = resp[:-(END_PATTERN_LEN)].decode('utf-8')
        if cmd == "stop":
            break
        
        try:
            #gc.collect()
            await stream_out.awrite(str(eval(cmd,namespace)).encode('utf-8'))
            await stream_out.awrite(END_PATTERN)
        except: # SyntaxError:
            try:
                #gc.collect()
                exec(cmd,namespace)
                await stream_out.awrite(END_PATTERN)                
            except Exception as e:
                await stream_out.awrite(("Exception: "+str(e)).encode('utf-8')+END_PATTERN) # prefix with Exception, so it can be filtered to prevent evaluation
        #gc.collect()
        
    micropython.kbd_intr(3) # enable C-c    
