# Copyright (c) 2015, PLUMgrid Inc, http://plumgrid.com

# This file contains functions used by the hooks to deploy PLUMgrid Edge.

import pg_edge_context
import subprocess
import time
import os
import json
from collections import OrderedDict
from socket import gethostname as get_unit_hostname
from copy import deepcopy
from charmhelpers.contrib.openstack.neutron import neutron_plugin_attribute
from charmhelpers.contrib.storage.linux.ceph import modprobe
from charmhelpers.contrib.openstack import templating
from charmhelpers.core.hookenv import (
    log,
    config,
    unit_get,
    network_get_primary_address,
    status_set
)
from charmhelpers.contrib.network.ip import (
    get_iface_from_addr,
    get_host_ip,
    get_iface_addr,
    get_bridges,
    get_bridge_nics,
)
from charmhelpers.core.host import (
    write_file,
    service_restart,
    service_start,
    service_stop,
    service_running,
    path_hash,
    set_nic_mtu
)
from charmhelpers.fetch import (
    apt_cache,
    apt_install
)
from charmhelpers.contrib.openstack.utils import (
    os_release,
)

SOURCES_LIST = '/etc/apt/sources.list'
SHARED_SECRET = "/etc/nova/secret.txt"
LXC_CONF = '/etc/libvirt/lxc.conf'
TEMPLATES = 'templates/'
PG_LXC_DATA_PATH = '/var/lib/libvirt/filesystems/plumgrid-data'
PG_CONF = '%s/conf/pg/plumgrid.conf' % PG_LXC_DATA_PATH
PG_HN_CONF = '%s/conf/etc/hostname' % PG_LXC_DATA_PATH
PG_HS_CONF = '%s/conf/etc/hosts' % PG_LXC_DATA_PATH
PG_IFCS_CONF = '%s/conf/pg/ifcs.conf' % PG_LXC_DATA_PATH
OPS_CONF = '%s/conf/etc/00-pg.conf' % PG_LXC_DATA_PATH
AUTH_KEY_PATH = '%s/root/.ssh/authorized_keys' % PG_LXC_DATA_PATH
SUDOERS_CONF = '/etc/sudoers.d/ifc_ctl_sudoers'
FILTERS_CONF_DIR = '/etc/nova/rootwrap.d'
FILTERS_CONF = '%s/network.filters' % FILTERS_CONF_DIR
IFC_LIST_GW = '/var/run/plumgrid/ifc_list_gateway'

BASE_RESOURCE_MAP = OrderedDict([
    (PG_CONF, {
        'services': ['plumgrid'],
        'contexts': [pg_edge_context.PGEdgeContext()],
    }),
    (PG_HN_CONF, {
        'services': ['plumgrid'],
        'contexts': [pg_edge_context.PGEdgeContext()],
    }),
    (PG_HS_CONF, {
        'services': ['plumgrid'],
        'contexts': [pg_edge_context.PGEdgeContext()],
    }),
    (OPS_CONF, {
        'services': ['plumgrid'],
        'contexts': [pg_edge_context.PGEdgeContext()],
    }),
    (PG_IFCS_CONF, {
        'services': [],
        'contexts': [pg_edge_context.PGEdgeContext()],
    }),
    (FILTERS_CONF, {
        'services': [],
        'contexts': [pg_edge_context.PGEdgeContext()],
    }),
])


def configure_pg_sources():
    '''
    Returns true if install sources is updated in sources.list file
    '''
    try:
        with open(SOURCES_LIST, 'r+') as sources:
            all_lines = sources.readlines()
            sources.seek(0)
            for i in (line for line in all_lines if "plumgrid" not in line):
                sources.write(i)
            sources.truncate()
        sources.close()
    except IOError:
        log('Unable to update /etc/apt/sources.list')


def configure_analyst_opsvm():
    '''
    Configures Anaylyst for OPSVM
    '''
    if not service_running('plumgrid'):
        restart_pg()
    opsvm_ip = pg_edge_context._pg_dir_context()['opsvm_ip']
    NS_ENTER = ('/opt/local/bin/nsenter -t $(ps ho pid --ppid $(cat'
                '/var/run/libvirt/lxc/plumgrid.pid)) -m -n -u -i -p ')
    sigmund_stop = NS_ENTER + '/usr/bin/service plumgrid-sigmund stop'
    sigmund_status = NS_ENTER \
        + '/usr/bin/service plumgrid-sigmund status'
    sigmund_autoboot = NS_ENTER \
        + '/usr/bin/sigmund-configure --ip {0} --start --autoboot' \
        .format(opsvm_ip)
    try:
        status = subprocess.check_output(sigmund_status, shell=True)
        if 'start/running' in status:
            if subprocess.call(sigmund_stop, shell=True):
                log('plumgrid-sigmund couldn\'t be stopped!')
                return
        subprocess.check_call(sigmund_autoboot, shell=True)
    except:
        log('plumgrid-sigmund couldn\'t be started!')


def determine_packages():
    '''
    Returns list of packages required by PLUMgrid Edge as specified
    in the neutron_plugins dictionary in charmhelpers.
    '''
    pkgs = []
    tag = 'latest'
    for pkg in neutron_plugin_attribute('plumgrid', 'packages', 'neutron'):
        if 'plumgrid' in pkg:
            tag = config('plumgrid-build')
        elif pkg == 'iovisor-dkms':
            tag = config('iovisor-build')

        if tag == 'latest':
            pkgs.append(pkg)
        else:
            if tag in [i.ver_str for i in apt_cache()[pkg].version_list]:
                pkgs.append('%s=%s' % (pkg, tag))
            else:
                error_msg = \
                    "Build version '%s' for package '%s' not available" \
                    % (tag, pkg)
                raise ValueError(error_msg)
    return pkgs


def get_unit_address(binding='internal'):
    '''
    Returns the unit's PLUMgrid Management/Fabric IP
    '''
    try:
        # Using Juju 2.0 network spaces feature
        return network_get_primary_address(binding)
    except NotImplementedError:
        # Falling back to private-address
        return get_host_ip(unit_get('private-address'))


def register_configs(release=None):
    '''
    Returns an object of the Openstack Tempating Class which contains the
    the context required for all templates of this charm.
    '''
    release = release or os_release('nova-compute', base='kilo')
    if release < 'kilo':
        raise ValueError('OpenStack %s release not supported' % release)

    configs = templating.OSConfigRenderer(templates_dir=TEMPLATES,
                                          openstack_release=release)
    for cfg, rscs in resource_map().iteritems():
        configs.register(cfg, rscs['contexts'])
    return configs


def resource_map():
    '''
    Dynamically generate a map of resources that will be managed for a single
    hook execution.
    '''
    resource_map = deepcopy(BASE_RESOURCE_MAP)
    return resource_map


def restart_map():
    '''
    Constructs a restart map based on charm config settings and relation
    state.
    '''
    return {cfg: rscs['services'] for cfg, rscs in resource_map().iteritems()}


def ensure_files():
    '''
    Ensures PLUMgrid specific files exist before templates are written.
    '''
    release = os_release('nova-compute', base='kilo')
    if release == 'kilo':
        disable_apparmor_libvirt()
    write_file(SUDOERS_CONF,
               "\nnova ALL=(root) NOPASSWD: /opt/pg/bin/ifc_ctl_pp *\n",
               owner='root', group='root', perms=0o644)
    _exec_cmd(cmd=['mkdir', '-p', FILTERS_CONF_DIR])
    _exec_cmd(cmd=['touch', FILTERS_CONF])


def restart_pg():
    '''
    Stops and Starts PLUMgrid service after flushing iptables.
    '''
    stop_pg()
    service_start('plumgrid')
    time.sleep(3)
    if not service_running('plumgrid'):
        if service_running('libvirt-bin'):
            raise ValueError("plumgrid service couldn't be started")
        else:
            if service_start('libvirt-bin'):
                time.sleep(8)
                if not service_running('plumgrid') \
                        and not service_start('plumgrid'):
                    raise ValueError("plumgrid service couldn't be started")
            else:
                raise ValueError("libvirt-bin service couldn't be started")
    status_set('active', 'Unit is ready')


def stop_pg():
    '''
    Stops PLUMgrid service.
    '''
    service_stop('plumgrid')
    time.sleep(2)


def load_iovisor():
    '''
    Loads iovisor kernel module.
    '''
    modprobe('iovisor')


def remove_iovisor():
    '''
    Removes iovisor kernel module.
    '''
    _exec_cmd(cmd=['rmmod', 'iovisor'],
              error_msg='Error Removing IOVisor Kernel Module')
    time.sleep(1)


def interface_exists(interface):
    '''
    Checks if interface exists on node.
    '''
    try:
        subprocess.check_call(['ip', 'link', 'show', interface],
                              stdout=open(os.devnull, 'w'),
                              stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        return False
    return True


def get_mgmt_interface():
    '''
    Returns the managment interface.
    '''
    mgmt_interface = config('mgmt-interface')
    if not mgmt_interface:
        try:
            return get_iface_from_addr(get_unit_address('internal'))
        except:
            # workaroud if get_unit_address returns hostname
            # (issue with unit-get 'private-address') also
            # workaround the curtin issue where the
            # interface on which bridge is created also gets
            # an ip
            for bridge_interface in get_bridges():
                if (get_unit_address()
                        in get_iface_addr(bridge_interface)):
                    return bridge_interface
    elif interface_exists(mgmt_interface):
        return mgmt_interface
    else:
        log('Provided managment interface %s does not exist'
            % mgmt_interface)
        return get_iface_from_addr(get_unit_address())


def fabric_interface_changed():
    '''
    Returns true if interface for node changed.
    '''
    fabric_interface = get_fabric_interface()
    try:
        with open(PG_IFCS_CONF, 'r') as ifcs:
            for line in ifcs:
                if 'fabric_core' in line:
                    if line.split()[0] == fabric_interface:
                        return False
    except IOError:
        return True
    return True


def remove_ifc_list():
    '''
    Removes ifc_list_gateway file if fabric interface is changed
    '''
    _exec_cmd(cmd=['rm', '-f', IFC_LIST_GW])


def get_fabric_interface():
    '''
    Returns the fabric interface.
    '''
    fabric_interfaces = config('fabric-interfaces')
    if not fabric_interfaces:
        try:
            fabric_ip = get_unit_address('compute-data')
            mgmt_ip = get_unit_address('internal')
        except:
            raise ValueError('Unable to get interface using \'fabric\' \
                              binding! Ensure fabric interface has IP \
                              assigned.')
        if fabric_ip == mgmt_ip:
            return get_mgmt_interface()
        else:
            return get_iface_from_addr(fabric_ip)
    else:
        try:
            all_fabric_interfaces = json.loads(fabric_interfaces)
        except ValueError:
            raise ValueError('Invalid json provided for fabric interfaces')
    hostname = get_unit_hostname()
    if hostname in all_fabric_interfaces:
        node_fabric_interface = all_fabric_interfaces[hostname]
    elif 'DEFAULT' in all_fabric_interfaces:
        node_fabric_interface = all_fabric_interfaces['DEFAULT']
    else:
        raise ValueError('No fabric interface provided for node')
    if interface_exists(node_fabric_interface):
        return node_fabric_interface
    else:
        log('Provided fabric interface %s does not exist'
            % node_fabric_interface)
        raise ValueError('Provided fabric interface does not exist')
    return node_fabric_interface


def ensure_mtu():
    '''
    Ensures required MTU of the underlying networking of the node.
    '''
    interface_mtu = config('network-device-mtu')
    fabric_interface = get_fabric_interface()
    if fabric_interface in get_bridges():
        attached_interfaces = get_bridge_nics(fabric_interface)
        for interface in attached_interfaces:
            set_nic_mtu(interface, interface_mtu)
    set_nic_mtu(fabric_interface, interface_mtu)


def _exec_cmd(cmd=None, error_msg='Command exited with ERRORs', fatal=False,
              verbose=False):
    '''
    Function to execute any bash command on the node.
    '''
    if cmd is None:
        log("No command specified")
    else:
        if fatal and verbose:
            subprocess.check_call(cmd, stdout=open(os.devnull, 'w'),
                                  stderr=subprocess.STDOUT)
        elif fatal and not verbose:
            subprocess.check_call(cmd)
        else:
            try:
                if verbose:
                    subprocess.check_call(cmd, stdout=open(os.devnull, 'w'),
                                          stderr=subprocess.STDOUT)
                else:
                    subprocess.check_call(cmd)
            except subprocess.CalledProcessError:
                log(error_msg)


def disable_apparmor_libvirt():
    '''
    Disables Apparmor profile of libvirtd.
    '''
    apt_install('apparmor-utils')
    apt_install('cgroup-bin')
    _exec_cmd(['sudo', 'aa-disable', '/usr/sbin/libvirtd'],
              error_msg='Error disabling AppArmor profile of libvirtd',
              verbose=True)
    disable_apparmor()
    service_restart('libvirt-bin')


def disable_apparmor():
    '''
    Disables Apparmor security for lxc.
    '''
    try:
        f = open(LXC_CONF, 'r')
    except IOError:
        log('Libvirt not installed yet')
        return 0
    filedata = f.read()
    f.close()
    newdata = filedata.replace("security_driver = \"apparmor\"",
                               "#security_driver = \"apparmor\"")
    f = open(LXC_CONF, 'w')
    f.write(newdata)
    f.close()


def add_lcm_key():
    '''
    Adds public key of PLUMgrid-lcm to authorized keys of PLUMgrid Edge.
    '''
    key = config('lcm-ssh-key')
    if key == 'null':
        log('lcm key not specified')
        return 0
    file_write_type = 'w+'
    if os.path.isfile(AUTH_KEY_PATH):
        file_write_type = 'a'
        try:
            fr = open(AUTH_KEY_PATH, 'r')
        except IOError:
            log('plumgrid-lxc not installed yet')
            return 0
        for line in fr:
            if key in line:
                log('key already added')
                return 0
    try:
        fa = open(AUTH_KEY_PATH, file_write_type)
    except IOError:
        log('Error opening file to append')
        return 0
    fa.write(key)
    fa.write('\n')
    fa.close()
    return 1


def load_iptables():
    '''
    Loads iptables rules to allow all PLUMgrid communication.
    '''
    network = get_cidr_from_iface(get_mgmt_interface())
    if network:
        _exec_cmd(['sudo', 'iptables', '-A', 'INPUT', '-p', 'tcp',
                   '-j', 'ACCEPT', '-s', network, '-d',
                   network, '-m', 'state', '--state', 'NEW'])
        _exec_cmd(['sudo', 'iptables', '-A', 'INPUT', '-p', 'udp', '-j',
                   'ACCEPT', '-s', network, '-d', network,
                   '-m', 'state', '--state', 'NEW'])
        apt_install('iptables-persistent')


def get_cidr_from_iface(interface):
    '''
    Determines Network CIDR from interface.
    '''
    if not interface:
        return None
    apt_install('ohai')
    try:
        os_info = subprocess.check_output(['ohai', '-l', 'fatal'])
    except OSError:
        log('Unable to get operating system information')
        return None
    try:
        os_info_json = json.loads(os_info)
    except ValueError:
        log('Unable to determine network')
        return None
    device = os_info_json['network']['interfaces'].get(interface)
    if device is not None:
        if device.get('routes'):
            routes = device['routes']
            for net in routes:
                if 'scope' in net:
                    return net.get('destination')
        else:
            return None
    else:
        return None


def director_cluster_ready():
    dirs_count = len(pg_edge_context._pg_dir_context()['director_ips'])
    return True if dirs_count == 1 or dirs_count == 3 else False


def restart_on_change(restart_map):
    """
    Restart services based on configuration files changing
    """
    def wrap(f):
        def wrapped_f(*args, **kwargs):
            checksums = {path: path_hash(path) for path in restart_map}
            f(*args, **kwargs)
            for path in restart_map:
                if path_hash(path) != checksums[path]:
                    restart_pg()
                    break
        return wrapped_f
    return wrap
