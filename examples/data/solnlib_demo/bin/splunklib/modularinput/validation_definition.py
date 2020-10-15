# Copyright 2011-2015 Splunk, Inc.
# SPDX-FileCopyrightText: 2020 2020
#
# SPDX-License-Identifier: Apache-2.0

try:
    import xml.etree.cElementTree as ET
except ImportError as ie:
    import xml.etree.ElementTree as ET

from utils import parse_xml_data


class ValidationDefinition(object):
    """This class represents the XML sent by Splunk for external validation of a
    new modular input.

    **Example**::

    ``v = ValidationDefinition()``

    """
    def __init__(self):
        self.metadata = {}
        self.parameters = {}

    def __eq__(self, other):
        if not isinstance(other, ValidationDefinition):
            return False
        return self.metadata == other.metadata and self.parameters == other.parameters

    @staticmethod
    def parse(stream):
        """Creates a ``ValidationDefinition`` from a provided stream containing XML.

        The XML typically will look like this:

        ``<items>``
        ``   <server_host>myHost</server_host>``
        ``     <server_uri>https://127.0.0.1:8089</server_uri>``
        ``     <session_key>123102983109283019283</session_key>``
        ``     <checkpoint_dir>/opt/splunk/var/lib/splunk/modinputs</checkpoint_dir>``
        ``     <item name="myScheme">``
        ``       <param name="param1">value1</param>``
        ``       <param_list name="param2">``
        ``         <value>value2</value>``
        ``         <value>value3</value>``
        ``         <value>value4</value>``
        ``       </param_list>``
        ``     </item>``
        ``</items>``

        :param stream: ``Stream`` containing XML to parse.
        :return definition: A ``ValidationDefinition`` object.

        """

        definition = ValidationDefinition()

        # parse XML from the stream, then get the root node
        root = ET.parse(stream).getroot()

        for node in root:
            # lone item node
            if node.tag == "item":
                # name from item node
                definition.metadata["name"] = node.get("name")
                definition.parameters = parse_xml_data(node, "")
            else:
                # Store anything else in metadata
                definition.metadata[node.tag] = node.text

        return definition