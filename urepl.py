import asyncio
import sys
import micropython
import gc


# simplified version of aiorepl by https://github.com/micropython/micropython-lib/blob/master/micropython/aiorepl/aiorepl.py
async def repl(namespace=None):
    END_PATTERN = const(b'\x04') #const(b'$@')
    END_PATTERN_LEN = len(END_PATTERN)
    #BUF_SIZE=const(64)
    
    if namespace is None:
        namespace = __import__("__main__").__dict__
        
    stream_in = asyncio.StreamReader(sys.stdin)
    stream_out = asyncio.StreamWriter(sys.stdout)
    micropython.kbd_intr(-1) # disable C-c
    while True:
        gc.collect()
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
            stream_out.write(repr(eval(cmd,namespace)).encode('utf-8'))
            stream_out.write(END_PATTERN)
        except: # SyntaxError:
            try:
                exec(cmd,namespace)
                stream_out.write(END_PATTERN)                
            except Exception as e:
                stream_out.write(("Exception: "+str(e)).encode('utf-8')+END_PATTERN) # prefix with Exception, so it can be filtered to prevent evaluation
        await stream_out.drain()        

    micropython.kbd_intr(3) # enable C-c
    
