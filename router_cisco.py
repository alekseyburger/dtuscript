# GNU GENERAL PUBLIC LICENSE
# Autor: Aleksey Burger

import telnetlib
import time
import re
import logging
from curses import ascii
from exception_dev import ExceptionDevice

# Configure section "dtulib" in [dtutest]/loggin.conf to manage logging for this module
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

def paraseResponce(string) -> (str, str) :
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
    if len(found) > 1:
        # name is before '(config' or at the end of string if '(config' is not found
        name = found[-2].split('(')[0] if '(' in found[-2] else found[-2]
    else:
        name = '<noname>'
    return (mode, name.strip())

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
            self.toExec()

        except Exception as inst:
            error_text = "start except " + str(type(inst))
            if not self.ignore_exception_connection:
                raise Exception(error_text)
            error(error_text)    # the exception instance

    def end(self):
            self.tn.close()

    def waitPrompt(self) -> bool:
        ''' 
        Wait for prompt and define mode and name of router. Return True if prompt is found, False if not
        self.mode is set to one of MODES or NONE_MODE if prompt is not found
        self.name is set to router name if prompt is found or <unknown> if not
        '''

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
                    self.enterWaitResponce("ena", "assword:")
                    self.enterWaitResponce(self.password, self.name+"#")
                else:
                    self.enterWaitResponce("ena", self.name+"#")
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
                self.enterWaitResponce("config term", "(config)#")
                continue
            repeat -= 1
        raise Exception(f"{self.name}: Can't get Config mode")


    def enterWaitResponce(self, command, expect=None):
            """ enterWaitResponce(command, expect)  sent command and wait expected respoce """
            if not expect:
                expect = f'{self.name}'
                if self.mode == USER_MODE:
                    expect = expect + ">"
                else:
                    expect = expect + "#"
            device_log(f"{self.name} ENTER: {command} EXPECT: {expect} MODE: {self.mode}")
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
              
            device_log(f"RESPONCE: {self.resp}")
            invalid_input = re.findall(r'^\%',self.resp,re.MULTILINE)
            if len(invalid_input) and not self.ignore_exception_syntax:
                raise ExceptionDevice("syntax error", self.resp)

    def enterExecCommand(self, command):
            """Execute an exec-mode command from any mode.

            If the router is in CONFIG modes, the command is prefixed with
            'do '. If the router is in USER mode, it switches to EXEC mode
            first. In EXEC mode, the command is executed as-is.

            Args:
                command (str): The exec mode command to execute (e.g. 'show ip int br').
                expect (str, optional): Explicit expected prompt. If not provided,
                    the default logic of enterWaitResponce() is used.
            """

            # Ensure we know the current mode if it's not set yet
            if self.mode == EXEC_MODE:
                self.enterWaitResponce(command, '#')
            elif self.mode in [CONFIG_MODE, CONFIG_DEEP_MODE]:
                self.enterWaitResponce(f"do {command}", ')#')
            else:
                # Go to EXEC (enable) and run the command
                self.toExec()
                self.enterWaitResponce(command, '#')

    def __probe_command__(self, verb, address, vrf=None, source=None, **extra):
        """Build a 'ping'/'traceroute' command line.

        IOS wants the pieces in a fixed order:
            <verb> [vrf <name>] <address> [source <x>] [<extra> <value>...]
        The vrf keyword comes before the destination, everything else after.

        Args:
            verb (str): 'ping' or 'traceroute'.
            address (str): destination IPv4 address.
            vrf (str|CiscoVrf, optional): VRF to send from. An object with a
                .name is accepted as well as a plain name.
            source (str|CiscoInterface, optional): source interface or address.
            **extra: further 'keyword value' pairs appended in order.
        """
        if not address:
            raise Exception("RouterCisco: destination address is required")

        # accept config objects as well as plain strings
        vrf_name = getattr(vrf, 'name', vrf)
        source_name = getattr(source, 'name', source)

        command = verb
        if vrf_name:
            command += f" vrf {vrf_name}"
        command += f" {address}"
        if source_name:
            command += f" source {source_name}"
        for keyword, value in extra.items():
            if value is not None:
                command += f" {keyword} {value}"
        return command

    def ping(self, address, vrf=None, source=None, counter=None):
        """Ping an IPv4 address and return the success rate as a percentage.

        Args:
            address (str): destination IPv4 address.
            vrf (str|CiscoVrf, optional): VRF to send from.
            source (str|CiscoInterface, optional): source interface or address.
            counter (int, optional): number of echos to send ('repeat' on IOS).
                The device default is 5 when omitted.

        Returns:
            int: success rate, 0 to 100. Zero is falsy, so
                'if not router.ping(addr):' reads as "no connectivity", while
                the number is there when an exact rate matters. A first packet
                lost to ARP shows as 80 with the default repeat of 5, which is
                normal on a quiet link rather than a failure.

            The raw device output stays in self.resp. An unparsable reply
            returns 0 and is logged.
        """
        command = self.__probe_command__('ping', address, vrf, source,
                                         repeat=counter)
        self.enterExecCommand(command)

        match = re.findall(r'Success rate is (\d+) percent', self.resp)
        if not match:
            error(f"ping {address}: no success rate in reply")
            return 0
        rate = int(match[0])
        info(f"ping {address}: {rate} percent")
        return rate

    def trace(self, address, vrf=None, source=None):
        """Traceroute to an IPv4 address and return the raw device output.

        Args:
            address (str): destination IPv4 address.
            vrf (str|CiscoVrf, optional): VRF to send from.
            source (str|CiscoInterface, optional): source interface or address.

        Returns:
            str: the device reply, also left in self.resp. Hops are not parsed -
                the output shape varies too much between unreachable, timed out
                and administratively blocked paths to be worth guessing at.

        Note this can block for a while: unreachable hops time out one probe at
        a time, and read_until() has no timeout.
        """
        command = self.__probe_command__('traceroute', address, vrf, source)
        self.enterExecCommand(command)
        return self.resp



