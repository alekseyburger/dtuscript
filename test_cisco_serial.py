#!/usr/bin/env python3
# GNU GENERAL PUBLIC LICENSE
# Autor: Aleksey Burger

from router_cisco import RouterCisco
from cisco_interface import CiscoInterface, cisco_get_all_interfaces
from cisco_bgp import CiscoBgp, CiscoBgpVrf, CiscoBgpAFamily, CiscoBgpNeighbor, CiscoBgpNeighborAFamily
from cisco_bgp import cisco_get_all_bgp
from dtu_definition import BGP_AFAMILY_IPV4_UNICAST,BGP_AFAMILY_IPV6_UNICAST,BGP_AFAMILY_L2_EVPN, BGP_AFAMILY_IPV4_VPN
import time
import logging, logging.config

logging.config.fileConfig("loggin.conf")
logger = logging.getLogger("testLog")

HOST = "10.10.10.1"
port=30001

logger.info("-- Start --")
crouter = RouterCisco(HOST, port, "cisco", "cisco")
crouter.start()
crouter.toExec()
crouter.writeWithResponce("terminal length 0")

GE1 = CiscoInterface('GigabitEthernet1')
if not GE1.attach(crouter):
    GE1.create(crouter)

GE1.down()
time.sleep(3)
GE1.up()

GE1.delete()

# define Loopback100 interface
L100  = CiscoInterface('Loopback100')
if not L100.attach(crouter):
    L100.create(crouter)
L100.modify(ipv4_address_mask="33.33.33.1/32", description="loopback for test")
L100.up()


# define iBGP peers
bgp_as = 111
neighbor_af_ipv4 = CiscoBgpNeighborAFamily(BGP_AFAMILY_IPV4_UNICAST)
neighbor = CiscoBgpNeighbor("77.77.77.77", bgp_as, local_address=L100)
neighbor.add_afamily(neighbor_af_ipv4)
bgp_default = CiscoBgpVrf('default')
bgp_default.add_neighbor(neighbor)
bgp = CiscoBgp(bgp_as)
bgp.add_vrf(bgp_default)
bgp.create(crouter)

# show bgp neighbors
logger.info(cisco_get_all_bgp(crouter))

# remove BGP
bgp.delete()

crouter.toExec()
crouter.writeWithResponce("show ip int b", "#")

L100.delete()

crouter.toExec()
crouter.writeWithResponce("show ip int b", "#")

crouter.toExec()
crouter.writeWithResponce("show platform", "#")

crouter.end()

logger.info("-- End --")

