# GNU GENERAL PUBLIC LICENSE
# Autor: Aleksey Burger

VRF_AFAMILY_IPV4_UNICAST = "af-ipv4 unicast"
VRF_AFAMILY_IPV6_UNICAST = "af-ipv6 unicast"

BGP_AFAMILY_IPV4_UNICAST = "af-ipv4 unicast"
BGP_AFAMILY_IPV6_UNICAST = "af-ipv6 unicast"
BGP_AFAMILY_L2_EVPN = "af-l2vpn evpn"
BGP_AFAMILY_IPV4_VPN = "af-ipv4 vpn"

OSPF_INTF_NTYPE_P2P = "point-to-point"
OSPF_INTF_NTYPE_P2M = "point-to-multipoint"
OSPF_INTF_NTYPE_BCAST = "broadcast"
OSPF_INTF_NTYPE_NBCAST = "non-broadcast"
OSPF_INTF_NTYPE_P2M_NBCAST = "p2mp-non-broadcast"

# On Exaware these strings are the CLI command itself; on Cisco they are mapped
# to 'address-family ...' by _cisco_isis_get_af_command() in cisco_isis.py.
ISIS_AFAMILY_IPV4_UNICAST = "af-ipv4 unicast"
ISIS_AFAMILY_IPV6_UNICAST = "af-ipv6 unicast"

ISIS_LEVEL_1 = 1
ISIS_LEVEL_2 = 2

ISIS_INTF_NTYPE_P2P = "point-to-point"
ISIS_INTF_NTYPE_BCAST = "broadcast"