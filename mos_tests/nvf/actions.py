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


def check_compute(os_conn, host, total_pages, free_pages):
    compute = os_conn.env.find_node_by_fqdn(host)
    with os_conn.env.get_ssh_to_node(compute.data['ip']) as remote:
        total = remote.execute("grep HugePages_Total /proc/meminfo")['stdout']
        free = remote.execute("grep HugePages_Free /proc/meminfo")['stdout']
        assert str(total_pages) in total[0], "Unexpected HugePages_Total"
        assert str(free_pages) in free[0], "Unexpected HugePages_Free"


def check_instance(os_conn, vm, size):
    name = getattr(os_conn.nova.servers.get(vm),
                   "OS-EXT-SRV-ATTR:instance_name")
    host = os_conn.env.find_node_by_fqdn(
        getattr(os_conn.nova.servers.get(vm), "OS-EXT-SRV-ATTR:host"))
    with os_conn.env.get_ssh_to_node(host.data['ip']) as remote:
        cmd = "virsh dumpxml {0} " \
              "|awk '/memoryBacking/ {{p=1}}; p; /\/numatune/ {{p=0}}' " \
              "| grep 'page size='".format(name)
        res = remote.execute(cmd)['stdout'][0]
        assert "page size='{0}'".format(size) in res, "Unexpected package size"
