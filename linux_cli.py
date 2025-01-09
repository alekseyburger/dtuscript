# GNU GENERAL PUBLIC LICENSE
# Autor: Aleksey Burger

import paramiko
import time
import re
import pdb
import logging

logger = logging.getLogger("dtulibLog")

def trace(format):
    logger.debug(f'Linux:{format}')
    pass

def info(format):
    logger.info(f'Linux:{format}')

device_logger = logging.getLogger("deviceLog")
def device_log(format):
    device_logger.info(f'{format}')

NONE_MODE = "none"
EXEC_MODE = "exec"
MODES = [EXEC_MODE]

# catch router name from the prompt:
PATTERN_PROMPT = re.compile(r'\s*\w+@(.*)#$')

def paraseResponce(string):

    founds = re.findall(PATTERN_PROMPT, string.strip())
    if not founds:
        # string doesn't look to be prompt
        return (NONE_MODE, None)

    mode = EXEC_MODE
    name = founds[0]

    return (mode, name)

def strPrefixRem(string, prefix):
    if not prefix:
        return string

    start = string.find(prefix)
    if start != 0:
        return string

    end = len(prefix)
    for c in string[len(prefix):]:
        if c.isprintable():
            break
        end += 1
    return string[end:]

PATTERN_MORE = re.compile(r'.*--More--\s*$')

class LinuxCli:

    def __init__(self, ipAddress, user, password, name=None):
        self.ipAddress = ipAddress
        self.user = user
        self.password = password
        self.mode = NONE_MODE
        self.name = name

        self.resp = None

        self.input_size = 10000
        self.wait_count = 20
        self.wait_time  = 1

    def startSSH(self):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            trace(f"Connecting {self.ipAddress}...")
            self.client.connect(hostname=self.ipAddress, username=self.user, password=self.password, look_for_keys=False, allow_agent=False)

            trace("Start shell..")
            self.channel = self.client.invoke_shell(width=80, height=100)

            self.waitPrompt()
        except Exception as e:
            logger.error(f"Exception {type(e)}: {e}")
            return False
        return True

    def end(self):
        self.channel.close()
        self.client.close()

    def checkReady(self):

        repeat = self.wait_count
        while repeat != 0 and not self.channel.recv_ready():
            trace(f"checkReady WAIT ... {repeat}")
            time.sleep(self.wait_time)
            repeat -= 1

        return self.channel.recv_ready()

    def binaryToAscii(self, binary):
        ascii = binary.decode("ascii")
        pattern = re.compile(r'\x1b\[[0-9?]+[m|K|h]')
        #re.compile(r'\x1b\[\d+m')
        return pattern.sub('', ascii)        

    def waitInput(self, prefix=None, clean=False):
        
        # if we have data in buffer from previous input return it
        if not clean and self.resp:
            tmp = self.resp
            self.resp = ""
            return tmp

        self.resp = ""
        echo = True
        # buffer is empty
        #try:

        while  self.checkReady():
            trace("waitInput IS READY - READ")
            resp = self.binaryToAscii(self.channel.recv(self.input_size))

            # remove the command from the input buffer
            if echo:
                echo = False
                resp = strPrefixRem(resp, prefix)

            self.resp += resp

            # send backspace if --More-- prompt is faced
            if PATTERN_MORE.search(resp):
                trace("waitInput MORE FOUND")
                self.channel.send(" ")

            # it looks to be cli prompt - done
            name = self.name if self.name else ""
            cli_prompt = fr'{name}#\s$'
            if re.search(cli_prompt, resp):
                break

        self.mode, name = paraseResponce(self.resp)
        if not self.name and self.mode in MODES and name:
            self.name = name.strip()
            trace(f"SET NAME {self.name}")

        trace(f"waitInput SUCCESS {len(self.resp)} bytes")
        device_log(self.resp)
        return self.resp

        # except Exception as e:
        #     print(f"Exception write {type(e)} {e}")    # the exception instance

    def waitPrompt(self):

        for repeat in range(self.wait_count):

            resp = self.waitInput(clean=True)

            if self.mode in MODES:
                trace(f"waitPrompt: MODE: {self.mode}")
                return
            
            trace(f"waitPrompt: UNEXPECTED MODE: {self.mode}")
            trace(f"SEND <cr>")

            self.channel.send('\n')


    def writeWithResponce(self, command, expect=None):
        """ writeWithResponce(command, expect)  sent command and wait expected respoce """

        # try:

        trace(f"writeWithResponce SENT '{command}'")
        self.channel.send(command + "\n")
        device_log(command + "\n")

        self.resp = None
        self.waitInput(prefix=command)

        # if not expect:
        #     self.waitPrompt()

        # except Exception as e:
        #     print(f"Exception  write {type(e)}) {e}") # the exception instance

    def toConfig(self):

        while self.mode != CONFIG_MODE:
            if self.mode == CONFIG_DEEP_MODE :
                self.writeWithResponce("exit")
            elif self.mode == EXEC_MODE:
                self.writeWithResponce("config")
            elif self.mode == NONE_MODE:
                self.waitPrompt()

    def toExec(self):

        while self.mode != EXEC_MODE:
            if self.mode in [CONFIG_MODE, CONFIG_DEEP_MODE]:
                self.writeWithResponce("exit")
            elif self.mode == NONE_MODE:
                self.waitPrompt()

    def doesOutputContain(self, substr):
        return self.resp.find(substr) >= 0
