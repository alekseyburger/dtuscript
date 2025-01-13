# GNU GENERAL PUBLIC LICENSE
# Autor: Aleksey Burger

import re
from base_config import base_config
from dtu_definition import BGP_AFAMILY_IPV4_UNICAST,BGP_AFAMILY_IPV6_UNICAST,BGP_AFAMILY_L2_EVPN, BGP_AFAMILY_IPV4_VPN
from cisco_interface import  CiscoInterface
from cisco_vrf import  CiscoVrf
from exception_dev import exception_dev
import logging

logger = logging.getLogger("dtulibLog")

def trace(format):
    logger.debug(f'\n\x1b[1;94mCiscoBgp: {format}\x1b[0m')

def error(format):
    logger.error(f'\n\x1b[1;31mCiscoBgp: {format}\x1b[0m')

def info(format):
    logger.info(f'\n\x1b[1;92mCiscoBgp: {format}\x1b[0m')

def warn(format):
    logger.warning(f'\n\x1b[1;94mCiscoBgp: {format}\x1b[0m')

device_logger = logging.getLogger("deviceLog")
def device_log(format):
    device_logger.info(f'{format}')

def _cisco_bgp_get_af_command (name):
    if name == BGP_AFAMILY_IPV4_UNICAST:
        return 'address-family ipv4 unicast'
    elif name == BGP_AFAMILY_IPV6_UNICAST:
        return 'address-family ipv6 unicast'
    else:
        raise Exception("cisco bgp af is not implemented ")

def str_normalize (str):
    str = ' '.join(str.split())
    return str.lower()

class CiscoBgpNeighborAFamily(base_config):
    def __init__ (self, af_type, **kwargs):

        base_config.__init__(self, None, af_type)

        self.neighbor_list = set()
        self.feature_set = set()
        for feature in kwargs.keys():
            self._feature_set_modify(feature)

    def _feature_set_modify (self, str):
        ''' 
        parse string with purpose to ​recognize 'no' command
        modify self.feature_set with feture
        returns two results:
            True if it is 'no' command, otherwise False
            Normalized command string
        '''
        match = re.findall(r'(no\s+)?(.+)',str)
        if not match or len(match[0]) != 2:
            # parsing error
            return None, None
        is_no = len(match[0][0]) != 0
        nstr = str_normalize(match[0][1])
        if is_no:
            self.feature_set.remove(nstr)
        else:
            self.feature_set.add(nstr)
        return is_no, nstr

    def __repr__(self):
        ret = f"CiscoBgpNeighborAFamily {self.name}"
        return ret

    def create (self):
        pass

    def __apply__ (self, upref):

        is_first_call = self.router == None
        self.upref = upref
        self.router = upref.router   
     
        self.router.writeWithResponce(_cisco_bgp_get_af_command(self.name) , '(config-router-af)#')
        
        if  upref not in self.neighbor_list:
            self.router.writeWithResponce(f'neighbor {upref.name} activate' , '(config-router-af)#')
            self.neighbor_list.add(upref)
        
        if is_first_call:
            for feature in self.feature_set:
                self.router.writeWithResponce(f'neighbor {upref.name} {feature}', '(config-router-af)#')

        self.router.writeWithResponce('exit-address-family' , '(config-router)#')

    def __detach__ (self):
        self.upref = None
        self.router = None
        self.neighbor_list = set()
        self.feature_set = set()

    def add_feature (self, feature_str): 
        self._feature_set_modify(feature_str)

    def modify_feature (self, str):
        is_no, feature_str = self._feature_set_modify(str)
        if feature_str and self.router:
            prefix = 'no ' if is_no else ''
            self.router.toConfig()
            self.router.writeWithResponce(f"router bgp {self.get_router_name()}", '(config-router)#')
            self.router.writeWithResponce(_cisco_bgp_get_af_command(self.name) , '(config-router-af)#')
            self.router.writeWithResponce(f'{prefix}neighbor {self.upref.name} {feature_str}', '(config-router-af)#')
            self.router.writeWithResponce('exit-address-family' , '(config-router)#')

    def get_router_name (self):
        if not self.router:
            return None
        return self.upref.upref.upref.name

class CiscoBgpNeighbor(base_config):
    def __init__ (self, name, as_number, **kwargs):

        base_config.__init__(self, None, name)

        self.as_number = str(as_number)

        for feature in kwargs.keys():

            if feature == "local_address":
                local_address = kwargs[feature]
                if isinstance(local_address, CiscoInterface):
                    self.local_address = local_address.name
                elif isinstance(local_address, str):
                    self.local_address = local_address
                else:
                    Exception("CiscoBgp: unexpected interface name")

        self.af_list = []

    def __repr__(self):
        ret = f"CiscoBgpNeighbor {self.name} AS {self.as_number}"
        return ret

    def create (self):
        pass

    def add_afamily (self, *afamily):
        for af in afamily:
            if self.router:
                self.router.toConfig()
                self.router.writeWithResponce(f"router bgp {self.upref.upref.name}", '(config-router)#')
                af.__apply__(self)
                self.router.toConfig()
            self.af_list.append(af)

    def __apply__ (self, upref):
        self.upref = upref
        self.router = upref.router

        self.router.writeWithResponce(f"neighbor {self.name} remote-as {self.as_number}", '#')

        if hasattr(self, "local_address") and self.local_address:
            self.router.writeWithResponce(f"neighbor {self.name} update-source {self.local_address}", '#')

        for af in self.af_list:
            af.__apply__(self)

    def __detach__ (self):

        for af in self.af_list:
            af.__detach__()

        self.router.writeWithResponce(f"no neighbor {self.name}", '#')
        self.upref = None
        self.router = None

    def get_router_name (self):
        if not self.router:
            return None
        return self.upref.upref.name

class CiscoBgpAFamily(base_config):
    def __init__ (self, af_type, **kwargs):
        base_config.__init__(self, None, af_type)
        self.feature_set = set()
        for feature in kwargs.keys():
            self._feature_set_modify(feature)
        
    def __repr__(self):
        ret = f"CiscoBgpAFamily {self.name}"
        return ret

    def _feature_set_modify (self, str):
        ''' 
        parse string with purpose to ​recognize 'no' command
        modify self.feature_set with feture
        returns two results:
            True if it is 'no' command, otherwise False
            Normalized command string
        '''
        match = re.findall(r'(no\s+)?(.+)',str)
        if not match or len(match[0]) != 2:
            # parsing error
            return None, None
        is_no = len(match[0][0]) != 0
        nstr = str_normalize(match[0][1])
        if is_no:
            self.feature_set.remove(nstr)
        else:
            self.feature_set.add(nstr)
        return is_no, nstr

    def create (self):
        pass

    def __apply__ (self, upref):
        self.upref = upref  # Parent BgpVrf
        self.router = upref.router

        self.router.writeWithResponce(_cisco_bgp_get_af_command(self.name), "#")
        # set import/export targets
        if self.upref.upvrf and self.upref.upvrf.router:
            # Get Vrf from BgpVrf, then iterate on vrf af and get import/export targets
            for af in self.upref.upvrf.af_list:
                if self.name == af.name:
                    for itarget in af.import_list:
                        self.router.writeWithResponce(f'import-rt {itarget}')
                    for etarget in af.export_list:
                        self.router.writeWithResponce(f'export-rt {etarget}')
        # set features
        for feature in self.feature_set:
            self.router.writeWithResponce(feature, "#")

        self.router.writeWithResponce("exit-address-family", "(config-router)#")

    def __detach__ (self):
        self.upref = None
        self.router = None

    def add_feature (self, feature_str):
        self._feature_set_modify(feature_str)

    def modify_feature (self, str):
        is_no, feature_str = self._feature_set_modify(str)
        if feature_str and self.router:
            prefix = 'no ' if is_no else ''
            self.router.toConfig()
            self.router.writeWithResponce(f"router bgp {self.get_router_name()}", '(config-router)#')
            self.router.writeWithResponce(_cisco_bgp_get_af_command(self.name) , '(config-router-af)#')
            self.router.writeWithResponce(f'{prefix} {feature_str}', '(config-router-af)#')
            self.router.writeWithResponce('exit-address-family' , '(config-router)#')

    def get_router_name (self):
        if not self.router:
            return None
        return self.upref.upref.name

class CiscoBgpVrf(base_config):
    def __init__ (self, vrf, **kwargs):

        if isinstance(vrf, CiscoVrf):
            name = vrf.name
            self.upvrf = vrf
        elif isinstance(vrf,str):
            name = vrf
            self.upvrf = None
        else:
            Exception("CiscoBgp: unexpected vrf name")
        base_config.__init__(self, None, name)

        self.af_list = []
        self.neighbor_list = []

    def __repr__(self):
        ret = f"CiscoBgpVrf {self.name}"
        return ret

    def create (self):
        pass

    def __apply__ (self, upref):
        self.upref = upref
        self.router = upref.router

        for neighbor in self.neighbor_list:
            neighbor.__apply__(self)  
        for af in self.af_list:
            af.__apply__(self)
             
        # self.router.writeWithResponce("exit")

    def __detach__ (self):

        for af in self.af_list:
            af.__detach__()
        for neighbor in self.neighbor_list:
            neighbor.__detach__()

        self.upref = None
        self.router = None           

    def add_afamily (self, *afamilies):
        for af in afamilies:
            if (self.router):
                self.router.toConfig()
                self.router.writeWithResponce(f"router bgp {self.upref.name}", '(config-router)#')
                af.__apply__(self)
                self.router.toConfig()
            self.af_list.append(af)

    def add_neighbor (self, *neighbors):
        for neighbor in neighbors:
            if (self.router):
                self.router.toConfig()
                self.router.writeWithResponce(f"router bgp {self.upref.name}", '(config-router)#')
                neighbor.__apply__(self)
                self.router.toConfig()

            self.neighbor_list.append(neighbor)    

class CiscoBgp(base_config):
    def __init__ (self, name, **kwargs):
        base_config.__init__(self, None, str(name))
        self.vrf_list = []

    def __repr__(self):
        ret = f"CiscoBgp {self.name}"
        return ret

    def add_vrf (self, bgp_vrf):
        if (self.router):
            self.router.toConfig()
            self.router.writeWithResponce(f"router bgp {self.name}", '(config-router)#')
            bgp_vrf.__apply__(self)
            self.router.toConfig()
        self.vrf_list.append(bgp_vrf)
    
    def create (self, router):
        self.router = router

        self.router.toConfig()
        self.router.writeWithResponce(f"router bgp {self.name}", '(config-router)#')

        for vrf in self.vrf_list:
            vrf.__apply__(self)

        self.router.toConfig()

        info(f"router bgp {self.name} created")

    def delete (self, router=None):
        if router:
            self.router = router
        self.router.toConfig()
        self.router.writeWithResponce(f"router bgp {self.name}", '(config-router)#')
        for vrf in self.vrf_list:
            vrf.__detach__()

        self.router.writeWithResponce(f"no router bgp {self.name}", '(config)#')

        self.router.toConfig()
        self.router = None

        info(f"router bgp {self.name} deleted")

def cisco_get_all_bgp (router):
    bgp_list = []
    router.toExec()
    try:
        router.writeWithResponce('show ip bgp summary')
    except exception_dev:
        # bgp is not active
        return bgp_list
    

    match = re.findall(r'local AS number\s+(\d+)', router.resp, re.MULTILINE)
    if match and len(match):
        if int(match[0]):
            bgp_list.append(match[0])

    return bgp_list