# GNU GENERAL PUBLIC LICENSE
# Autor: Aleksey Burger

import logging
import re
from base_config import BaseConfig
from dtu_definition import VRF_AFAMILY_IPV4_UNICAST, VRF_AFAMILY_IPV6_UNICAST
from router_cisco import RouterCisco
from router_cisco import CONFIG_MODE
from exception_dev import ExceptionDevice

logger = logging.getLogger("dtulibLog")

def trace(format):
    logger.debug(f'\n\x1b[1;94mCisco: {format}\x1b[0m')

def error(format):
    logger.error(f'\n\x1b[1;31mCisco: {format}\x1b[0m')

def info(format):
    logger.info(f'\n\x1b[1;92mCisco: {format}\x1b[0m')

def warn(format):
    logger.warning(f'\n\x1b[1;94mCisco: {format}\x1b[0m')


class CiscoVrfAFamily(BaseConfig):
    def __init__ (self, af_type, **kwargs):
        BaseConfig.__init__(self, None, af_type)
        self.import_list = []
        self.export_list = []

    def __repr__(self):
        ret = f"CiscoVrfAFamily {self.name}"
        return ret

    def create (self):
        pass

    def __apply__ (self, upref):
        self.upref = upref
        self.router = upref.router

        if self.name == VRF_AFAMILY_IPV4_UNICAST:
            self.router.writeWithResponce(f'ip vrf {self.upref.name}', '(config-vrf)#')
        elif self.name == VRF_AFAMILY_IPV6_UNICAST:
            raise Exception('CiscoVrf: ipv6 vrf is not supported')
        else:
            raise Exception(f'CiscoVrf: Unexpected vrf type "{self.name}"')

        if hasattr(self.upref, "rd") and self.upref.rd:
            self.router.writeWithResponce(f"rd {self.upref.rd}", '(config-vrf)#')
        else:
            raise Exception('CiscoVrf: RD is mondatory!')

        for target in self.import_list:
            self.router.writeWithResponce(f'route-target import {target}' , '(config-vrf)#')
        for target in self.export_list:
            self.router.writeWithResponce(f'route-target export {target}' , '(config-vrf)#')

    def __detach__ (self):
        self.router.writeWithResponce(f'no ip vrf {self.upref.name}', '(config)#')

        self.upref = None
        self.router = None

    def add_import_target (self, *targets):
        for target in targets:
            if (self.router):
                self.router.toConfig()
                self.router.writeWithResponce(f'ip vrf {self.upref.name}', '(config-vrf)#')
                self.router.writeWithResponce(f'route-target import {target}' , '(config-vrf)#')
                self.router.toConfig()
            self.import_list.append(target)

    def add_export_target (self, *targets):
        for target in targets:
            if (self.router):
                self.router.toConfig()
                self.router.writeWithResponce(f'ip vrf {self.upref.name}', '(config-vrf)#')
                self.router.writeWithResponce(f'route-target export {target}' , '(config-vrf)#')
                self.router.toConfig()
            self.export_list.append(target)

class CiscoVrf(BaseConfig):
    def __init__ (self, name, rd, **kwargs):
        BaseConfig.__init__(self, None, name)

        self.rd = rd
        for feature in kwargs.keys():
            error(f"CiscoVrf: Unexpected cfg feature {feature}")
        
        self.af_list = []

    def __repr__(self):
        ret = f"vrf {self.name}"
        if hasattr(self, "rd") and self.rd:
            ret = ret + f" rd:{self.rd}"
        return ret

    def is_exist (self, router=None):
        if  self.router:
            router=self.router
        if not router:
            raise Exception("CiscoVrf: can't get router config - router is not defined")

        vrf_names = cisco_get_all_vrf(router)

        return self.name in vrf_names
        
    def create (self, router):
        self.router = router

        self.router.toConfig()

        for af in self.af_list:
            af.__apply__(self)

        info(f"{self} created")
        return True

    def delete (self, router=None):
        if router:
            self.router = router

        self.router.toConfig()
        try:
            if not len(self.af_list):
                self.router.writeWithResponce(f'no ip vrf {self.name}', '(config)#')
            else:
                for af in self.af_list:
                    af.__detach__()
        except ExceptionDevice:
            pass
        self.router = None
        info(f"{self} deleted")


    def add_afamily (self, *afamilies):
        for af in afamilies:
            if (self.router):
                self.router.toConfig()
                af.__apply__(self)
                self.router.toConfig()
            self.af_list.append(af)
    

def cisco_get_all_vrf (router):
    router.toExec()
    router.writeWithResponce('show vrf')
    vrf_list = []

    #remove show header
    delimiter_pos = re.search(r'Name\s+Default RD\s+Protocols\s+(Interfaces\r\n)', router.resp, re.MULTILINE)
    if not delimiter_pos:
        return vrf_list
    body = router.resp[delimiter_pos.span()[1]:]
    # remove prompt after the table
    table_end_pos = re.search(f'^{router.name}#', body, re.MULTILINE)
    if table_end_pos:
        body = body[:table_end_pos.span()[0]]

    for line in body.split('\r\n'):
        match = re.findall(r'(\w+)', line)
        if match and len(match):
            vrf_list.append(match[0])
    return vrf_list