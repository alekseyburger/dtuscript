# GNU GENERAL PUBLIC LICENSE
# Autor: Aleksey Burger

import logging
from base_config import BaseConfig
from router_cisco import RouterCisco
from cisco_interface import  CiscoInterface
from dtu_definition import OSPF_INTF_NTYPE_P2P,OSPF_INTF_NTYPE_P2M, OSPF_INTF_NTYPE_BCAST, OSPF_INTF_NTYPE_NBCAST, OSPF_INTF_NTYPE_P2M_NBCAST
from exception_dev import ExceptionDevice

logger = logging.getLogger("dtulibLog")

def trace(format):
    logger.debug(f'\n\x1b[1;94mCiscoOspf: {format}\x1b[0m')

def error(format):
    logger.error(f'\n\x1b[1;31mCiscoOspf: {format}\x1b[0m')

def info(format):
    logger.info(f'\n\x1b[1;92mCiscoOspf: {format}\x1b[0m')

def warn(format):
    logger.warning(f'\n\x1b[1;94mExa: {format}\x1b[0m')



def __network_type_command__ (ntype):
    if ntype == OSPF_INTF_NTYPE_P2P:
        return 'point-to-point'
    else:
        raise Exception(f'CiscoOspf: unexpectd network type {ntype}')

class CiscoOspfInterface(BaseConfig):
    def __init__ (self, interface, **kwargs):
        if isinstance(interface, CiscoInterface):
            name = interface.name
        elif isinstance(interface,str):
            name = interface
        else:
            Exception("CiscoOspf: unexpected interface name")

        BaseConfig.__init__(self, None, name)

        self.network_type = OSPF_INTF_NTYPE_P2P
        for feature in kwargs.keys():

            if feature == "network_type":
                self.network_type = kwargs[feature]
            # elif feature == "metric":
            #     self.metric = kwargs[feature]            
            # elif feature == "mtu":
            #     self.mtu = kwargs[feature]
            elif feature == "passive":
                self.passive = kwargs[feature]
            else:
                raise Exception(f'CiscoOspfInterface: unexpectd feature {feature}')

    def __repr__(self):
        ret = f"CiscoOspfInterface {self.name}"
        if hasattr(self, "network_type"):
            ret = ret + f" {self.network_type}"
        return ret

    def create (self):
        pass

    def __apply__ (self, upref):
        self.upref = upref
        self.router = upref.router

        self.router.toConfig
        self.router.writeWithResponce(f"interface {self.name}", '(config-if)#')
        self.router.writeWithResponce(f'ip ospf {self.upref.upref.name} area {self.upref.name}', '(config-if)#')
        # if hasattr(self, "mtu") and self.mtu:
        #     self.router.writeWithResponce(f"mtu {self.mtu}", '#')
        # else:
        #     self.router.writeWithResponce(f"no mtu", '#')
        # if hasattr(self, "metric") and self.metric:
        #     self.router.writeWithResponce(f"metric {self.metric}", '#')
        # else:
        #     self.router.writeWithResponce(f"no metric", '#')
        if not hasattr(self,'passive') or not self.passive:
            self.router.writeWithResponce(f"ip ospf network  {self.network_type}", '(config-if)#')
        self.router.toConfig

    def __detach__ (self):
        self.upref = None
        self.router = None

class CiscoOspfArea(BaseConfig):
    def __init__ (self, name, **kwargs):
        BaseConfig.__init__(self, None, name)

        self.vrf = 'default'
        for feature in kwargs.keys():
            # if feature == "metric":
            #     self.metric = kwargs[feature]
            # if feature == "network_type":
            #     self.network_type = kwargs[feature]
            # if feature == "mtu":
            #     self.mtu = kwargs[feature]
            # for feature in kwargs.keys():
            #     if feature == "vrf":
            #         self.vrf = kwargs[feature]
            raise Exception(f'CiscoOspfArea: unexpectd feature {feature}')
        self.intf_list = []

    def __repr__(self):
        ret = f"CiscoOspfArea {self.name}"
        return ret

    def create (self):
        pass

    def __apply__ (self, upref):
        self.upref = upref
        self.router = upref.router

        # self.router.writeWithResponce(f"area {self.name}", '#')
        for ospf_intf in self.intf_list:
            ospf_intf.__apply__(self)

    def __apply__phase2__ (self, upref):

        for ospf_intf in self.intf_list:
            if hasattr(ospf_intf,'passive') and ospf_intf.passive:
                self.router.writeWithResponce(f'passive-interface {ospf_intf.name}', '(config-router)#')

    def __detach__ (self):

        for ospf_intf in self.intf_list:
            ospf_intf.__detach__()

        self.upref = None
        self.router = None 

    def add_interface (self, *ospf_interface):
        for intf in ospf_interface:
            self.intf_list.append(intf)

class CiscoOspf(BaseConfig):
    def __init__ (self, name, **kwargs):
        BaseConfig.__init__(self, None, int(name))
        self.area_list = []

    def __repr__(self):
        ret = f"CiscoOsp {self.name}"
        return ret

    def add_area (self, ospf_area):
        self.area_list.append(ospf_area)
    
    def create (self, router):
        self.router = router

        self.router.toConfig()

        for area in self.area_list:
            area.__apply__(self)
    
        self.router.toConfig()
        self.router.writeWithResponce(f"router ospf {self.name}", '(config-router)#')
        for area in self.area_list:
            area.__apply__phase2__(self)
        self.router.toConfig()

        info(f"router ospf {self.name} created")

    def delete (self, router=None):
        if router:
            self.router = router
        self.router.toConfig()

        self.router.writeWithResponce(f"no router ospf {self.name}", '(config)#')

        for area in self.area_list:
            area.__detach__()

        self.router.toConfig()
        self.router = None

        info(f"router ospf {self.name} deleted")