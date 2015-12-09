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

import logging
import os

logger = logging.getLogger(__package__)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)
logger.setLevel(logging.INFO)

_boolean_states = {'1': True, 'yes': True, 'true': True, 'on': True,
                   '0': False, 'no': False, 'false': False, 'off': False}

def get_var_as_bool(name, default):
    value = os.environ.get(name, '')
    return _boolean_states.get(value.lower(), default)

PATH_TO_CERT = os.environ.get('PATH_TO_CERT', os.path.join(
    SSL_CERTS_DIR, 'ca.crt'))
DISABLE_SSL = get_var_as_bool('DISABLE_SSL', False)

LOGS_DIR = os.environ.get('LOGS_DIR', os.getcwd())

os.environ["ENV_NAME"] = "some_environment"
os.environ["ISO_PATH"] = "./fuel.iso"

JENKINS = {
    'url': os.environ.get('JENKINS_URL', 'http://localhost/'),
    'version_artifact': os.environ.get('JENKINS_VERSION_ARTIFACT',
                                       'version.yaml.txt')
}

GROUPS_TO_EXPAND = [
    'setup_master', 'prepare_release', 'prepare_slaves_1', 'prepare_slaves_3',
    'prepare_slaves_5', 'prepare_slaves_9']


class LaunchpadSettings(object):
    """LaunchpadSettings."""  # TODO documentation

    project = os.environ.get('LAUNCHPAD_PROJECT', 'fuel')
    milestone = os.environ.get('LAUNCHPAD_MILESTONE', '8.0')
    closed_statuses = [
        os.environ.get('LAUNCHPAD_RELEASED_STATUS', 'Fix Released'),
        os.environ.get('LAUNCHPAD_INVALID_STATUS', 'Invalid')
    ]


class TestRailSettings(object):
    """TestRailSettings."""  # TODO documentation

    url = os.environ.get('TESTRAIL_URL', 'https://mirantis.testrail.com')
    user = os.environ.get('TESTRAIL_USER', 'user@example.com')
    password = os.environ.get('TESTRAIL_PASSWORD', 'password')
    project = os.environ.get('TESTRAIL_PROJECT', 'Mirantis OpenStack')
    milestone = os.environ.get('TESTRAIL_MILESTONE', '8.0')
    tests_suite = os.environ.get('TESTRAIL_TEST_SUITE',
                                 '[{0}] Swarm'.format(milestone))
    tests_section = os.environ.get('TESTRAIL_TEST_SECTION', 'All')
    tests_include = os.environ.get('TESTRAIL_TEST_INCLUDE', None)
    tests_exclude = os.environ.get('TESTRAIL_TEST_EXCLUDE', None)
    previous_results_depth = os.environ.get('TESTRAIL_TESTS_DEPTH', 5)
    operation_systems = []
    centos_enabled = os.environ.get('USE_CENTOS', 'false') == 'true'
    ubuntu_enabled = os.environ.get('USE_UBUNTU', 'true') == 'true'
    if centos_enabled:
        operation_systems.append(os.environ.get(
            'TESTRAIL_CENTOS_RELEASE', 'Centos 6.5'))
    if ubuntu_enabled:
        operation_systems.append(os.environ.get(
            'TESTRAIL_UBUNTU_RELEASE', 'Ubuntu 14.04'))
