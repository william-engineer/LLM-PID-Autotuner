import serial
import logging

class SerialPort:
    """
    串口通信封装类
    只负责底层串口连接、收发、状态管理
    """
    def __init__(self,port: str,baudrate: int,bytesize: int = None,parity: str = None,stopbits: float = None):
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize if bytesize is not None else serial.EIGHTBITS
        self.parity = parity if parity is not None else serial.PARITY_NONE
        self.stopbits = stopbits if stopbits is not None else serial.STOPBITS_ONE
        self.serial = None
        self.logger = logging.getLogger("SerialPort")

    def connect(self):
        try:
            self.serial = serial.Serial(self.port, self.baudrate, bytesize=self.bytesize, parity=self.parity, stopbits=self.stopbits, timeout=1)
            self.logger.info(f"串口 {self.port} 连接成功")
            return True
        except Exception as e: 
            self.logger.error(f"无法连接串口 {self.port} at {self.baudrate} baud: {e}")
            return False
        
    def disconnect(self):
        if self.serial: self.serial.close()

    def write_command(self, cmd: str):
        if not self.serial:
            return False
        try:
            if isinstance(cmd, str):
                data = cmd.encode('utf-8')
            else:
                data = cmd
            self.serial.write(data)
            try:
                self.serial.flush()
            except Exception:
                pass
            return True
        except Exception as e:
            self.logger.error(f"send_command failed: {e}")
            return False