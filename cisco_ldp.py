# GNU GENERAL PUBLIC LICENSE
# Autor: Aleksey Burger

import logging
from base_config import base_config
from router_cisco import RouterCisco
from cisco_interface import  CiscoInterface
from exception_dev import exception_dev

logger = logging.getLogger('dtulibLog')

def trace(format):
    logger.debug(f'\n\x1b[1;94mCiscoLdp: {format}\x1b[0m')

def error(format):
    logger.error(f'\n\x1b[1;31mCiscoLdp: {format}\x1b[0m')

def info(format):
    logger.info(f'\n\x1b[1;92mCiscoLdp: {format}\x1b[0m')

def warn(format):
    logger.warning(f'\n\x1b[1;94mCiscoLdp: {format}\x1b[0m')

def get_interface_name (intf_or_name):
    if isinstance(intf_or_name, CiscoInterface):
        return intf_or_name.name
    return intf_or_name

class CiscoLdpInterface(base_config):
    def __init__ (self, interface, **kwargs):
        if isinstance(interface, CiscoInterface):
            name = interface.name
        elif isinstance(interface,str):
            name = interface
        else:
            Exception('CiscoLdp: unexpected interface name')

        base_config.__init__(self, None, name)

        for feature in kwargs.keys():
            raise Exception(f'CiscoLdpInterface: {feature} is not implemented')

    def __repr__(self):
        ret = f'CiscoLdpInterface {self.name}'
        return ret

    def create (self):
        pass

    def __apply__ (self, upref):
        self.upref = upref
        self.router = upref.router

    def __detach__ (self):
        self.upref = None
        self.router = None

class CiscoLdp(base_config):
    def __init__ (self, **kwargs):
        base_config.__init__(self, None, 'default')
        self.intf_list = []
        for feature in kwargs.keys():
            if feature == 'local_address':
                self.router_id = get_interface_name(kwargs[feature])
            if feature == 'router_id':
                self.router_id = get_interface_name(kwargs[feature])       
    def __repr__(self):
        ret = f'CiscoLdp {self.name}'
        return ret
    
    def create (self, router):
        self.router = router

        self.router.toConfig()
        self.router.writeWithResponce('mpls label protocol ldp', '(config)#')
        if hasattr(self, 'router_id') and self.router_id:
            self.router.writeWithResponce(f'mpls ldp router-id {self.router_id}', '(config)#')
        self.router.toConfig()

        info(f'mpls ldp  {self.name} is created')

    def delete (self, router=None):
        if router:
            self.router = router
        self.router.toConfig()

        self.router.writeWithResponce('no mpls ldp router-id', '(config)#')

        for intf in self.intf_list:
            intf.__detach__()

        self.router.toConfig()
        self.router = None

        info(f'mpls ldp  {self.name} is deleted')

    def add_interface (self, *ldp_interface):
        for intf in ldp_interface:
            self.intf_list.append(intf)