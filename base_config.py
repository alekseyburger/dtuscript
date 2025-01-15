# GNU GENERAL PUBLIC LICENSE
# Autor: Aleksey Burger
from builtins import str
import re


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