#Overview

This charm provides the PLUMgrid Edge configuration for a node.


# Usage

To deploy (partial deployment of linked charms only):

    juju deploy neutron-api
    juju deploy neutron-iovisor
    juju deploy plumgrid-director
    juju deploy plumgrid-edge
    juju add-relation plumgrid-edge neutron-iovisor
    juju add-relation plumgrid-edge plumgrid-director


