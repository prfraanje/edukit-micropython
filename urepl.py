import uasyncio as asyncio
import sys
import micropython
import gc


# simplified version of aiorepl by https://github.com/micropython/micropython-lib/blob/master/micropython/aiorepl/aiorepl.py
async def repl(namespace=None,tasks_to_cancel_on_stop=[]):
    END_PATTERN = const(b'\r\n<-> ')
    #BUF_SIZE=const(256)
    BUF_SIZE=const(64)
    #BUF_SIZE=const(1024)
    
    if namespace is None:
        namespace == __import__("__main__").__dict__
        
    stream_in = asyncio.StreamReader(sys.stdin)
    stream_out = asyncio.StreamWriter(sys.stdout)
    micropython.kbd_intr(-1) # disable C-c
    while True:
        cmd = b''
        while True:
            b = await stream_in.read(1)
            if ord(b) == 0xa: # on newline (ord(b'\n') => 0xa)
                break
            if ord(b) == 0x3: # cancel input on C-c
                cmd = b''
            else:
                cmd += b
        if cmd == b'stop':
            await stream_out.awrite(b'"stop" was entered, so stopping now!\n'+END_PATTERN)
            #for task in tasks_to_cancel_on_stop:
            #    task.cancel()
            namespace['supervisory']['control'] = False
            break

        cmd = cmd.decode('utf-8')
        try:
            gc.collect()
            #res = str(eval(cmd,namespace))
            print(eval(cmd,namespace))
            await stream_out.awrite(END_PATTERN)
            #await asyncio.sleep_ms(2)
            #print("",end="")
            #print('\r\n',end="")
            #print('<-> ',end="")
            # if not (res == "None"):
            #     for i in range(len(res)//BUF_SIZE+1):
            #         if (i+1)*BUF_SIZE<len(res):
            #             await stream_out.awrite(res[i*BUF_SIZE:(i+1)*BUF_SIZE].encode('utf-8'))
            #         else:
            #             await stream_out.awrite(res[i*BUF_SIZE:].encode('utf-8')+END_PATTERN)
            # else:
            #     await stream_out.awrite( b"None"+END_PATTERN )
        except: # SyntaxError:
            try:
                gc.collect()
                #res = str(exec(cmd,namespace))
                exec(cmd,namespace)
                await stream_out.awrite(END_PATTERN)                
                # if not (res == "None"):
                #     for i in range(len(res)//BUF_SIZE+1):
                #         if (i+1)*BUF_SIZE<len(res):
                #             await stream_out.awrite(res[i*BUF_SIZE:(i+1)*BUF_SIZE].encode('utf-8'))
                #         else:
                #             await stream_out.awrite(res[i*BUF_SIZE:].encode('utf-8')+END_PATTERN)
                # else:
                #     await stream_out.awrite( b"None"+END_PATTERN )
            except Exception as e:
                await stream_out.awrite(("Exception"+str(e)).encode('utf-8')+END_PATTERN) # prefix with Exception, so it can be filtered to prevent evaluation
        gc.collect()
        
    micropython.kbd_intr(3) # enable C-c    
