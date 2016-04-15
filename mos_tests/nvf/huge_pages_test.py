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
import logging
import pytest

from mos_tests.functions.common import wait
from mos_tests.nvf import actions

logger = logging.getLogger(__name__)


@pytest.mark.testrail_id('111111')
def test_allocate_huge_pages_for_vm(os_conn, aggregate, hp_flavor, key, networks):
    vm1 = os_conn.create_server(name='vm1', flavor=hp_flavor, key_name=key,
                                nics=[{'net-id': networks[0]}])
    vm2 = os_conn.create_server(name='vm2', flavor=hp_flavor, key_name=key,
                                nics=[{'net-id': networks[0]}])
    vm3 = os_conn.create_server(name='vm3', flavor=hp_flavor, key_name=key,
                                nics=[{'net-id': networks[1]}])
    vm4 = os_conn.create_server(name='vm4', flavor=hp_flavor, key_name=key,
                                nics=[{'net-id': networks[1]}])
    [host1, host2] = aggregate.hosts
    for vm in [vm1, vm2, vm3]:
        if getattr(vm, "OS-EXT-SRV-ATTR:host") != host1:
            os_conn.nova.servers.live_migrate(
                vm, host1, block_migration=True, disk_over_commit=False)
            wait(lambda: os_conn.is_server_active(vm), timeout_seconds=10 * 60)
    if getattr(vm4, "OS-EXT-SRV-ATTR:host") != host2:
        os_conn.nova.servers.live_migrate(
            vm4, host2, block_migration=True, disk_over_commit=False)
        wait(lambda: os_conn.is_server_active(vm4), timeout_seconds=10 * 60)

    # # 6. Add floating ip
    # vm1_floating_ip = os_conn.assign_floating_ip(vm1)

    actions.check_compute(os_conn, host1, 1024, 256)
    actions.check_compute(os_conn, host2, 1024, 768)
    for vm in [vm1, vm2, vm3, vm4]:
        actions.check_instance(os_conn, vm, 2048)

    os_conn.delete_servers()
