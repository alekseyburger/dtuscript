# GNU GENERAL PUBLIC LICENSE
# Autor: Aleksey Burger
from builtins import str
import logging
import re

logger = logging.getLogger("dtulibLog")

def error(format):
    logger.error(f'\n\x1b[1;31mFeatureConfig: {format}\x1b[0m')

def info(format):
    logger.info(f'\n\x1b[1;92mFeatureConfig: {format}\x1b[0m')


def feature_str_normalize (str):
    str = ' '.join(str.split())
    return str.lower()

def _feature_set_modify (feature_set, str):
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
        return None
    is_no = len(match[0][0]) != 0
    nstr = feature_str_normalize(match[0][1])
    if is_no:
        feature_set.remove(nstr)
    else:
        feature_set.add(nstr)
    return feature_set

class BaseConfig:
    def __init__ (self, router, name):
        self.router = router
        self.name = ' '.join(name.strip().split()) if isinstance(name, str) else name


class FeatureConfig(BaseConfig):
    '''
    Platform-neutral implementation of the configuration object lifecycle
    described in dtu-doc/design_considerations.md.

    Provides attach / modify / is_exist and the attr_list machinery. A platform
    base (CiscoFeatureConfig in cisco_base.py, ExaFeatureConfig in exa_base.py)
    supplies the CLI mechanics; the concrete feature class supplies attr_list,
    __headline__, __detect_filter__ and __apply_feature__.

    create() and delete() are deliberately NOT defined here. The root classes
    differ too much to share one skeleton: CiscoOspf applies its areas in
    interface context before entering 'router ospf', and CiscoLdp has no
    submode at all. Each root keeps its own create()/delete().
    '''

    # Ordered tuple of configurable attributes. The order is the order in which
    # create() applies them, so it encodes dependencies (e.g. vrf before the
    # ip addresses that the vrf move would otherwise wipe).
    attr_list = ()

    # ---- hooks the concrete feature class must supply --------------------

    def __headline__ (self):
        '''The configuration line that identifies and enters the feature,
        e.g. "router ospf 1", "interface loopback0", "ip vrf red".'''
        raise NotImplementedError(f"{type(self).__name__} must define __headline__")

    def __detect_filter__ (self):
        '''Case-stable keyword prefix used to filter the running configuration
        when looking for this feature, e.g. "router ospf", "interface".'''
        raise NotImplementedError(f"{type(self).__name__} must define __detect_filter__")

    def __apply_feature__ (self, feature, value):
        '''Emit the CLI for one feature. Called with the router already in the
        feature's configuration context.'''
        raise NotImplementedError(f"{type(self).__name__} must define __apply_feature__")

    # ---- hooks the platform base supplies --------------------------------

    def __is_exist__ (self, router):
        raise NotImplementedError(f"{type(self).__name__} must define __is_exist__")

    def __enter_config__ (self):
        raise NotImplementedError(f"{type(self).__name__} must define __enter_config__")

    def __leave_config__ (self):
        raise NotImplementedError(f"{type(self).__name__} must define __leave_config__")

    def __commit__ (self):
        '''Commit policy. Cisco has none; Exaware overrides this.'''
        pass

    def __read_features__ (self):
        '''
        Populate attributes from the device, called by attach() once the object
        is bound. Default is a no-op; a feature class overrides it to parse its
        own configuration section, normally via __merge_features__ below.
        Raising rejects the attach.
        '''
        pass

    # ---- concrete lifecycle ----------------------------------------------

    def __set_feature__ (self, feature, value):
        '''Offline staging: update the python attribute only, never the device.'''
        if feature not in self.attr_list:
            error(f"{type(self).__name__}: unexpected cfg feature {feature}")
            return
        setattr(self, feature, value)

    def __apply_features__ (self):
        '''Push every staged attribute, in attr_list order.'''
        for feature in self.attr_list:
            if hasattr(self, feature):
                self.__apply_feature__(feature, getattr(self, feature))

    def is_exist (self, router=None):
        '''
        True if the feature is present on the device.

        Uses the attached router when the object is attached, otherwise the
        router passed in. Raises when neither is available.
        '''
        if self.router:
            router = self.router
        if not router:
            raise Exception(f"{type(self).__name__}: can't get router config - "
                            "router is not defined")
        return self.__is_exist__(router)

    def __merge_features__ (self, device_values):
        '''
        Reconcile attributes read back from the device with what the caller set.

        An attribute the caller set explicitly and that the device contradicts
        is an error; an attribute the caller never set is taken from the device.
        Only real instance attributes count as "set" - a value a class derives
        on the fly (CiscoISIS.is_type from the levels added, for example) is
        never consulted here, or attaching to a process whose shape differs
        from the staged one would be impossible.

        All disagreements are collected and reported together, so a caller with
        two wrong attributes sees both at once.
        '''
        mismatch = []
        for feature, device_value in device_values.items():
            if device_value is None:
                continue                        # nothing on the device to contradict
            if hasattr(self, feature):
                own = getattr(self, feature)
                if str(own) != str(device_value):
                    mismatch.append(
                        f"  {feature}: object '{own}' != device '{device_value}'")
            else:
                setattr(self, feature, device_value)

        if mismatch:
            raise Exception(f"{type(self).__name__}: attached object disagrees "
                            "with device:\n" + "\n".join(mismatch))

    def attach (self, router):
        '''
        Bind this object to configuration that already exists on the device,
        without changing that configuration. Returns False and stays detached
        when the feature is not present.

        Raises when __read_features__ finds the device contradicting an
        attribute the caller set explicitly. The object stays detached in that
        case, so a rejected attach never leaves it half bound.
        '''
        if not self.is_exist(router):
            return False
        self.router = router
        try:
            self.__read_features__()
        except Exception:
            self.router = None
            raise
        # logged last: __repr__ prints attributes read_features has just filled
        info(f"{self} attached")
        return True

    def modify (self, **kwargs):
        '''
        Attached: push each feature to the device immediately.
        Detached: stage each feature locally for a later create().
        '''
        if self.router:
            self.__enter_config__()
            for feature, value in kwargs.items():
                self.__apply_feature__(feature, value)
            self.__commit__()
            self.__leave_config__()
        else:
            for feature, value in kwargs.items():
                self.__set_feature__(feature, value)
        info(f"{self} modified")