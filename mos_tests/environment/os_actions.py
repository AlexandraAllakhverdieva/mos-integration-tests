#    Copyright 2015 Mirantis, Inc.
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

import time
import random
from tempfile import NamedTemporaryFile

from cinderclient import client as cinderclient
from glanceclient.v1 import Client as GlanceClient
from keystoneclient.v2_0 import Client as KeystoneClient
from keystoneclient.exceptions import ClientException as KeyStoneException
from novaclient.v1_1 import Client as NovaClient
from novaclient.exceptions import ClientException as NovaClientException
import neutronclient.v2_0.client as neutronclient
from neutronclient.common.exceptions import NeutronClientException
from devops.error import TimeoutError
from devops.helpers import helpers

from tools.settings import logger


class OpenStackActions(object):

    def __init__(self, controller_ip, user='admin', password='admin',
                 tenant='admin', cert=None):
        self.controller_ip = controller_ip

        if cert is None:
            auth_url = 'http://{0}:5000/v2.0/'.format(self.controller_ip)
            path_to_cert = None
        else:
            auth_url = 'https://{0}:5000/v2.0/'.format(self.controller_ip)
            with NamedTemporaryFile(prefix="fuel_cert_", suffix=".pem",
                                    delete=False) as f:
                f.write(cert)
            path_to_cert = f.name

        logger.debug('Auth URL is {0}'.format(auth_url))
        self.nova = NovaClient(username=user,
                               api_key=password,
                               project_id=tenant,
                               auth_url=auth_url,
                               cacert=path_to_cert)

        self.cinder = cinderclient.Client(1, user, password,
                                          tenant, auth_url,
                                          cacert=path_to_cert)

        self.neutron = neutronclient.Client(username=user,
                                            password=password,
                                            tenant_name=tenant,
                                            auth_url=auth_url,
                                            ca_cert=path_to_cert)

        self.keystone = self._get_keystoneclient(username=user,
                                                 password=password,
                                                 tenant_name=tenant,
                                                 auth_url=auth_url,
                                                 ca_cert=path_to_cert)

        token = self.keystone.auth_token
        logger.debug('Token is {0}'.format(token))
        glance_endpoint = self.keystone.service_catalog.url_for(
            service_type='image', endpoint_type='publicURL')
        logger.debug('Glance endpoind is {0}'.format(glance_endpoint))

        self.glance = GlanceClient(endpoint=glance_endpoint,
                                   token=token,
                                   cacert=path_to_cert)

    def _get_keystoneclient(self, username, password, tenant_name, auth_url,
                            retries=3, ca_cert=None):
        keystone = None
        for i in range(retries):
            try:
                if ca_cert:
                    keystone = KeystoneClient(username=username,
                                              password=password,
                                              tenant_name=tenant_name,
                                              auth_url=auth_url,
                                              cacert=ca_cert)

                else:
                    keystone = KeystoneClient(username=username,
                                              password=password,
                                              tenant_name=tenant_name,
                                              auth_url=auth_url)
                break
            except KeyStoneException as e:
                err = "Try nr {0}. Could not get keystone client, error: {1}"
                logger.warning(err.format(i + 1, e))
                time.sleep(5)
        if not keystone:
            raise
        return keystone

    def _get_cirros_image(self):
        for image in self.glance.images.list():
            if image.name.startswith("TestVM"):
                return image

    def get_instance_detail(self, server):
        details = self.nova.servers.get(server)
        return details

    def get_servers(self):
        servers = self.nova.servers.list()
        if servers:
            return servers

    def create_server(self, name, image_id=None, flavor=1, scenario='',
                      files=None, key_name=None, timeout=100, **kwargs):
        try:
            if scenario:
                with open(scenario, "r+") as f:
                    scenario = f.read()
        except Exception as exc:
            logger.info("Error opening file: %s" % exc)
            raise Exception()

        if image_id is None:
            image_id = self._get_cirros_image().id
        srv = self.nova.servers.create(name=name,
                                       image=image_id,
                                       flavor=1,
                                       userdata=scenario,
                                       files=files,
                                       key_name=key_name,
                                       **kwargs)
        try:
            helpers.wait(
                lambda: self.get_instance_detail(srv).status == "ACTIVE",
                timeout=timeout)
            return self.get_instance_detail(srv.id)
        except TimeoutError:
            logger.debug("Create server failed by timeout")
            assert self.get_instance_detail(srv).status == "ACTIVE", (
                "Instance doesn't reach active state, current state"
                " is {0}".format(self.get_instance_detail(srv).status))

    def get_nova_instance_ips(self, srv):
        """Return all nova instance ip addresses as dict

        Example return:
        {'floating': '10.109.2.2',
        'fixed': '192.168.1.2'}

        :param srv: nova instance
        :rtype: dict
        :return: Dict with server ips
        """
        return {x['OS-EXT-IPS:type']: x['addr']
                for y in srv.addresses.values()
                for x in y}

    def get_node_with_dhcp_for_network(self, net_id):
        result = self.list_dhcp_agents_for_network(net_id)
        nodes = [i['host'] for i in result['agents']]
        return nodes

    def list_dhcp_agents_for_network(self, net_id):
        return self.neutron.list_dhcp_agent_hosting_networks(net_id)

    def get_l3_agent_hosts(self, router_id):
        result = self.get_l3_for_router(router_id)
        hosts = [i['host'] for i in result['agents']]
        return hosts

    def get_l3_for_router(self, router_id):
        return self.neutron.list_l3_agent_hosting_routers(router_id)

    def create_network(self, name):
        network = {'name': name, 'admin_state_up': True}
        return self.neutron.create_network({'network': network})

    def create_subnet(self, network_id, name, cidr):
        subnet = {
            "network_id": network_id,
            "ip_version": 4,
            "cidr": cidr,
            "name": name
        }
        return self.neutron.create_subnet({'subnet': subnet})

    def list_networks(self):
        return self.neutron.list_networks()

    def assign_floating_ip(self, srv, use_neutron=False):
        if use_neutron:
            #   Find external net id for tenant
            nets = self.neutron.list_networks()['networks']
            err_msg = "Active external network not found in nets:{}"
            ext_net_ids = [
                net['id'] for net in nets
                if net['router:external'] and net['status'] == "ACTIVE"]
            assert ext_net_ids, err_msg.format(nets)
            net_id = ext_net_ids[0]
            #   Find instance port
            ports = self.neutron.list_ports(device_id=srv.id)['ports']
            err_msg = "Not found active ports for instance:{}"
            assert ports, err_msg.format(srv.id)
            port = ports[0]
            #   Create floating IP
            body = {'floatingip': {'floating_network_id': net_id,
                                   'port_id': port['id']}}
            flip = self.neutron.create_floatingip(body)
            #   Wait active state for port
            port_id = flip['floatingip']['port_id']
            state = lambda: self.neutron.show_port(port_id)['port']['status']
            helpers.wait(lambda: state() == "ACTIVE")
            return flip['floatingip']

        fl_ips_pool = self.nova.floating_ip_pools.list()
        if fl_ips_pool:
            floating_ip = self.nova.floating_ips.create(
                pool=fl_ips_pool[0].name)
            self.nova.servers.add_floating_ip(srv, floating_ip)
            return floating_ip

    def create_router(self, name, tenant_id=None):
        router = {'name': name}
        if tenant_id is not None:
            router['tenant_id'] = tenant_id
        return self.neutron.create_router({'router': router})

    def router_interface_add(self, router_id, subnet_id):
        subnet = {
            'subnet_id': subnet_id
        }
        self.neutron.add_interface_router(router_id, subnet)

    def router_gateway_add(self, router_id, network_id):
        network = {
            'network_id': network_id
        }
        self.neutron.add_gateway_router(router_id, network)

    def create_sec_group_for_ssh(self):
        name = "test-sg" + str(random.randint(1, 0x7fffffff))
        secgroup = self.nova.security_groups.create(
            name, "descr")

        rulesets = [
            {
                # ssh
                'ip_protocol': 'tcp',
                'from_port': 22,
                'to_port': 22,
                'cidr': '0.0.0.0/0',
            },
            {
                # ping
                'ip_protocol': 'icmp',
                'from_port': -1,
                'to_port': -1,
                'cidr': '0.0.0.0/0',
            }
        ]

        for ruleset in rulesets:
            self.nova.security_group_rules.create(
                secgroup.id, **ruleset)
        return secgroup

    def create_key(self, key_name):
        logger.debug('Try to create key {0}'.format(key_name))
        return self.nova.keypairs.create(key_name)

    def delete_subnets(self, networks):
        # Subnets and ports are simply filtered by network ids
        for subnet in self.neutron.list_subnets()['subnets']:
            if subnet['network_id'] not in networks:
                continue
            try:
                self.neutron.delete_subnet(subnet['id'])
            except NeutronClientException:
                logger.info('the subnet {} is not deletable'
                            .format(subnet['id']))

    def delete_routers(self):
        # Did not find the better way to detect the fuel admin router
        # Looks like it just always has fixed name router04
        for router in self.neutron.list_routers()['routers']:
            if router['name'] == 'router04':
                continue
            try:
                self.neutron.delete_router(router)
            except NeutronClientException:
                logger.info('the router {} is not deletable'
                            .format(router))

    def delete_floating_ips(self):
        for floating_ip in self.nova.floating_ips.list():
            try:
                self.nova.floating_ips.delete(floating_ip)
            except NovaClientException:
                logger.info('floating_ip {} is not deletable'.
                             format(floating_ip.id))

    def delete_servers(self):
        for server in self.nova.servers.list():
            try:
                self.nova.servers.delete(server)
            except NovaClientException:
                logger.info('nova server {} is not deletable'.format(server))

    def delete_keypairs(self):
        for key_pair in self.nova.keypairs.list():
            try:
                self.nova.keypairs.delete(key_pair)
            except NovaClientException:
                logger.info('key pair {} is not deletable'.
                             format(key_pair.id))

    def delete_security_groups(self):
        for sg in self.nova.security_groups.list():
            if sg.description == 'Default security group':
                continue
            try:
                self.nova.security_groups.delete(sg)
            except NovaClientException:
                logger.info('The Security Group {} is not deletable'
                             .format(sg))

    def delete_ports(self, networks):
        # After some experiments the following sequence for deletion was found
        # router_interface and ports -> subnets -> routers -> nets
        # Delete router interafce and ports
        # TBD some ports are still kept after the cleanup.
        # Need to find why and delete them as well
        # But it does not fail the execution so far.
        for port in self.neutron.list_ports()['ports']:
            if port['network_id'] not in networks:
                continue
            try:
                # TBD Looks like the port migh be used either by router or
                # l3 agent
                # in case of router this condition is true
                # port['network'] == 'router_interface'
                # dunno what will happen in case of the l3 agent
                for fixed_ip in port['fixed_ips']:
                    logger.debug(
                        self.neutron.remove_interface_router(
                            port['device_id'],
                            {
                                'router_id': port['device_id'],
                                'subnet_id': fixed_ip['subnet_id'],
                            }
                        )
                    )
                logger.debug(
                    self.neutron.delete_port(port['id'])
                )
            except NeutronClientException:
                logger.info('the port {} is not deletable'
                            .format(port['id']))

    def cleanup_network(self, networks_to_skip=[]):
        """Clean up the neutron networks.

        The networks that should be kept are passed as list of names
        """
        # net ids with the names from networks_to_skip are filtered out
        networks = [x['id'] for x in self.neutron.list_networks()['networks']
                    if x['name'] not in networks_to_skip]

        self.delete_keypairs()

        self.delete_floating_ips()

        self.delete_servers()

        self.delete_security_groups()

        self.delete_ports(networks)

        self.delete_subnets(networks)

        self.delete_routers()

        # Delete nets
        for net in networks:
            try:
                self.neutron.delete_network(net)
            except NeutronClientException:
                logger.info('the net {} is not deletable'
                            .format(net))
