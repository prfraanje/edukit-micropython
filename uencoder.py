from machine import Pin

class Encoder:
    #__slots__ = "forward", "pin_x", "pin_y", "_x", "_y", "_pos"
    def __init__(self, pin_x, pin_y):
        self.forward = True
        self.pin_x = pin_x
        self.pin_y = pin_y
        self._x = pin_x()
        self._y = pin_y()
        self._pos = 0
        try:
            self.x_interrupt = pin_x.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self.x_callback, hard=True)
            self.y_interrupt = pin_y.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self.y_callback, hard=True)
        except TypeError:
            self.x_interrupt = pin_x.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self.x_callback)
            self.y_interrupt = pin_y.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self.y_callback)

    @micropython.native
    def x_callback(self, pin_x):
        if (x := pin_x()) != self._x:  # Reject short pulses
            self._x = x
            self.forward = x ^ self.pin_y()
            self._pos += 1 if self.forward else -1

    @micropython.native
    def y_callback(self, pin_y):
        if (y := pin_y()) != self._y:
            self._y = y
            self.forward = y ^ self.pin_x() ^ 1
            self._pos += 1 if self.forward else -1

    @micropython.native
    def position(self, value=None):
        if value is not None:
            self._pos = value
        return self._pos

    @micropython.native
    def value(self, value=None):
        if value is not None:
            self._pos = value
        return self._pos
