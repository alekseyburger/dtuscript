Python framework for configuring and testing a network with Cisco routers

The framework contains two types of classes. The RouterCisco class creates communication channels with the router via a telnet connection to the console port. This class also allows changing the mode of interaction with the router (Exec/Config), sends console commands and receives a response from the router. 
Configuration objects are created to store the desired configurations. The methods of these classes interact with the router and try on the configuration via the RouterCisco object. 
Examples of configuration classes are CiscoInterface, CiscoOspf, CiscoBgp, etc.

Example for connection to router console on port 10.1.1.1:30252

```
HOST = "10.1.1.1"
port=30252
router = RouterCisco(HOST, port, "name", "pass")
router.start()    # start conntction
router.toExec()   # go to exec mode
# print platform info
router.writeWithResponce("show platform", "#")
print(router.resp)
```

Example for loopback creation:
```
L100  = CiscoInterface('Loopback100')
if not L100.attach(router):       # is loopback exist yet
    L100.create(router)           # create if needed
L100.modify(ipv4_address_mask="33.33.33.1/32", description="loopback for test")
L100.up()
```
