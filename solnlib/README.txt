
Changes in conf_manager.py in v1.0.17: (ADDON-18553)(APPSC-2429)

    In UCC built app, To distinguish encrypted passwords, different REALMs are generated like below format:

    [credential:__REST_CREDENTIAL__#Splunk_TA_test#configs/conf-CONF_FILENAME:STANZA_NAME``splunk_cred_sep``1:]

    In this scenario, 'conf_manager' will fail while searching for passwords as it expects REALM to be simply APP_NAME.
    So, this fix will add support to read encrypted passwords using REALMs other than APP_NAME.

    If conf file is created using splunktaucclib:
        >>> from solnlib import conf_manager
        >>> cfm = conf_manager.ConfManager(session_key,
                                           'Splunk_TA_test', realm='REALM')

        EXAMPLE:
            If stanza in passwords.conf is formatted as below:

            [credential:__REST_CREDENTIAL__#Splunk_TA_test#configs/conf-CONF_FILENAME:STANZA_NAME``splunk_cred_sep``1:]

            >>> from solnlib import conf_manager
            >>> cfm = conf_manager.ConfManager(session_key,
                                               'Splunk_TA_test', realm='__REST_CREDENTIAL__#Splunk_TA_test#configs/conf-CONF_FILENAME')
