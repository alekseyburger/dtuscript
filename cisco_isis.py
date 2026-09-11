# GNU GENERAL PUBLIC LICENSE
# Autor: Aleksey Burger

import logging
import re
from base_config import BaseConfig
from cisco_base import CiscoFeatureConfig
from cisco_interface import CiscoInterface
from dtu_definition import ISIS_AFAMILY_IPV4_UNICAST, ISIS_AFAMILY_IPV6_UNICAST
from dtu_definition import ISIS_LEVEL_1, ISIS_LEVEL_2
from dtu_definition import ISIS_INTF_NTYPE_P2P

logger = logging.getLogger("dtulibLog")

def trace(format):
    logger.debug(f'\n\x1b[1;94mCiscoISIS: {format}\x1b[0m')

def error(format):
    logger.error(f'\n\x1b[1;31mCiscoISIS: {format}\x1b[0m')

def info(format):
    logger.info(f'\n\x1b[1;92mCiscoISIS: {format}\x1b[0m')

def warn(format):
    logger.warning(f'\n\x1b[1;94mCiscoISIS: {format}\x1b[0m')

PROMPT_ROUTER = '(config-router)#'
PROMPT_ROUTER_AF = '(config-router-af)#'
PROMPT_CFG_IF = '(config-if)#'
PROMPT_CFG = '(config)#'

# NET: area id (2-4 hex) . one or more 4-hex groups (system id) . NSEL, always 00
PATTERN_NET = re.compile(r'^[0-9a-fA-F]{2,4}(\.[0-9a-fA-F]{4})+\.00$')

# is-type keyword for the set of levels in use
IS_TYPE_BY_LEVELS = {
    (ISIS_LEVEL_1,): 'level-1',
    (ISIS_LEVEL_2,): 'level-2-only',
    (ISIS_LEVEL_1, ISIS_LEVEL_2): 'level-1-2',
}

# per-interface circuit-type keyword for a single level
CIRCUIT_TYPE_BY_LEVEL = {
    ISIS_LEVEL_1: 'level-1',
    ISIS_LEVEL_2: 'level-2-only',
}


def _validate_net (net):
    '''
    Check the NET is present and well formed, and return it.

    A malformed NET is accepted by IOS without complaint - the process simply
    never forms an adjacency - so catching a typo here saves a long hunt on the
    device.
    '''
    if not net:
        raise Exception("CiscoISIS: net is mondatory before create()")
    if not PATTERN_NET.match(str(net).strip()):
        raise Exception(f"CiscoISIS: malformed net '{net}', "
                        "expected for example 49.0001.0000.0000.0002.00")
    return str(net).strip()


def _section_for_tag (resp, headline):
    '''
    Return the body lines of one 'router isis <tag>' section, header excluded.

    'show run | sec router isis' returns EVERY matching section when more than
    one process is configured, so capture starts at the line equal to the
    headline and stops at the next line starting in column 0. The echoed
    command and the trailing prompt are both column 0, so neither is captured.
    '''
    lines = []
    capturing = False
    for line in resp.splitlines():
        if not line.strip():
            continue
        if len(line) - len(line.lstrip()) == 0:
            if capturing:
                break
            capturing = line.strip().lower() == str(headline).strip().lower()
            continue
        if capturing:
            lines.append(line)
    return lines


def _section_value (lines, *key):
    '''
    Value of a 'key value' line, matched on whole lowercased tokens.

    Splits on any run of whitespace: IOS aligns some values into columns, so a
    single-space split is not safe. Returns None when the key is absent.
    '''
    width = len(key)
    for line in lines:
        tokens = line.split()
        if len(tokens) > width and tuple(t.lower() for t in tokens[:width]) == key:
            return tokens[width]
    return None


def _cisco_isis_get_af_command (name):
    '''
    Map an address family to the command that opens its block.

    IOS-XE has no 'address-family ipv4' under router isis - IPv4 is native to
    the process - so the IPv4 family returns None and emits no block. It still
    matters as a marker: it is what puts 'ip router isis' on the interfaces.
    '''
    if name == ISIS_AFAMILY_IPV4_UNICAST:
        return None
    elif name == ISIS_AFAMILY_IPV6_UNICAST:
        return 'address-family ipv6'
    else:
        raise Exception(f"CiscoISIS: address family '{name}' is not implemented")


def get_interface_name (intf_or_name):
    if isinstance(intf_or_name, CiscoInterface):
        return intf_or_name.name
    return intf_or_name


class CiscoISISAFamily(BaseConfig):
    '''
    IS-IS address family. Holds the raw feature lines emitted inside the
    family's block, for example 'multi-topology'.
    '''

    def __init__ (self, af_type, *features):
        BaseConfig.__init__(self, None, af_type)
        self.feature_list = list(features)

    def __repr__(self):
        return f"CiscoISISAFamily {self.name}"

    def add_feature (self, *features):
        for feature in features:
            self.feature_list.append(feature)

    def __apply__ (self, upref):
        self.upref = upref
        self.router = upref.router

        headline = _cisco_isis_get_af_command(self.name)
        if not headline:
            # IPv4 is native to the process - nothing to open, nothing to emit
            return

        self.router.enterWaitResponce(headline, PROMPT_ROUTER_AF)
        for feature in self.feature_list:
            self.router.enterWaitResponce(feature, PROMPT_ROUTER_AF)
        self.router.enterWaitResponce('exit-address-family', PROMPT_ROUTER)

    def __detach__ (self):
        self.upref = None
        self.router = None


class CiscoISISInterface(BaseConfig):
    '''
    An interface participating in IS-IS.

    The CLI lives in interface context and names the *process*, not the level,
    so __apply__ reaches the root through its parent level as
    self.upref.upref.
    '''

    def __init__ (self, interface, **kwargs):
        if isinstance(interface, CiscoInterface):
            name = interface.name
        elif isinstance(interface, str):
            name = interface
        else:
            raise Exception("CiscoISIS: unexpected interface name")

        BaseConfig.__init__(self, None, name)

        self.network_type = ISIS_INTF_NTYPE_P2P
        self.passive = False
        self.owner_level = None

        for feature in kwargs.keys():
            if feature == "network_type":
                self.network_type = kwargs[feature]
            elif feature == "passive":
                self.passive = kwargs[feature]
            elif feature == "metric":
                self.metric = kwargs[feature]
            elif feature == "circuit_type":
                self.circuit_type = kwargs[feature]
            else:
                raise Exception(f'CiscoISISInterface: unexpected feature {feature}')

    def __repr__(self):
        ret = f"CiscoISISInterface {self.name}"
        if self.passive:
            ret = ret + " (passive)"
        return ret

    def __circuit_type__ (self):
        '''Explicit circuit_type wins; otherwise it follows the owning level.'''
        if hasattr(self, "circuit_type") and self.circuit_type:
            return self.circuit_type
        if self.owner_level is not None:
            return CIRCUIT_TYPE_BY_LEVEL.get(self.owner_level.level)
        return None

    def __apply__ (self, upref):
        self.upref = upref              # parent CiscoISISLevel
        self.router = upref.router
        tag = self.upref.upref.name     # the isis process tag
        af_list = self.upref.upref.af_list

        # An empty af_list means the caller never declared a family; treat that
        # as IPv4, otherwise the interface would join no family at all.
        af_names = [af.name for af in af_list] or [ISIS_AFAMILY_IPV4_UNICAST]

        self.router.toConfig()
        self.router.enterWaitResponce(f"interface {self.name}", PROMPT_CFG_IF)

        if ISIS_AFAMILY_IPV4_UNICAST in af_names:
            self.router.enterWaitResponce(f"ip router isis {tag}", PROMPT_CFG_IF)
        if ISIS_AFAMILY_IPV6_UNICAST in af_names:
            self.router.enterWaitResponce(f"ipv6 router isis {tag}", PROMPT_CFG_IF)

        if not self.passive:
            self.router.enterWaitResponce(f"isis network {self.network_type}",
                                          PROMPT_CFG_IF)

        circuit_type = self.__circuit_type__()
        if circuit_type:
            self.router.enterWaitResponce(f"isis circuit-type {circuit_type}",
                                          PROMPT_CFG_IF)

        if hasattr(self, "metric") and self.metric:
            level = self.upref.level
            self.router.enterWaitResponce(f"isis metric {self.metric} level-{level}",
                                          PROMPT_CFG_IF)

        # leave the interface submode so the caller resumes at '(config)#'
        self.router.toConfig()

    def __remove__ (self, upref):
        '''Strip the IS-IS binding from the interface, leaving the interface
        itself alone.'''
        self.router = upref.router
        tag = upref.upref.name
        af_names = [af.name for af in upref.upref.af_list] or [ISIS_AFAMILY_IPV4_UNICAST]

        self.router.toConfig()
        self.router.enterWaitResponce(f"interface {self.name}", PROMPT_CFG_IF)
        if ISIS_AFAMILY_IPV4_UNICAST in af_names:
            self.router.enterWaitResponce(f"no ip router isis {tag}", PROMPT_CFG_IF)
        if ISIS_AFAMILY_IPV6_UNICAST in af_names:
            self.router.enterWaitResponce(f"no ipv6 router isis {tag}", PROMPT_CFG_IF)
        self.router.toConfig()

    def __detach__ (self):
        self.upref = None
        self.router = None


class CiscoISISLevel(BaseConfig):
    '''
    An IS-IS level. Owns the interfaces that run at this level and the
    level-scoped router commands, which IOS spells with a ' level-N' suffix.
    '''

    def __init__ (self, level, **kwargs):
        if level not in (ISIS_LEVEL_1, ISIS_LEVEL_2):
            raise Exception(f"CiscoISISLevel: level must be 1 or 2, got {level}")

        BaseConfig.__init__(self, None, level)
        self.level = level
        self.intf_list = []

        for feature in kwargs.keys():
            if feature == "metric_style":
                self.metric_style = kwargs[feature]
            else:
                raise Exception(f'CiscoISISLevel: unexpected feature {feature}')

    def __repr__(self):
        return f"CiscoISISLevel level-{self.level}"

    def add_interface (self, *isis_interface):
        for intf in isis_interface:
            if intf.owner_level is not None and intf.owner_level is not self:
                raise Exception(
                    f"CiscoISISLevel: {intf.name} already belongs to "
                    f"level-{intf.owner_level.level}; one interface cannot run "
                    "at two levels")
            intf.owner_level = self
            self.intf_list.append(intf)

    def remove_interface (self, *isis_interface):
        '''
        Attached: strip the binding from the device, then drop from the list.
        Detached: drop from the list only.
        '''
        for intf in isis_interface:
            if self.router:
                intf.__remove__(self)
            for known in list(self.intf_list):
                if known.name == intf.name:
                    known.owner_level = None
                    self.intf_list.remove(known)

    def __apply__ (self, upref):
        '''Level-scoped router commands. Expects router context.'''
        self.upref = upref
        self.router = upref.router

        if hasattr(self, "metric_style") and self.metric_style:
            self.router.enterWaitResponce(
                f"metric-style {self.metric_style} level-{self.level}",
                PROMPT_ROUTER)

    def __apply_passive__ (self, upref):
        '''passive-interface lines. Router context, so they cannot go in
        __apply__interfaces__ below.'''
        self.router = upref.router
        for intf in self.intf_list:
            if intf.passive:
                self.router.enterWaitResponce(f"passive-interface {intf.name}",
                                              PROMPT_ROUTER)

    def __apply_interfaces__ (self, upref):
        '''Interface context pass. Expects global config mode.'''
        self.upref = upref
        self.router = upref.router
        for intf in self.intf_list:
            intf.__apply__(self)

    def __remove_interfaces__ (self, upref):
        self.upref = upref
        self.router = upref.router
        for intf in self.intf_list:
            intf.__remove__(self)

    def __detach__ (self):
        for intf in self.intf_list:
            intf.__detach__()
        self.upref = None
        self.router = None


class CiscoISIS(CiscoFeatureConfig):
    '''
    IS-IS routing process.

    Inherits attach / modify / is_exist from CiscoFeatureConfig. net is
    mandatory; is-type is derived from the levels added unless given
    explicitly.

        isis = CiscoISIS(1, net='49.0001.0000.0000.0002.00')
        lvl2 = CiscoISISLevel(2, metric_style='wide')
        lvl2.add_interface(CiscoISISInterface(GE1),
                           CiscoISISInterface(L0, passive=True))
        isis.add_level(lvl2)
        isis.add_afamily(CiscoISISAFamily(ISIS_AFAMILY_IPV4_UNICAST))
        isis.create(router)
    '''

    attr_list = ('net', 'is_type')
    config_prompt = PROMPT_ROUTER

    def __init__ (self, name, **kwargs):
        # Unlike CiscoOspf the tag is not coerced to int - IS-IS tags are
        # commonly strings, as in 'router isis CORE'.
        BaseConfig.__init__(self, None, name)

        self.af_list = []
        self.level_list = []

        # net is optional here: attaching to an existing process needs only the
        # tag, and attach() reads the net back off the device. It is create()
        # that requires one.
        net = kwargs.pop('net', None)
        if net:
            self.net = _validate_net(net)

        for feature in kwargs.keys():
            if feature == 'is_type':
                self.is_type = kwargs[feature]
            else:
                error(f"CiscoISIS: Unexpected cfg feature {feature}")

    def __repr__(self):
        ret = f"{self.router.name} " if self.router else "noname "
        ret = ret + f"ISIS {self.name}"
        if getattr(self, 'net', None):
            ret = ret + f" net {self.net}"
        return ret

    def __headline__ (self):
        return f"router isis {self.name}"

    def __detect_filter__ (self):
        return "router isis"

    def __is_type__ (self):
        '''Explicit is_type wins; otherwise derive it from the levels added.'''
        if hasattr(self, "is_type") and self.is_type:
            return self.is_type
        levels = tuple(sorted({lvl.level for lvl in self.level_list}))
        return IS_TYPE_BY_LEVELS.get(levels)

    def __read_features__ (self):
        '''
        Read net and is-type back off the device after attaching.

        CiscoFeatureConfig.__is_exist__ fetches only headlines
        ('show run | inc ^router isis'), so the attributes are not in resp and
        this needs its own command.
        '''
        self.router.enterExecCommand('show run | sec router isis')
        section = _section_for_tag(self.router.resp, self.__headline__())
        self.__merge_features__({
            'net':     _section_value(section, 'net'),
            'is_type': _section_value(section, 'is-type'),
        })

    def __apply_feature__ (self, feature, value):
        if feature == 'net':
            self.net = _validate_net(value)
            self.router.enterWaitResponce(f"net {self.net}", PROMPT_ROUTER)
        elif feature == 'is_type':
            self.is_type = value
            if value:
                self.router.enterWaitResponce(f"is-type {value}", PROMPT_ROUTER)
            else:
                self.router.enterWaitResponce("no is-type", PROMPT_ROUTER)
        else:
            error(f" Unexpected cfg feature {feature}")

    def add_afamily (self, *afamilies):
        for af in afamilies:
            if self.router:
                self.router.toConfig()
                self.router.enterWaitResponce(self.__headline__(), PROMPT_ROUTER)
                af.__apply__(self)
                self.router.toConfig()
            self.af_list.append(af)

    def add_level (self, *levels):
        for level in levels:
            self.level_list.append(level)

    def create (self, router):
        # Required to create, and checked before any CLI is emitted so a
        # missing or malformed net cannot leave a half built process behind.
        self.net = _validate_net(getattr(self, 'net', None))

        self.router = router

        self.router.toConfig()
        self.router.enterWaitResponce(self.__headline__(), PROMPT_ROUTER)
        self.router.enterWaitResponce(f"net {self.net}", PROMPT_ROUTER)

        is_type = self.__is_type__()
        if is_type:
            self.router.enterWaitResponce(f"is-type {is_type}", PROMPT_ROUTER)

        for level in self.level_list:
            level.__apply__(self)
        for level in self.level_list:
            level.__apply_passive__(self)
        for af in self.af_list:
            af.__apply__(self)

        # interface context pass
        self.router.toConfig()
        for level in self.level_list:
            level.__apply_interfaces__(self)

        self.router.toConfig()
        info(f"{self} created")
        return True

    def delete (self, router=None):
        if router:
            self.router = router

        # 'no router isis' does not strip the per-interface bindings, so walk
        # the interfaces first.
        self.router.toConfig()
        for level in self.level_list:
            level.__remove_interfaces__(self)

        self.router.toConfig()
        self.router.enterWaitResponce(f"no router isis {self.name}", PROMPT_CFG)

        for level in self.level_list:
            level.__detach__()
        for af in self.af_list:
            af.__detach__()

        self.router.toConfig()
        self.router = None
        info(f"isis {self.name} deleted")


def cisco_get_all_isis (router):
    '''
    Returns the list of configured IS-IS process tags, lowercased
    (from 'show run | inc ^router isis'). An untagged 'router isis' is
    reported as an empty string.
    '''
    router.enterExecCommand('show run | inc ^router isis')
    tags = []
    for line in router.resp.splitlines():
        match = re.match(r'^router isis\s*(\S*)\s*$', line.strip())
        if match:
            tags.append(match.group(1).lower())
    return tags
