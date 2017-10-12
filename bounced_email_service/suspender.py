import requests
from urllib.parse import quote
from uritemplate import URITemplate
from cachecontrol import CacheControl


class BaseSuspender(object):
    def __init__(self, config):
        self.config = config


class XikoloSuspender(BaseSuspender):
    mydomains = ['openhpi.de', 'opensap.info']

    def __init__(self, config):
        super(XikoloSuspender, self).__init__(config)
        self.cached_session = CacheControl(requests.session())

    def suspend(self, bounced_address):
        r = self.cached_session.get(self.config['base_url'])
        uri = r.json()['email_suspensions_url']

        tpl = URITemplate(uri)
        endpoint = tpl.expand(address=quote(bounced_address, safe=''))

        return self.cached_session.post(endpoint, data={}).status_code


class DefaultSuspender(BaseSuspender):
    mydomains = ['mydomain.de']

    def suspend(self, bounced_address):
        r = requests.put(
            self.config['endpoint'],
            data={'email_address': bounced_address})

        return r.status_code

