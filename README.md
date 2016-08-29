# About the PLUMgrid Platform

The [PLUMgrid Platform](http://www.plumgrid.com/technology/plumgrid-platform/) is a software-only solution that provides a rich set of distributed network functions such as routers, switches, NAT, IPAM, DHCP, and it also supports security policies, end-to-end encryption, and third party Layer 4-7 service insertion.


# Overview

This charm is responsible for configuring a Compute node as a PLUMgrid Edge. 

Once deployed, the charm configures the IO Visor kernel module as a PLUMgrid Edge. The charm also triggers the services essential for a PLUMgrid Edge.

It is a subordinate charm to nova-compute.

# Usage

Instructions on using the charm:

    juju deploy neutron-api
    juju deploy neutron-api-plumgrid
    juju deploy plumgrid-director
    juju deploy nova-compute
    juju deploy plumgrid-edge

    juju add-relation neutron-api neutron-api-plumgrid
    juju add-relation plumgrid-director plumgrid-edge
    juju add-relation nova-compute plumgrid-edge
    juju add-relation neutron-api-plumgrid plumgrid-edge

For plumgrid-edge to work make the configuration in the neutron-api, neutron-api-plumgrid and plumgrid-director charms as specified in the configuration section below.

# Known Limitations and Issues

This charm currently doesn't support Ubuntu 16.04.

# Configuration

Example Config

    plumgrid-edge:
        install_sources: 'ppa:plumgrid-team/stable'
        install_keys: 'null'
    plumgrid-director:
        plumgrid-virtual-ip: "192.168.100.250"
        install_sources: 'ppa:plumgrid-team/stable'
        install_keys: 'null'
    neutron-api-plumgrid:
        install_sources: 'ppa:plumgrid-team/stable'
        install_keys: 'null'
        enable-metadata: True
    neutron-api:
        neutron-plugin: "plumgrid"
        plumgrid-virtual-ip: "192.168.100.250"

Provide the source repo path for PLUMgrid Debs in 'install_sources' and the corresponding keys in 'install_keys'.
The virtual IP passed on in the neutron-api charm has to be same as the one passed in the plumgrid-director charm.

# Contact Information

Bilal Baqar <bbaqar@plumgrid.com>
Javeria Khan <javeriak@plumgrid.com>
Junaid Ali <junaidali@plumgrid.com>
