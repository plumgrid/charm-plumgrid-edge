from charmhelpers.core.hookenv import (
    relation_ids,
    related_units,
    relation_get,
)
from charmhelpers.contrib.openstack import context

from socket import gethostname as get_unit_hostname

'''
#This function will be used to get information from neutron-api
def _neutron_api_settings():
    neutron_settings = {
        'neutron_security_groups': False,
        'l2_population': True,
        'overlay_network_type': 'gre',
    }
    for rid in relation_ids('neutron-plugin-api'):
        for unit in related_units(rid):
            rdata = relation_get(rid=rid, unit=unit)
            if 'l2-population' not in rdata:
                continue
            neutron_settings = {
                'l2_population': rdata['l2-population'],
                'neutron_security_groups': rdata['neutron-security-groups'],
                'overlay_network_type': rdata['overlay-network-type'],
            }
            # Override with configuration if set to true
            if config('disable-security-groups'):
                neutron_settings['neutron_security_groups'] = False
            return neutron_settings
    return neutron_settings
'''


#Use this function to get information from the director
def _pg_dir_settings():
    '''
    Inspects current plumgrid relation
    '''
    pg_settings = {
        'pg_dir_ip': '192.168.100.201',
    }
    for rid in relation_ids('plumgrid'):
        for unit in related_units(rid):
            rdata = relation_get(rid=rid, unit=unit)
            pg_settings = {
                'pg_dir_ip': rdata['private-address'],
            }
    return pg_settings


class PGEdgeContext(context.NeutronContext):
    interfaces = []

    @property
    def plugin(self):
        return 'plumgrid'

    @property
    def network_manager(self):
        return 'neutron'

    def _save_flag_file(self):
        pass

    #@property
    #def neutron_security_groups(self):
    #    neutron_api_settings = _neutron_api_settings()
    #    return neutron_api_settings['neutron_security_groups']

    def pg_ctxt(self):
        #Generated Config for all Plumgrid templates inside
        #the templates folder
        pg_ctxt = super(PGEdgeContext, self).pg_ctxt()
        if not pg_ctxt:
            return {}

        #conf = config()
        pg_dir_settings = _pg_dir_settings()
        pg_ctxt['local_ip'] = pg_dir_settings['pg_dir_ip']
        #neutron_api_settings = _neutron_api_settings()
        pg_ctxt['pg_hostname'] = "pg-edge"
        pg_ctxt['interface'] = "juju-br0"
        pg_ctxt['label'] = get_unit_hostname()
        pg_ctxt['fabric_mode'] = 'host'

        return pg_ctxt
