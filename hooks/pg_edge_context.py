# Copyright (c) 2015, PLUMgrid Inc, http://plumgrid.com

# This file contains the class that generates context for
# PLUMgrid template files.

from charmhelpers.core.hookenv import (
    relation_ids,
    related_units,
    relation_get,
)
from charmhelpers.contrib.openstack import context
from charmhelpers.contrib.openstack.utils import get_host_ip
from socket import gethostname as get_unit_hostname


def _pg_dir_settings():
    '''
    Inspects relation with PLUMgrid director.
    '''
    director_ips = []
    for rid in relation_ids('plumgrid'):
        for unit in related_units(rid):
            rdata = relation_get(rid=rid, unit=unit)
            director_ips.append(str(get_host_ip(rdata['private-address'])))
    return director_ips


class PGEdgeContext(context.NeutronContext):

    @property
    def plugin(self):
        '''
        Over-riding function in NeutronContext Class to return 'plumgrid'
        as the neutron plugin.
        '''
        return 'plumgrid'

    @property
    def network_manager(self):
        '''
        Over-riding function in NeutronContext Class to return 'neutron'
        as the network manager.
        '''
        return 'neutron'

    def _save_flag_file(self):
        '''
        Over-riding function in NeutronContext Class.
        Function only needed for OVS.
        '''
        pass

    def pg_ctxt(self):
        '''
        Generated Config for all PLUMgrid templates inside the
        templates folder.
        '''
        pg_ctxt = super(PGEdgeContext, self).pg_ctxt()
        if not pg_ctxt:
            return {}

        pg_dir_ips = ''
        pg_dir_settings = _pg_dir_settings()
        single_ip = True
        for ip in pg_dir_settings:
            if single_ip:
                pg_dir_ips = str(ip)
                single_ip = False
            else:
                pg_dir_ips = pg_dir_ips + ',' + str(ip)
        pg_ctxt['local_ip'] = pg_dir_ips
        pg_ctxt['pg_hostname'] = "pg-edge"
        from pg_edge_utils import get_mgmt_interface
        pg_ctxt['interface'] = get_mgmt_interface()
        pg_ctxt['label'] = get_unit_hostname()
        pg_ctxt['fabric_mode'] = 'host'

        return pg_ctxt
