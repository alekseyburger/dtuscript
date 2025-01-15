# GNU GENERAL PUBLIC LICENSE
# Autor: Aleksey Burger

from router_cisco import RouterCisco
import logging
import re
from base_config import BaseConfig
from exception_dev import ExceptionDevice
import utils_ipv4
from cisco_vrf import CiscoVrf


logger = logging.getLogger("dtulibLog")
def trace(format):
    logger.debug(f'\n\x1b[1;32mCiscoInterface: {format}\x1b[0m')

def error(format):
    logger.error(f'\n\x1b[1;31mCiscoInterface: {format}\x1b[0m')

def info(format):
    logger.info(f'\n\x1b[1;92mCiscoInterface: {format}\x1b[0m')

def get_vrf_name (vrf_or_name):
    if isinstance(vrf_or_name, CiscoVrf):
        return vrf_or_name.name
    return vrf_or_name

PROMPT_CFG = '(config-if)#'
class CiscoInterface(BaseConfig):
    def __init__ (self, name):
        BaseConfig.__init__(self, None, name.lower())

        self.is_subinterface = (1 == len(re.findall(r"([a-zA-Z\-]+)([0-9\/]+)\.(\d+)",self.name)))
        self.is_loopback = (1 == len(re.findall(r"(loopback)\d+",self.name)))
        # self.__args_parse__(**kwargs)

    # def __args_parse__(self, **kwargs):
    #     for feature in kwargs.keys():
    #         if feature == "vrf":
    #             self.vrf = kwargs[feature]
    #         elif feature == "ipv4_address_mask":
    #             self.ipv4_address_mask = kwargs[feature]
    #         elif feature == "ipv6_address_mask":
    #             self.ipv6_address_mask = kwargs[feature]
    #         elif feature == "description":
    #             self.description = kwargs[feature]
    #         elif feature == "mpls":
    #             self.mpls = kwargs[feature]
    #         elif feature == "vlanId":
    #             self.vlanId = kwargs[feature]
    #         else:
    #             error(f" Unexpected cfg feature {feature}")

    @property
    def ipv4_address (self):
        if not hasattr(self, "ipv4_address_mask") or self.ipv4_address_mask is None:
            return None
        match = re.findall(r'(\d+.\d+.\d+.\d+)\/\d+',self.ipv4_address_mask)
        if len(match) != 1:
            return None
        return match[0]
    
    @property
    def ipv4_mask (self):
        if not hasattr(self, "ipv4_address_mask") or self.ipv4_address_mask is None:
            return None
        match = re.findall(r'\d+.\d+.\d+.\d+\/(\d+)',self.ipv4_address_mask)
        if len(match) != 1:
            return None
        return utils_ipv4.mask_len_to_4digit(int(match[0]))

    def __repr__(self):
        ret = f"interface {self.name}"
        if hasattr(self, "vrf") and not self.vrf is None:
            ret = ret + f" {self.vrf.name}"
        if hasattr(self, "ipv4_address_mask") and not self.ipv4_address_mask is None:
            ret = ret + f" {self.ipv4_address_mask}"
        if hasattr(self, "ipv6_address_mask") and not self.ipv6_address_mask is None:
            ret = ret + f" {self.ipv6_address_mask}"
        if self.is_subinterface:
            ret = ret + " (subInt) "
        if  self.is_loopback:
            ret = ret + " (LoopBack) "
        return ret

    # def __apply__ (self):
    #     if hasattr(self, "vrf") and not self.vrf is None:
    #         vrf_name = get_vrf_name(self.vrf)
    #         if vrf_name and len(vrf_name):
    #             self.router.writeWithResponce(f"ip vrf forwarding {vrf_name}",PROMPT_CFG)

    #     if hasattr(self, "ipv4_address_mask") and not self.ipv4_address_mask is None:
    #         self.router.writeWithResponce(f"ip address  {self.ipv4_address} {self.ipv4_mask}",
    #             PROMPT_CFG)
    #     else:
    #         self.router.writeWithResponce(f"no ip address",PROMPT_CFG)
    #     if hasattr(self, "ipv6_address_mask") and not self.ipv6_address_mask is None:
    #         self.router.writeWithResponce('ipv6 enable',PROMPT_CFG)
    #         self.router.writeWithResponce(f"ipv6 address {self.ipv6_address_mask}",PROMPT_CFG)
    #     else:
    #         self.router.writeWithResponce(f"no ipv6 address",PROMPT_CFG)
    #         self.router.writeWithResponce('no ipv6 enable',PROMPT_CFG)
    #     if hasattr(self, "description"):
    #         self.router.writeWithResponce(f'description "{self.description}"',PROMPT_CFG)
    #     if not self.is_loopback:
    #         if hasattr(self, "mpls") and self.mpls:
    #             self.router.writeWithResponce(f"mpls ip",PROMPT_CFG)
    #         else:
    #             self.router.writeWithResponce(f"no mpls ip",PROMPT_CFG)
    #     if not self.is_loopback:
    #         if hasattr(self, "vlanId") and self.vlanId:
    #             self.router.writeWithResponce(f"vlan-id dot1q {self.vlanId}",PROMPT_CFG)
    #         # else:
    #         #     self.router.writeWithResponce(f"no vlan-id dot1q",PROMPT_CFG)

    def __apply_feature__(self, feature, value):
        if feature == "vrf":
            # remove ip addresses before move to vrf
            self.router.writeWithResponce(f"no ip address",PROMPT_CFG)
            self.router.writeWithResponce(f"no ipv6 address",PROMPT_CFG)
            #  move to vrf
            vrf_name = get_vrf_name(value)
            if vrf_name and len(vrf_name):
                self.router.writeWithResponce(f"ip vrf forwarding {vrf_name}",PROMPT_CFG)
            else:
                self.router.writeWithResponce(f"no ip vrf forwarding",PROMPT_CFG)
            # restore ip addresses
            if hasattr(self, "ipv4_address_mask") and not self.ipv4_address_mask is None:
                self.router.writeWithResponce(f"ip address  {self.ipv4_address} {self.ipv4_mask}",
                    PROMPT_CFG)
            if hasattr(self, "ipv6_address_mask") and not self.ipv6_address_mask is None:
                self.router.writeWithResponce(f"ipv6 address {self.ipv6_address_mask}",PROMPT_CFG)       
            self.vrf = value

        elif feature == "ipv4_address_mask":
            self.ipv4_address_mask = value
            if value:
                self.router.writeWithResponce(f"ip address  {self.ipv4_address} {self.ipv4_mask}",
                    PROMPT_CFG)
            else:
                self.router.writeWithResponce(f"no ip address",PROMPT_CFG)
            
        elif feature == "ipv6_address_mask":
            self.ipv6_address_mask = value
            if value:
                self.router.writeWithResponce('ipv6 enable',PROMPT_CFG)
                self.router.writeWithResponce(f"ipv6 address {self.ipv6_address_mask}",PROMPT_CFG)
            else:
                self.router.writeWithResponce(f"no ipv6 address",PROMPT_CFG)
                self.router.writeWithResponce('no ipv6 enable',PROMPT_CFG)
        elif feature == "description":
            self.description = value
            if value:
                self.router.writeWithResponce(f'description "{self.description}"',PROMPT_CFG)
            else:
                self.router.writeWithResponce(f'no description',PROMPT_CFG)
        elif feature == "mpls":
            self.mpls = value
            if not self.is_loopback:
                if self.mpls:
                    self.router.writeWithResponce(f"mpls ip",PROMPT_CFG)
                else:
                    self.router.writeWithResponce(f"no mpls ip",PROMPT_CFG)
        elif feature == "vlanId":
            self.vlanId = value
            if not self.is_loopback:
                if self.vlanId:
                    self.router.writeWithResponce(f"vlan-id dot1q {self.vlanId}",PROMPT_CFG)
        else:
            error(f" Unexpected cfg feature {feature}")

    def attach (self, router):
        router.toExec()
        int_list = cisco_get_all_interfaces(router)
        if self.name not in int_list:
            return False
        self.router = router        
        return True

    
    def create (self, router):
        self.router = router

        self.router.toConfig()
        if not self.is_subinterface and not self.is_loopback:
            self.router.writeWithResponce(f"default interface {self.name}",'(config)#')
        self.router.writeWithResponce(f"interface {self.name}",PROMPT_CFG)
        # self.__apply__()
        info(f" {self} created")
        return True

    def modify (self, router=None, **kwargs):
        if not self.router and router:
            self.router = router

        if self.router:
            self.router.toConfig()
            self.router.writeWithResponce(f"interface {self.name}",PROMPT_CFG)
            for feature, value in kwargs.items():
                self.__apply_feature__(feature, value)
        info(f" {self} modified")

    def delete (self, router=None):
        if router:
            self.router = router

        self.router.toConfig()
        if self.is_subinterface or self.is_loopback:
            self.router.writeWithResponce(f"no interface {self.name}", '(config)#')
        else:
            self.router.writeWithResponce(f"default interface {self.name}", '(config)#')

        info(f" {self} deleted")
        self.router = None

    def up (self):
        self.router.toConfig()

        self.router.writeWithResponce(f"interface {self.name}",PROMPT_CFG)
        self.router.writeWithResponce(f"no shutdown",PROMPT_CFG)      

        info(f" {self} up")

    def down (self):
        self.router.toConfig()

        self.router.writeWithResponce(f"interface {self.name}",PROMPT_CFG)
        self.router.writeWithResponce(f"shutdown",PROMPT_CFG)      

        info(f" {self} down")


def cisco_get_all_interfaces (router):
    router.toExec()
    router.writeWithResponce('show ip interface brief')
    int_list = []

    #remove show header
    # delimiter_pos = re.search(r'Interface\s+IP-Address.+(Protocol$)', router.resp, re.MULTILINE)
    delimiter_pos = re.search(r'Interface\s+IP-Address.+(Protocol\r\n)', router.resp, re.MULTILINE)
    if not delimiter_pos:
        return int_list
    body = router.resp[delimiter_pos.span()[1]:]
    # remove prompt after the table
    table_end_pos = re.search(f'^{router.name}#', body, re.MULTILINE)
    if table_end_pos:
        body = body[:table_end_pos.span()[0]]

    for line in body.split('\r\n'):
        match = re.findall(r'(\w+)', line)
        if match and len(match):
            int_list.append(match[0].lower())
    return int_list