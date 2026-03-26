# API Guide

## Chapter 1: Cisco Classes

### `RouterCisco`

Purpose: Core Cisco device transport/session class over Telnet. It manages connection lifecycle, CLI mode detection and transitions (`user`, `exec`, `config`, `config-deep`), command execution, prompt waiting, and syntax/connection error handling used by higher-level `Cisco*` configuration objects.

Methods:

- `RouterCisco(ipAddress, port, user, password)`: Creates a Cisco session object. 
- Parameters: 
- `ipAddress` (device IP/DNS), 
- `port` (Telnet console port), 
- `user` (login name, stored for context), 
- `password` (enable password used in `toExec`).
    Attributes: You can get it from the object
`mode` the value of USER_MODE, EXEC_MODE, CONFIG_MODE, CONFIG_DEEP_MODE
- `ignore_exception_syntax` (attribute, bool): When `True`, syntax errors detected in command responses do not raise `ExceptionDevice`.
- `ignore_exception_connection` don't raise exception in case the value is `True`
- Methods:
- `start()`: Opens Telnet transport and initializes prompt/mode detection.
- `end()`: Closes the active Telnet connection.
- `waitPrompt() -> bool`: Sends newline, reads prompt, updates `self.mode` and `self.name`, and returns `True` when prompt is recognized.
- `toUser()`: Attempts to move CLI back to user mode (`>`), using repeated `exit` when needed.
- `toExec()`: Ensures exec mode (`#`), including enable-password flow if currently in user mode.
- `toConfig()`: Ensures global config mode (`(config)#`) from any supported mode.

- `writeWithResponse(command, expect=None)`: Sends one command and waits for expected text. 
    Parameters: 
    `command` (CLI command string),
    `expect` (optional prompt/token to wait for; defaults to current prompt).
    CLI output is accessible in attribute `resp`

Exception: `ExceptionDevice` conveys error string as parameter




### `CiscoInterface`

Methods:

- `CiscoInterface(name)`: Creates an interface config object. Parameters: `name` (interface name, for example `GigabitEthernet1` or `Loopback100`).
- `attach(router) -> bool`: Binds object to an existing interface. Parameters: `router` (`RouterCisco` instance). Returns `True` if interface exists.
- `create(router) -> bool`: Creates or resets interface and applies staged attributes. Parameters: `router` (`RouterCisco` instance).
- `modify(**kwargs)`: Updates interface attributes. Parameters: keyword fields like `vrf`, `ipv4_address_mask`, `ipv6_address_mask`, `description`, `mpls`, `vlanId`.
- `delete(router=None)`: Removes subinterface/loopback or defaults physical interface. Parameters: `router` (optional `RouterCisco` override).
- `up()`: Applies `no shutdown` on the interface.
- `down()`: Applies `shutdown` on the interface.

Usage flow (`attach`, `create`, `modify`, `delete`):

- `attach(router)`: Use when interface already exists and you want immediate management without reset/recreate. Returns `False` if interface is missing.
- `create(router)`: Use when you want a deterministic baseline; it resets/recreates as needed, then applies attributes previously staged on the object.
- `modify(**kwargs)`: On attached objects, changes are pushed immediately to device; on unattached objects, values are only staged in memory until `create(router)`.
- `delete(router=None)`: Cleans up interface config; deletes subinterfaces/loopbacks and defaults physical interfaces.

Attributes:

- `is_subinterface` (bool): True if the interface is a subinterface (e.g., `GigabitEthernet1.100`).
- `is_loopback` (bool): True if the interface is a Loopback interface (name starts with `loopback`).
- `is_non_physical` (bool): True if the interface is non-physical (name starts with any of the prefixes in the constant list `["loopback", "bdi"]`).
- `ipv4_address` (property): Returns configured IPv4 address (without prefix length) or `None`.
- `ipv4_mask` (property): Returns configured IPv4 netmask in dotted format or `None`.

### `CiscoLdpInterface`

- `CiscoLdpInterface(interface, **kwargs)`: Creates an LDP interface binding object. Parameters: `interface` (`CiscoInterface` or interface-name string), `**kwargs` (currently unsupported feature arguments).
- `create()`: Placeholder for direct create workflow; currently not implemented.

### `CiscoLdp`

- `CiscoLdp(local_address=... | router_id=...)`: Creates global LDP config object. Parameters: optional `local_address` or `router_id` (interface/name used for LDP router-id).
- `create(router)`: Enables LDP and optional router-id on device. Parameters: `router` (`RouterCisco` instance).
- `delete(router=None)`: Removes LDP router-id and detaches registered interfaces. Parameters: `router` (optional `RouterCisco` override).
- `add_interface(*ldp_interface)`: Registers one or more `CiscoLdpInterface` children. Parameters: variadic `ldp_interface` objects.

Hierarchy:

```text
CiscoLdp
└─ CiscoLdpInterface
```

### `CiscoOspfInterface`

- `CiscoOspfInterface(interface, network_type=..., passive=...)`: Creates interface-level OSPF object. Parameters: `interface` (`CiscoInterface` or interface-name string), `network_type` (OSPF network type constant), `passive` (boolean passive-interface behavior).
- `create()`: Placeholder for direct create workflow; currently not implemented.

### `CiscoOspfArea`

- `CiscoOspfArea(name, **kwargs)`: Creates OSPF area container. Parameters: `name` (area ID), `**kwargs` (reserved; unsupported keys raise exception).
- `create()`: Placeholder for direct create workflow; currently not implemented.
- `add_interface(*ospf_interface)`: Attaches one or more `CiscoOspfInterface` objects to the area. Parameters: variadic `ospf_interface` objects.

### `CiscoOspf`

- `CiscoOspf(name, **kwargs)`: Creates OSPF process object. Parameters: `name` (process ID), `**kwargs` (currently unused).
- `add_area(ospf_area)`: Adds an area object to the process. Parameters: `ospf_area` (`CiscoOspfArea`).
- `create(router)`: Applies OSPF process and linked area/interface configuration. Parameters: `router` (`RouterCisco` instance).
- `delete(router=None)`: Removes OSPF process from router. Parameters: `router` (optional `RouterCisco` override).

Hierarchy:

```text
CiscoOspf
└─ CiscoOspfArea
    └─ CiscoOspfInterface
```

### `CiscoVrfAFamily`

- `CiscoVrfAFamily(af_type, **kwargs)`: Creates VRF address-family object. Parameters: `af_type` (for example IPv4 unicast constant), `**kwargs` (reserved).
- `create()`: Placeholder for direct create workflow; currently not implemented.
- `add_import_target(*targets)`: Adds one or more import route-targets. Parameters: variadic `targets` strings such as `65000:100`.
- `add_export_target(*targets)`: Adds one or more export route-targets. Parameters: variadic `targets` strings such as `65000:100`.

### `CiscoVrf`

- `CiscoVrf(name, rd, **kwargs)`: Creates VRF object. Parameters: `name` (VRF name), `rd` (route distinguisher), `**kwargs` (unsupported keys are logged).
- `is_exist(router=None) -> bool`: Checks whether VRF exists on device. Parameters: `router` (optional `RouterCisco`; falls back to attached router).
- `create(router)`: Applies VRF and attached AF family configuration. Parameters: `router` (`RouterCisco` instance).
- `delete(router=None)`: Removes VRF (or attached AF definitions) from device. Parameters: `router` (optional `RouterCisco` override).
- `add_afamily(*afamilies)`: Registers one or more `CiscoVrfAFamily` objects. Parameters: variadic `afamilies`.

### `CiscoBgpNeighborAFamily`

- `CiscoBgpNeighborAFamily(af_type, *features)`: Creates neighbor AF feature object. Parameters: `af_type` (BGP AF constant), `*features` (initial CLI feature strings).
- `create()`: Placeholder for direct create workflow; currently not implemented.
- `add_feature(feature_str)`: Adds feature command to internal set. Parameters: `feature_str` (CLI fragment, optional `no ...` form supported).
- `modify_feature(str)`: Applies feature add/remove live if router is attached. Parameters: `str` (CLI fragment, supports `no ...`).

### `CiscoBgpNeighbor`

- `CiscoBgpNeighbor(name, as_number, local_address=...)`: Creates BGP neighbor object. Parameters: `name` (neighbor IP/name), `as_number` (remote AS), optional `local_address` (update-source interface/name).
- `create()`: Placeholder for direct create workflow; currently not implemented.
- `add_afamily(*afamily)`: Attaches one or more neighbor AF objects. Parameters: variadic `afamily` (`CiscoBgpNeighborAFamily`).

### `CiscoBgpAFamily`

- `CiscoBgpAFamily(af_type, *features)`: Creates router-level/VRF-level BGP AF object. Parameters: `af_type` (BGP AF constant), `*features` (initial CLI feature strings).
- `create()`: Placeholder for direct create workflow; currently not implemented.
- `add_feature(feature_str)`: Adds feature command to AF feature set. Parameters: `feature_str` (CLI fragment).
- `modify_feature(str)`: Applies feature add/remove live if router is attached. Parameters: `str` (CLI fragment, supports `no ...`).

### `CiscoBgpVrf`

- `CiscoBgpVrf(vrf, **kwargs)`: Creates BGP VRF node. Parameters: `vrf` (`CiscoVrf` object or VRF name string), `**kwargs` (reserved).
- `create()`: Placeholder for direct create workflow; currently not implemented.
- `add_afamily(*afamilies)`: Adds one or more `CiscoBgpAFamily` objects. Parameters: variadic `afamilies`.
- `add_neighbor(*neighbors)`: Adds one or more neighbors to this VRF. Parameters: variadic `neighbors` (`CiscoBgpNeighbor`).
- `remove_neighbor(*neighbors)`: Removes one or more neighbors from this VRF. Parameters: variadic `neighbors` (`CiscoBgpNeighbor`).

### `CiscoBgp`

- `CiscoBgp(name, **kwargs)`: Creates top-level BGP process object. Parameters: `name` (local ASN/process identifier), `**kwargs` (reserved).
- `add_vrf(*vrfs)`: Adds one or more BGP VRF nodes. Parameters: variadic `vrfs` (`CiscoBgpVrf`).
- `create(router)`: Applies BGP process and all attached VRF/AF/neighbor structures. Parameters: `router` (`RouterCisco` instance).
- `delete(router=None)`: Removes BGP process and detaches children. Parameters: `router` (optional `RouterCisco` override).

Hierarchy:

```text
CiscoBgp
└─ CiscoBgpVrf
    ├─ CiscoBgpAFamily
    └─ CiscoBgpNeighbor
        └─ CiscoBgpNeighborAFamily
```

### Configuration Examples (Cisco)

```python
from router_cisco import RouterCisco
from cisco_interface import CiscoInterface
from cisco_ospf import CiscoOspf, CiscoOspfArea, CiscoOspfInterface

router = RouterCisco("10.1.1.1", 30252, "name", "pass")
router.start()

# Interface configuration
lo100 = CiscoInterface("Loopback100")
lo100.modify(ipv4_address_mask="33.33.33.1/32", description="loopback for test")
lo100.create(router)
lo100.up()

# OSPF configuration
ospf_intf = CiscoOspfInterface("Loopback100", passive=True)
area0 = CiscoOspfArea(0)
area0.add_interface(ospf_intf)

ospf = CiscoOspf(100)
ospf.add_area(area0)
ospf.create(router)

router.end()
```

## Chapter 2: Linux Classes

### `LinuxCli`

Purpose: SSH CLI session handler for Linux hosts. It establishes interactive SSH shell access via `Paramiko`, detects prompt/readiness, sends commands, collects command output (including paginated `--More--` handling), and provides simple mode/output helpers used by automation flows.

- `LinuxCli(ipAddress, user, password, name=None)`: Creates Linux CLI session object. Parameters: `ipAddress` (host IP/DNS), `user` (SSH username), `password` (SSH password), `name` (optional prompt host token).
- `startSSH() -> bool`: Opens SSH connection, starts interactive shell, and initializes prompt detection.
- `end()`: Closes channel and SSH client.
- `checkReady() -> bool`: Waits for channel readability and reports whether buffered data is ready.
- `binaryToAscii(binary) -> str`: Decodes bytes and strips common ANSI escape sequences. Parameters: `binary` (raw bytes from SSH channel).
- `readPrompt(prefix=None, clean=False) -> str`: Reads command output until prompt/pager conditions are satisfied. Parameters: `prefix` (optional command echo to trim), `clean` (when `True`, ignore previously buffered response).
- `waitPrompt()`: Repeatedly probes until a recognized prompt/mode is detected.
- `enterWaitResponce(command, expect=None)`: Sends command and collects response into `self.resp`. Parameters: `command` (shell command string), `expect` (unused compatibility parameter).
- `toConfig()`: Attempts transition to config-like mode by issuing mode-changing commands.
- `toExec()`: Attempts transition back to exec-like mode.
- `doesOutputContain(substr) -> bool`: Checks whether latest response contains substring. Parameters: `substr` (search text).

### Cisco Helpers

- `cisco_get_all_interfaces(router) -> list[str]`: Returns existing interface names from `show ip interface brief` in lowercase. Parameters: `router` (`RouterCisco` instance).
- `cisco_get_all_vrf(router) -> list[str]`: Returns VRF names parsed from `show vrf`. Parameters: `router` (`RouterCisco` instance).
- `cisco_get_all_bgp(router) -> list[str]`: Returns detected local BGP AS number(s) parsed from `show ip bgp summary`; returns an empty list if BGP is not active. Parameters: `router` (`RouterCisco` instance).

### Configuration Examples (Linux)

```python
from linux_cli import LinuxCli

cli = LinuxCli("192.0.2.10", "admin", "password")
if cli.startSSH():
    cli.enterWaitResponce("hostname")
    print(cli.resp)

    cli.enterWaitResponce("ip -br address")
    print(cli.resp)

    if cli.doesOutputContain("eth0"):
        print("eth0 found in output")

    cli.end()
```

## Chapter 3: Logging Configuration

### Files

- `dtuscript/loggin.conf`: Logging configuration used by dtuscript-side runs.
- `dtutest/loggin.conf`: Logging configuration used by test runs.

Both files use Python INI-style logging configuration and are loaded with `logging.config.fileConfig("loggin.conf")`.

### Structure

- `[loggers]`: Declares configured logger entries (`root`, `test`, `dtulib`, `device`).
- `[handlers]`: Declares output targets (`toFile`, `toConsole`).
- `[formatters]`: Declares message format profiles (`formConsole`, `formFile`).

### Logger Roles

- `root` (`[logger_root]`): Fallback logger, level `ERROR`, writes to file.
- `testLog` (`[logger_test]`, `qualname=testLog`): Test-script logging, level `INFO`, writes to file and console.
- `dtulibLog` (`[logger_dtulib]`, `qualname=dtulibLog`): Library/module debug logging, level `DEBUG`, writes to file and console.
- `deviceLog` (`[logger_device]`, `qualname=deviceLog`): Device I/O logging, level `DEBUG`, writes to file and console.

### Handlers

- `toConsole` (`StreamHandler`): level `INFO`, formatter `formConsole`.
- `toFile` (`FileHandler`): level `DEBUG`, formatter `formFile`, file `logs/dtutest.log`, mode `'w'` (overwrite each run).

### Formatter

Both console and file formatters use:

- `%(asctime)s %(levelname)s %(message)s`

### Effective Behavior

- Messages must pass both logger level and handler level.
- `DEBUG` messages from `dtulibLog`/`deviceLog` go to file.
- Console output starts at `INFO`, so `DEBUG` is hidden there by default.

### Typical Usage

```python
import logging
import logging.config

logging.config.fileConfig("loggin.conf")

test_logger = logging.getLogger("testLog")
lib_logger = logging.getLogger("dtulibLog")
device_logger = logging.getLogger("deviceLog")

test_logger.info("Test started")
lib_logger.debug("Applying interface config")
device_logger.debug("CLI response chunk")
```

### Common Adjustments

- Show debug on console: set `[handler_toConsole] level=DEBUG`.
- Keep log history: change file mode from `'w'` to `'a'` in `[handler_toFile] args`.
- Reduce verbosity: set `[logger_dtulib]` and `[logger_device]` to `ERROR`.
- Keep per-run overwrite behavior when reproducible logs are preferred.

### Notes

- File name is intentionally `loggin.conf` in this repo.
- File path `logs/dtutest.log` is relative to current working directory.
