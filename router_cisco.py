# GNU GENERAL PUBLIC LICENSE
# Autor: Aleksey Burger

import telnetlib
import time
import re
import logging
from curses import ascii
from exception_dev import exception_dev

logger = logging.getLogger("dtulibLog")
def trace(format):
    logger.debug(f'\n\x1b[1;94mCisco: {format}\x1b[0m')

def error(format):
    logger.error(f'\n\x1b[1;31mCisco: {format}\x1b[0m')

def info(format):
    logger.info(f'\n\x1b[1;92mCisco: {format}\x1b[0m')

device_logger = logging.getLogger("deviceLog")
def device_log(format):
    device_logger.info(f'{format}')

NONE_MODE = "none"
EXEC_MODE = "exec"
USER_MODE = "user"
CONFIG_MODE = "config"
CONFIG_DEEP_MODE = "config-deep"
MODES = [USER_MODE, EXEC_MODE, CONFIG_MODE, CONFIG_DEEP_MODE]

def paraseResponce(string):
    """
        It gets router responce as parameter 'string', extracts last char that
        indicates the mode
        Return:
            mode as string 
            router name
    """
    #remove unprintable
    string = ''.join([ c for c in string if c.isprintable() ])
    # define 3 match groups:
    # left: anything that finish with # or >
    # midle: string between left and right
    # right: > or # at the end of string
    founds = re.findall(r'(.*[#>]+)*(.+)([#>])$', string)
    if not founds:
        return (NONE_MODE, "")
    found = founds[0]
    #print(found)
    # found: use right substring as mode indicator
    lastChar = found[-1]
    mode = {
        '>': USER_MODE,
        '#': EXEC_MODE,
    }.get(lastChar, "unknown")
    if mode == EXEC_MODE:
        check_config = re.findall(r'\S*(\(config)(.*\))', found[-2])
        if len(check_config) != 0: # '(config' and '...)' found
            if check_config[0][-1] == ')':  # we are in config root
                mode = CONFIG_MODE
            else:
                mode = CONFIG_DEEP_MODE
    return (mode, found[-2] if len(found) > 1 else '' )

class RouterCisco:

    def __init__(self, ipAddress, port, user, password):
        self.ipAddress = ipAddress
        self.port = port
        self.password = password
        self.mode = NONE_MODE
        self.repeat = 10
        self.resp = None

        self.name = "<unknown>"
        self.ignore_exception_connection = False
        self.ignore_exception_syntax  = False

    def start(self):
        
        try:
            self.tn = telnetlib.Telnet(self.ipAddress, self.port)
            self.waitPrompt()

        except Exception as inst:
            error_text = "start except " + str(type(inst))
            if not self.ignore_exception_connection:
                raise Exception(error_text)
            error(error_text)    # the exception instance

    def end(self):
            self.tn.close()

    def waitPrompt(self):

        repeat = self.repeat

        while repeat != 0:
            try:
                # clean input buffer
                while self.tn.read_very_eager() != b'':
                    pass

                # enter empty line - server will return with prompt
                trace(f"waitPrompt send <cr>")
                self.tn.write(b'\r')
                time.sleep(1)

                # read server responce and analyze it
                trace(f"waitPrompt read")
                respBin = self.tn.read_eager()

                resp = ''.join([ c for c in respBin.decode("utf-8") if c.isprintable() ])
                trace(f"waitPrompt read: bin: {respBin} decode: {resp}")

                self.mode, self.name = paraseResponce(resp)
                # if self.mode not in [USER_MODE, EXEC_MODE] or not self.name.strip():
                if self.mode == NONE_MODE or not self.name.strip():
                    trace(f"waitPrompt unexpected mode {self.mode}. Try to repeat {repeat}")
                    repeat -= 1
                    continue

                # succes
                trace(f"waitPrompt succ. name: `{self.name}` mode {self.mode}")
                return True

            except Exception as inst:
                error_text = "waitPrompt Exception read: " + str(type(inst))
                if repeat == 0 and not self.ignore_exception_connection:
                    raise Exception(error_text)
                error(error_text)    # the exception instance
                repeat -= 1

        return False

    def toUser(self):

        repeat = self.repeat
        if self.mode == NONE_MODE and not self.waitPrompt():
            error("Connection closed!")
            return
        while self.mode != USER_MODE and repeat != 0:
            self.tn.write(b"exit\n")
            self.waitPrompt()
            repeat -= 1

    def toExec(self):
        repeat = self.repeat
        while repeat:
            self.waitPrompt()
            if self.mode == EXEC_MODE:
                return
            if self.mode == USER_MODE:
                if len(self.password):
                    self.writeWithResponce("ena", "assword:")
                    self.writeWithResponce(self.password, self.name+"#")
                else:
                    self.writeWithResponce("ena", self.name+"#")
                continue
            if self.mode in [CONFIG_MODE, CONFIG_DEEP_MODE]:
                self.tn.write(ascii.ctrl('z').encode('utf-8'))
                continue
            repeat -= 1
        raise Exception(f"{self.name}:Can't get Exec mode")

    def toConfig(self):
        repeat = self.repeat
        while repeat:
            self.waitPrompt()
            if self.mode == CONFIG_MODE:
                return
            if self.mode == CONFIG_DEEP_MODE:
                self.tn.write(b"exit\n")
                continue
            if self.mode == USER_MODE:
                self.toExec()
                continue
            if self.mode == EXEC_MODE:
                self.writeWithResponce("config term", "(config)#")
                continue
            repeat -= 1
        raise Exception(f"{self.name}: Can't get Config mode")


    def writeWithResponce(self, command, expect=None):
            """ writeWithResponce(command, expect)  sent command and wait expected respoce """
            if not expect:
                expect = f'{self.name}'
                if self.mode == USER_MODE:
                    expect = expect + ">"
                else:
                    expect = expect + "#"
            try:
                command += "\n"
                trace(f"SEND: {command}  EXPEXT:{expect}")
                self.tn.write(command.encode("utf-8"))
                self.resp = self.tn.read_until(expect.encode("utf-8")).decode("utf-8")
                trace(f"RCV: {self.resp}")
            except Exception as inst:
                error_text = "write error: " + str(type(inst))
                if not self.ignore_exception_connection:
                    raise Exception(error_text) 
                error(error_text)    # the exception instance
                return
              
            device_log(f"{self.resp}")
            invalid_input = re.findall(r'^\%',self.resp,re.MULTILINE)
            if len(invalid_input) and not self.ignore_exception_syntax:
                raise exception_dev("syntax error", self.resp)



