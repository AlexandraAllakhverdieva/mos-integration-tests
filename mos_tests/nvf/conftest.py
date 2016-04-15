#    Copyright 2016 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import pytest


@pytest.yield_fixture
def aggregate(os_conn):
    hp_computes = []
    for compute in os_conn.env.get_nodes_by_role('compute'):
        with os_conn.env.get_ssh_to_node(compute.data['ip']) as remote:
            res = remote.execute('grep HugePages_Total /proc/meminfo')['stdout']
        if res:
            if res[0].split(':')[1].rstrip().lstrip() != '0':
                hp_computes.append(compute)
    aggr = os_conn.nova.aggregates.create('hpgs-aggr', 'nova')
    os_conn.nova.aggregates.set_metadata(aggr, {'hpgs': 'true'})
    for host in hp_computes:
        os_conn.nova.aggregates.add_host(aggr, host.data['fqdn'])
    yield aggr
    for host in hp_computes:
        os_conn.nova.aggregates.remove_host(aggr, host.data['fqdn'])
    os_conn.nova.aggregates.delete(aggr)


@pytest.yield_fixture
def hp_flavor(os_conn):
    flavor = os_conn.nova.flavors.create('m1.small.hpgs', 512, 1, 1)
    flavor.set_keys({'hw:mem_page_size': 2048})
    flavor.set_keys({'aggregate_instance_extra_specs:hpgs': 'true'})
    yield flavor.id
    os_conn.nova.flavors.delete(flavor)


@pytest.yield_fixture
def key(os_conn):
    key = os_conn.create_key(key_name='huge_pages')
    yield key.name
    os_conn.delete_key(key_name='huge_pages')


@pytest.fixture
def networks(os_conn):
    router = os_conn.create_router(name="router01")['router']
    ext_net = [x for x in os_conn.list_networks()['networks']
               if x.get('router:external')][0]
    os_conn.router_gateway_add(router_id=router['id'],
                               network_id=ext_net['id'])
    net01 = os_conn.add_net(router['id'])
    net02 = os_conn.add_net(router['id'])
    return [net01, net02]

