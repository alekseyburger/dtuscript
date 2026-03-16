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
NON_PHYSICAL_IFACES = ["loopback", "bdi"]
class CiscoInterface(BaseConfig):
    '''
    CiscoInterface object contains desired configuration for the interface.
    However, the object is created not attached to the interface. Changing the 
    attributes of an non-attached object does not cause changes in the router 
    configuration until the .attach or .create methods are called. The .create 
    method creates an interface with the default configuration on the router. 
    The .attach method makes the object connected to the interface, but does not 
    change the interface configuration. After calling these methods, it is possible 
    to change the interface configuration using the .modify method or delete/clear 
    the interface using the .delete method.
    '''

    attr_list = ("vrf",
                 "ipv4_address_mask",
                 "ipv6_address_mask",
                 "description",
                 "mpls",
                "vlanId")


    def __init__ (self, name):
        BaseConfig.__init__(self, None, name.lower())

        self.is_subinterface = (1 == len(re.findall(r"([a-zA-Z\-]+)([0-9\/]+)\.(\d+)",self.name)))
        self.is_loopback = (1 == len(re.findall(r"(loopback)\d+",self.name)))
        # Set is_non_physical if interface name matches any in NON_PHYSICAL_IFACES
        self.is_non_physical = any(self.name.startswith(prefix) for prefix in NON_PHYSICAL_IFACES)

    @property
    def ipv4_address (self):
        '''
        This method returns the IP address assigned to interface
        '''
        if not hasattr(self, "ipv4_address_mask") or self.ipv4_address_mask is None:
            return None
        match = re.findall(r'(\d+.\d+.\d+.\d+)\/\d+',self.ipv4_address_mask)
        if len(match) != 1:
            return None
        return match[0]
    
    @property
    def ipv4_mask (self):
        '''
        This method returns the IP network mask assigned to interface 
        '''
        if not hasattr(self, "ipv4_address_mask") or self.ipv4_address_mask is None:
            return None
        match = re.findall(r'\d+.\d+.\d+.\d+\/(\d+)',self.ipv4_address_mask)
        if len(match) != 1:
            return None
        return utils_ipv4.mask_len_to_4digit(int(match[0]))

    def __repr__(self):
        if self.router:
            ret = f"{self.router.name} "
        else:
            ret = f"noname "
        ret =  ret + f"interface {self.name}"
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

    def __set_feature__(self, feature, value):
        if feature not in self.attr_list:
            error(f" Unexpected cfg feature {feature}")
            return
        setattr(self, feature, value) 

    def __apply_feature__(self, feature, value):
        """
        This method applies the configuration feature to the interface. It is expected that the
        object is attached to an interface.  The method should be called for each feature that 
        is being applied to the interface. It is expected that the method is called in the 
        context of interface configuration mode. The method should not change the configuration 
        of the interface if the value of the feature is None. The method should apply the default 
        configuration if the value of the feature is False or empty string.
        """
        if feature == "vrf":
            # remove ip addresses before move to vrf
            self.router.enterWithResponce(f"no ip address",PROMPT_CFG)
            self.router.enterWithResponce(f"no ipv6 address",PROMPT_CFG)
            #  move to vrf
            vrf_name = get_vrf_name(value)
            if vrf_name and len(vrf_name):
                self.router.enterWithResponce(f"ip vrf forwarding {vrf_name}",PROMPT_CFG)
            else:
                self.router.enterWithResponce(f"no ip vrf forwarding",PROMPT_CFG)
            # restore ip addresses
            if hasattr(self, "ipv4_address_mask") and not self.ipv4_address_mask is None:
                self.router.enterWithResponce(f"ip address  {self.ipv4_address} {self.ipv4_mask}",
                    PROMPT_CFG)
            if hasattr(self, "ipv6_address_mask") and not self.ipv6_address_mask is None:
                self.router.enterWithResponce(f"ipv6 address {self.ipv6_address_mask}",PROMPT_CFG)       
            self.vrf = value

        elif feature == "ipv4_address_mask":
            self.ipv4_address_mask = value
            if value:
                self.router.enterWithResponce(f"ip address  {self.ipv4_address} {self.ipv4_mask}",
                    PROMPT_CFG)
            else:
                self.router.enterWithResponce(f"no ip address",PROMPT_CFG)
            
        elif feature == "ipv6_address_mask":
            self.ipv6_address_mask = value
            if value:
                self.router.enterWithResponce('ipv6 enable',PROMPT_CFG)
                self.router.enterWithResponce(f"ipv6 address {self.ipv6_address_mask}",PROMPT_CFG)
            else:
                self.router.enterWithResponce(f"no ipv6 address",PROMPT_CFG)
                self.router.enterWithResponce('no ipv6 enable',PROMPT_CFG)
        elif feature == "description":
            self.description = value
            if value:
                self.router.enterWithResponce(f'description "{self.description}"',PROMPT_CFG)
            else:
                self.router.enterWithResponce(f'no description',PROMPT_CFG)
        elif feature == "mpls":
            self.mpls = value
            if not self.is_non_physical:
                if self.mpls:
                    self.router.enterWithResponce(f"mpls ip",PROMPT_CFG)
                else:
                    self.router.enterWithResponce(f"no mpls ip",PROMPT_CFG)
        elif feature == "vlanId":
            self.vlanId = value
            if not self.is_non_physical:
                if self.vlanId:
                    self.router.enterWithResponce(f"vlan-id dot1q {self.vlanId}",PROMPT_CFG)
        else:
            error(f" Unexpected cfg feature {feature}")

    def __apply_features__ (self):
        for feature in self.attr_list:
            if hasattr(self, feature):
                self.__apply_feature__(feature, getattr(self, feature))

    def attach (self, router):
        '''
        If interface is exist, then attach the Object to router interface and returns True.
        Otherwise retunts False.  After calling these methods, it is possible 
        to change the interface configuration using the .modify method or delete/clear 
        the interface using the .delete method.
        '''
        int_list = cisco_get_all_interfaces(router)
        if self.name not in int_list:
            return False
        self.router = router
        return True

    
    def create (self, router):
        '''
        Create interface with default configuration. After calling these methods, 
        it is possible     to change the interface configuration using the .modify 
        method or delete/clear the interface using the .delete method.
        '''
        int_list = cisco_get_all_interfaces(router)
        self.router = router
        # clean interface configuration
        self.router.toConfig()
        if not self.is_subinterface and not self.is_non_physical:
            self.router.enterWithResponce(f"default interface {self.name}",'(config)#')
        elif self.name in int_list:
            self.router.enterWithResponce(f"no interface {self.name}",'(config)#')
        # recreate interface and applay configured features
        self.router.enterWithResponce(f"interface {self.name}",PROMPT_CFG)
        self.__apply_features__()
        info(f" {self} created")
        return True

    def modify (self, **kwargs):
        '''
        This method has different effects for attached and unattached objects. 
        If the object is not attached to an interface, the .modify method simply 
        stores the desired configuration attributes in the object. This 
        configuration will be applied to the interface when the .create 
        method is called. If the object is attached to an interface, then 
        calling the method affects the interface configuration immediately.
        '''

        if self.router:
            # Apply configuration immediately if the object is attached to an interface
            self.router.toConfig()
            self.router.enterWithResponce(f"interface {self.name}",PROMPT_CFG)
            for feature, value in kwargs.items():
                self.__apply_feature__(feature, value)
        else:
            # Just store the desired configuration in the object if it is not attached to an interface
            for feature, value in kwargs.items():
                self.__set_feature__(feature, value)
        info(f" {self} modified")


    def delete (self, router=None):
        '''
        This method removes the interface from the configuration if it is a 
        loopback or subinterface. It applies the default configuration to 
        the physical interface.
        '''
        if router:
            self.router = router

        self.router.toConfig()
        if self.is_subinterface or self.is_non_physical:
            self.router.enterWithResponce(f"no interface {self.name}", '(config)#')
        else:
            self.router.enterWithResponce(f"default interface {self.name}", '(config)#')

        info(f" {self} deleted")
        self.router = None

    def up (self):
        '''
        This method apply up state to interface. It is expected that object
        is attached to interface
        '''
        self.router.toConfig()
        self.router.enterWithResponce(f"interface {self.name}",PROMPT_CFG)
        self.router.enterWithResponce(f"no shutdown",PROMPT_CFG)      

        info(f" {self} up")

    def down (self):
        '''
        This method apply down state to interface. It is expected that object
        is attached to interface
        '''
        self.router.toConfig()
        self.router.enterWithResponce(f"interface {self.name}",PROMPT_CFG)
        self.router.enterWithResponce(f"shutdown",PROMPT_CFG)      

        info(f" {self} down")


def cisco_get_all_interfaces (router):
    '''
    Returns the list of existing interfaces (from 'show ip interface brief')
    '''
    router.enterExecCommand('show ip interface brief')
    int_list = []

    #remove show header
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


def cisco_get_all_interfaces_params (router):
    """
    Requests and parses the output of 'show ip interface brief' from a RouterCisco object.
    :param router: RouterCisco instance
    :return: List of dicts with keys: Interface, IP-Address, Status
    """
    router.enterExecCommand("show ip interface brief")
    lines = router.resp.splitlines()
    if not lines:
        return []
    result = []
    parsing = False
    for line in lines:
        if not parsing:
            if line.strip().startswith('Interface'):
                parsing = True
            continue
        # Now parsing data lines, skip the header itself
        if '#' in line:
            break
        fields = re.split(r'\s{1,}', line.strip())
        if len(fields) == 6:
            iface = {
                'Interface': fields[0].lower(),
                'IP': fields[1],
                'Status': fields[4],
            }
            result.append(iface)
    return result