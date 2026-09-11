# GNU GENERAL PUBLIC LICENSE
# Autor: Aleksey Burger

import logging
from base_config import FeatureConfig

logger = logging.getLogger("dtulibLog")

def trace(format):
    logger.debug(f'\n\x1b[1;94mCiscoFeature: {format}\x1b[0m')

def error(format):
    logger.error(f'\n\x1b[1;31mCiscoFeature: {format}\x1b[0m')

def info(format):
    logger.info(f'\n\x1b[1;92mCiscoFeature: {format}\x1b[0m')


class CiscoFeatureConfig(FeatureConfig):
    '''
    Cisco half of the FeatureConfig contract: how to detect a feature in the
    running configuration, how to enter and leave its configuration context,
    and the (absent) commit policy.

    A concrete class supplies __headline__, __detect_filter__, attr_list,
    __apply_feature__ and config_prompt.
    '''

    # Prompt the feature's configuration context shows, e.g. '(config-if)#'.
    # Features that have no submode of their own leave this at '(config)#'.
    config_prompt = '(config)#'

    def __is_exist__ (self, router):
        '''
        Look the feature up in the running configuration.

        The '^' anchor keeps sub-lines out of the match - without it
        'passive-interface Loopback0' would answer a query for
        'interface Loopback0'.

        The comparison is done in python, lowercased, rather than by making the
        filter more specific: IOS '| include' is case sensitive and the running
        config prints 'interface Loopback0' / 'router ospf 1', while
        BaseConfig lowercases self.name. Filtering on '^interface loopback0'
        would therefore match nothing.
        '''
        router.enterExecCommand(f"show run | inc ^{self.__detect_filter__()}")
        headline = str(self.__headline__()).strip().lower()
        for line in router.resp.splitlines():
            if line.strip().lower() == headline:
                return True
        return False

    def __enter_config__ (self):
        '''Put the session in the feature's configuration context.'''
        self.router.toConfig()
        self.router.enterWaitResponce(self.__headline__(), self.config_prompt)

    def __leave_config__ (self):
        '''Return to global config, so the caller resumes at '(config)#'.'''
        self.router.toConfig()

    def __commit__ (self):
        '''Cisco applies configuration as it is entered - nothing to commit.'''
        pass
