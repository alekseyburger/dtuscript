# GNU GENERAL PUBLIC LICENSE
# Autor: Aleksey Burger

import re

def paraseResponce(string):

    #remove unprintable
    string = ''.join([ c for c in string if c.isprintable() ])
    # define 3 match groups:
    # left: anything that finish with # or >
    # midle: string between left and right
    # right: > or # at the end of string
    founds = re.findall(r'(.*[#>]+)*(.+)([#>])$', string)
    if not founds:
        return ("none", "")
    found = founds[0]

    # found: use right substring as mode indicator
    lastChar = found[-1]
    mode = {
        '>': "user",
        '#': "exec",
    }.get(lastChar, "unknown")

    return (mode, found[-2] if len(found) > 1 else '' )
