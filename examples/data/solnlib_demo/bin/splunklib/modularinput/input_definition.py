# Copyright 2011-2015 Splunk, Inc.
# SPDX-FileCopyrightText: 2020 2020
#
# SPDX-License-Identifier: Apache-2.0

try:
    import xml.etree.cElementTree as ET
except ImportError as ie:
    import xml.etree.ElementTree as ET

from utils import parse_xml_data

class InputDefinition:
    """``InputDefinition`` encodes the XML defining inputs that Splunk passes to
    a modular input script.

     **Example**::

        i = InputDefinition()

    """
    def __init__ (self):
        self.metadata = {}
        self.inputs = {}

    def __eq__(self, other):
        if not isinstance(other, InputDefinition):
            return False
        return self.metadata == other.metadata and self.inputs == other.inputs

    @staticmethod
    def parse(stream):
        """Parse a stream containing XML into an ``InputDefinition``.

        :param stream: stream containing XML to parse.
        :return: definition: an ``InputDefinition`` object.
        """
        definition = InputDefinition()

        # parse XML from the stream, then get the root node
        root = ET.parse(stream).getroot()

        for node in root:
            if node.tag == "configuration":
                # get config for each stanza
                definition.inputs = parse_xml_data(node, "stanza")
            else:
                definition.metadata[node.tag] = node.text

        return definition