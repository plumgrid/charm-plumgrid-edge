# Overview

This charm is responsible for configuring a Compute node as a PLUMgrid Edge.

Once deployed, the charm configures the IO Visor kernel module as a PLUMgrid Edge. The charm also triggers the services essential for a PLUMgrid Edge.

# Usage

Step by step instructions on using the charm:

    juju deploy neutron-api
    juju deploy neutron-plumgrid-plugin neutron-api
    juju deploy neutron-iovisor
    juju deploy plumgrid-director --to <Machince No of neutron-iovisor>
    juju add-unit neutron-iovisor
    juju deploy plumgrid-edge --to <Machice No of 2nd unit of neutron-iovisor>

    juju add-relation neutron-api neutron-plumgrid-plugin
    juju add-relation neutron-plumgrid-plugin neutron-iovisor
    juju add-relation neutron-iovisor plumgrid-director
    juju add-relation neutron-iovisor plumgrid-edge
    juju add-relation plumgrid-director plumgrid-edge

For plumgrid-edge to work make the configuration in the neutron-api, neutron-plumgrid-plugin, neutron-iovisor and plumgrid-director charms as specified in the configuration section below.

# Known Limitations and Issues

This is an early access version of the PLUMgrid Edge charm and it is not meant for production deployments. The charm currently only supports JUNO. This charm needs to be deployed on a node where a unit of neutron-iovisor charm exists. Also plumgrid-director and plumgrid-gateway charms should not be deployed on the same node.

# Configuration

plumgrid-edge charm does not require any configuration itself but the following config is required in the other charms.

Example Config

    plumgrid-director:
        plumgrid-virtual-ip: "192.168.100.250"
    neutron-iovisor:
        install_sources: 'ppa:plumgrid-team/stable'
        install_keys: 'null'
    neutron-plumgrid-plugin:
        install_sources: 'ppa:plumgrid-team/stable'
        install_keys: 'null'
        enable-metadata: False
    neutron-api:
        neutron-plugin: "plumgrid"
        plumgrid-virtual-ip: "192.168.100.250"

The virtual IP passed on in the neutron-api charm has to be same as the one passed in the plumgrid-director charm.

# Contact Information

Bilal Baqar <bbaqar@plumgrid.com>
Bilal Ahmad <bilal@plumgrid.com>
