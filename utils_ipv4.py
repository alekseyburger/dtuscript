# GNU GENERAL PUBLIC LICENSE
# Autor: Aleksey Burger

import re

def bits_in_byte(b):
	if b < 0 or b >8:
		raise Exception(f'bits_in_byte: {b} is not expected')
	res = 0
	for i in range(0,b):
		res = res + (1 << (7-i))
	return res


def mlen_to_mask (mlen):
	if mlen < 8:
		return bits_in_byte(mlen) << 24
	if mlen < 16:
		return 0xFF000000 + (bits_in_byte(mlen%8) << 16)
	if mlen < 24:
		return 0xFFFF0000 + (bits_in_byte(mlen%16) << 8)
	if mlen < 32:
		return 0xFFFFFF00 + (bits_in_byte(mlen%24))
	return 0xFFFFFFFF

def mask_len_to_4digit (mlen):
	mask = mlen_to_mask(mlen)
	if not mask:
		return None
	bytes_list = [str(d) for d in (0xFF&(mask>>24), 0xFF&(mask>>15), 0xFF&(mask>>8), 0xFF&mask) ]
	return '.'.join(bytes_list)

def replace_byte (saddr, ibyte, val):
    pars_list = re.findall(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', saddr)
    if len(pars_list) != 1:
        return None
    pars_tuple = pars_list[0]
    if len(pars_tuple) != 4:
        return None
    res_list  = [*pars_tuple]
    res_list[ibyte] = str(val)
    return '.'.join(res_list)