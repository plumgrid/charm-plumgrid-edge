#!/usr/bin/python

# Copyright (c) 2015, PLUMgrid Inc, http://plumgrid.com

# The hooks of this charm have been symlinked to functions
# in this file.

import sys

from charmhelpers.core.hookenv import (
    Hooks,
    UnregisteredHookError,
    log,
    relation_set,
    relation_ids,
    config,
)

from charmhelpers.fetch import (
    apt_install,
    apt_purge,
    configure_sources,
)

from charmhelpers.core.host import service_running

from pg_edge_utils import (
    register_configs,
    ensure_files,
    restart_pg,
    stop_pg,
    determine_packages,
    load_iovisor,
    remove_iovisor,
    ensure_mtu,
    add_lcm_key,
    fabric_interface_changed,
    load_iptables
)

hooks = Hooks()
CONFIGS = register_configs()


@hooks.hook()
def install():
    '''
    Install hook is run when the charm is first deployed on a node.
    '''
    load_iptables()
    configure_sources(update=True)
    pkgs = determine_packages()
    for pkg in pkgs:
        apt_install(pkg, options=['--force-yes'], fatal=True)
    load_iovisor()
    ensure_mtu()
    ensure_files()
    add_lcm_key()


@hooks.hook('plumgrid-relation-joined')
@hooks.hook('plumgrid-relation-changed')
def director_joined():
    '''
    This hook is run when relation between plumgrid-edge and
    plumgrid-director is made or changed.
    '''
    ensure_mtu()
    ensure_files()
    add_lcm_key()
    CONFIGS.write_all()
    restart_pg()


@hooks.hook('neutron-plugin-relation-joined')
@hooks.hook('plumgrid-plugin-relation-joined')
def neutron_plugin_joined(relation_id=None):
    '''
    This hook updates the metadata shared key in neutron-api-plumgrid
    and nova-compute.
    '''
    rel_data = {
        'metadata-shared-secret': config('metadata-shared-key'),
    }
    relation_set(relation_id=relation_id, **rel_data)


@hooks.hook('config-changed')
def config_changed():
    '''
    This hook is run when a config parameter is changed.
    It also runs on node reboot.
    '''
    charm_config = config()
    if charm_config.changed('lcm-ssh-key'):
        if add_lcm_key():
            log("PLUMgrid LCM Key added")
    if charm_config.changed('fabric-interfaces'):
        if not fabric_interface_changed():
            log("Fabric interface already set")
        else:
            stop_pg()
    if charm_config.changed('os-data-network'):
        ensure_files()
        if charm_config['fabric-interfaces'] == 'MANAGEMENT':
            log('Fabric running on managment network')
    if (charm_config.changed('install_sources') or
        charm_config.changed('plumgrid-build') or
        charm_config.changed('install_keys') or
            charm_config.changed('iovisor-build')):
        stop_pg()
        configure_sources(update=True)
        pkgs = determine_packages()
        for pkg in pkgs:
            apt_install(pkg, options=['--force-yes'], fatal=True)
            remove_iovisor()
            load_iovisor()
    if charm_config.changed('metadata-shared-key'):
        stop_pg()
        for rid in relation_ids('neutron-plugin'):
            neutron_plugin_joined(rid)
        for rid in relation_ids('plumgrid-plugin'):
            neutron_plugin_joined(rid)
    CONFIGS.write_all()
    # Restarting the plumgrid service only if it is
    # already stopped by any config-parameters or node reboot
    if not service_running('plumgrid'):
        restart_pg()


@hooks.hook('upgrade-charm')
def upgrade_charm():
    load_iptables()
    ensure_mtu()
    ensure_files()
    CONFIGS.write_all()
    restart_pg()


@hooks.hook('stop')
def stop():
    '''
    This hook is run when the charm is destroyed.
    '''
    stop_pg()
    remove_iovisor()
    pkgs = determine_packages()
    for pkg in pkgs:
        apt_purge(pkg, fatal=False)


def main():
    try:
        hooks.execute(sys.argv)
    except UnregisteredHookError as e:
        log('Unknown hook {} - skipping.'.format(e))


if __name__ == '__main__':
    main()
