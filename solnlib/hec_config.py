import solnlib.splunk_rest_client as rest_client

__all__ = ['HECConfig']


class HECConfig(object):
    '''
    HTTP Event Collector configuration
    '''

    input_type = 'http'

    def __init__(self, session_key, scheme=None,
                 host=None, port=None, **context):
        self._rest_client = rest_client.SplunkRestClient(
            session_key,
            'splunk_httpinput',
            scheme=scheme,
            host=host,
            port=port,
            **context)

    def get_settings(self):
        '''Get http data input global settings
        :returns: http global setting like: {
            'enableSSL': 1,
            'disabled': 0,
            'useDeploymentServer': 0,
            'port': 8088,
            'output_mode': 'json',
        }
        :rtype: dict
        :raises exception if error happen
        '''

        return self._do_get_input(self.input_type).content

    def update_settings(self, settings):
        '''Update http data input global settings

        :param settings: http global setting like: {
            'enableSSL': 1,
            'disabled': 0,
            'useDeploymentServer': 0,
            'port': 8088,
            'output_mode': 'json',
        }
        :raises exception if error happen
        '''

        res = self._do_get_input(self.input_type)
        res.update(**settings)

    def create_input(self, name, stanza):
        '''Create http data input
        :param name: http data input name,
        :type name: ``string``
        :param stanza: Data input stanza content which should not contain 'name' key, like: {
            'index': 'main'
            'sourcetype': 'akamai:cm:json'
            'token': 'A0-5800-406B-9224-8E1DC4E720B6'}
        :type stanza: ``dict``
        :returns: dict object like: {
            'index': 'main',
            'sourcetype': 'test',
            'host': 'Kens-MacBook-Pro.local',
            'token': 'A0-5800-406B-9224-8E1DC4E720B7'
        }

        Usage::

           >>> from solnlib import HEConfig
           >>> hec = HECConfig(session_key)
           >>> hec.create_input('my_hec_data_input', {'index': 'main', 'sourcetype': 'hec'})
        '''

        res = self._rest_client.inputs.create(name, self.input_type, **stanza)
        return res.content

    def update_input(self, name, stanza):
        '''Update http data input, will create if the data input doesn't exist

        :name: http data input name
        :type name: ``string``
        :param stanza: Data input stanza which should not contain 'name' key, like:
        {
        'index': 'main'
        'sourcetype': 'akamai:cm:json'
        'token': 'A0-5800-406B-9224-8E1DC4E720B6'}
        :type stanza: ``dict``

        Usage::

           >>> from solnlib import HEConfig
           >>> hec = HECConfig(session_key)
           >>> hec.update_input('my_hec_data_input', {'index': 'main', 'sourcetype': 'hec2'})
        '''

        res = self._do_get_input(name)
        if res is None:
            return self.create_input(name, stanza)
        res.update(**stanza)

    def delete_input(self, name):
        '''
        :name: http data input name
        :type name: ``string``
        :returns: None when delete successfully or there is no such data input
        :raises exception if there are other errors
        '''

        try:
            self._rest_client.inputs.delete(name, self.input_type)
        except KeyError:
            return

    def get_input(self, name):
        '''
        :param name: http event collector data input name,
        :type param: ``string``
        :returns: http event collector data input config dict, like: {
            'disabled': '0',
            'index': 'main',
            'sourcetype': 'hec',
        } if successful. return None if there is no such data input
        :rtype: ``dict``

        :raises exception if other errors happened
        '''

        res = self._do_get_input(name)
        if res:
            return res.content
        else:
            return None

    def _do_get_input(self, name):
        try:
            return self._rest_client.inputs[(name, self.input_type)]
        except KeyError:
            return None

    def get_limits(self):
        '''Get http input limits

        :returns: dict object like: {
            'metrics_report_interval': '60',
            'max_content_length': '2000000',
            'max_number_of_acked_requests_pending_query': '10000000',
            ...
        }
        '''

        return self._rest_client.confs['limits']['http_input'].content

    def set_limits(self, limits):
        ''' Set http input limits

        :param limits: dict object which can contain: {
            'max_content_length': '3000000',
            'metrics_report_interval': '70',
            ...
        }
        '''

        res = self._rest_client.confs['limits']['http_input']
        res.submit(limits)
