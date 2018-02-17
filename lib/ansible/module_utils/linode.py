# This code is part of Ansible, but is an independent component.
# This particular file snippet, and this file snippet only, is BSD licensed.
# Modules you write using this snippet, which is embedded dynamically by Ansible
# still belong to the author of the module, and may assign their own license
# to the complete work.
#
# Copyright (c), Ansible Project 2018
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import json
import os
from ansible.module_utils.urls import fetch_url
from ansible.module_utils._text import to_text
from ansible.module_utils.basic import env_fallback
try:
    # python3
    from urllib.parse import ParseResult
    from urllib.parse import urlunparse
except ImportError:
    # python2
    from urlparse import ParseResult
    from urlparse import urlunparse


class Response(object):

    def __init__(self, resp, info):
        self.body = None
        if resp:
            self.body = resp.read()
        self.info = info

    @property
    def json(self):
        if not self.body:
            if "body" in self.info:
                return json.loads(to_text(self.info["body"]))
            return None
        try:
            return json.loads(to_text(self.body))
        except ValueError:
            return None

    @property
    def status_code(self):
        return self.info["status"]


class LinodeV4Helper:

    def __init__(self, module):
        self.module = module
        self.baseurl = 'https://api.linode.com/v4'
        self.oauth_token = None
        self.headers = {'Authorization': 'Bearer {0}'.format(self.oauth_token),
                        'Content-type': 'application/json'}

        # Check if api_token is valid or not
        response = self.get('account')
        if response.status_code == 401:
            module.fail_json(msg='Failed to login using API token, please verify validity of API token.')

        self.timeout = module.params.get('timeout', 30)

    def _url_builder(self, path):
        if path[0] == '/':
            path = path[1:]
        return '%s/%s' % (self.baseurl, path)

    def send(self, method, path, data=None):
        url = self._url_builder(path)
        data = self.module.jsonify(data)

        resp, info = fetch_url(self.module, url, data=data, headers=self.headers, method=method, timeout=self.timeout)

        return Response(resp, info)

    def get(self, path, data=None):
        return self.send('GET', path, data)

    def put(self, path, data=None):
        return self.send('PUT', path, data)

    def post(self, path, data=None):
        return self.send('POST', path, data)

    def delete(self, path, data=None):
        return self.send('DELETE', path, data)

    @staticmethod
    def linode_argument_spec():
        return dict(
            validate_certs=dict(type='bool', required=False, default=True),
            oauth_token=dict(
                no_log=True,
                # Support environment variable for Linode Personal Access Token
                fallback=(env_fallback, ['LINODE_API_TOKEN', 'LINODE_API_KEY']),
                required=False,
            ),
            timeout=dict(type='int', default=30),
        )


class LinodeLegacyHelper(LinodeV4Helper):

    def __init__(self, module):
        self.module = module
        self.baseurl = 'https://api.linode.com'
        self.oauth_token = None

        # Check if api_token is valid or not
        response = self.get(data={ 'api_action': 'account.info' })
        if len(response.json['ERRORARRAY']) != 0:
            module.fail_json(msg='Failed to login using legacy API token, please verify validity of legacy API token.')

        self.timeout = module.params.get('timeout', 30)

    def _url_builder(self, data):
        data['api_key'] = self.oauth_token
        try:
            # python3
            encoded_bits = '&'.join([
                "{}={}".format(k, v) for (k, v) in data.items()
                ])
        except AttributeError:
            # python2
            encoded_bits = '&'.join([
                "{}={}".format(k, v) for (k, v) in data.iteritems()
                ])

        builder = ParseResult(
                scheme='https',
                netloc='api.linode.com',
                path='/',
                params='',
                query=encoded_bits,
                fragment=''
        )
        return urlunparse(builder)

    def send(self, method, path, data=None):
        url = self._url_builder(data)

        # data set to None since the important bits are packed into the url
        # argument
        resp, info = fetch_url(self.module, url, data=None, method=method, timeout=self.timeout)

        return Response(resp, info)

    def get(self, path, data=None):
        return self.send('GET', None, data)

    def put(self, path, data=None):
        '''
        All methods in the legacy API are GET's
        '''
        return NotImplementedError

    def post(self, path, data=None):
        '''
        All methods in the legacy API are GET's
        '''
        return NotImplementedError

    def delete(self, path, data=None):
        '''
        All methods in the legacy API are GET's
        '''
        return NotImplementedError
