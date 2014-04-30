#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <arne-neumann@web.de>

"""
The C{realization} module shall take HLDS XML structures, realize them with
the OpenCCG surface realizer and parse its output string.
"""

import os
import re
import pexpect
import time
from tempfile import NamedTemporaryFile
from commands import getstatusoutput
from copy import deepcopy

from hlds import (Diamond, Sentence, diamond2sentence, add_nom_prefixes,
                  create_hlds_file)


if __name__ == '__main__':
    GRAMMAR_DIR = 'grammar'
else:
    GRAMMAR_DIR = os.path.join(os.path.dirname(__file__), 'grammar')


class OpenCCG(object):
    """
    command-line interaction with OpenCCG's I{tccg} parser/generator, which
    can either be run as a JSON-RPC server or simply imported as a Python
    module.
    """
    def __init__(self, grammar_dir=GRAMMAR_DIR):
        """
        spawns the OpenCCG/tccg server as a process

        Parameters
        ----------
        grammar_dir : path to the directory that contains the grammar
        """
        current_dir = os.getcwd()
        grammar_path = GRAMMAR_DIR
        tccg_binary = "tccg"

        os.chdir(grammar_path)
        self._server = pexpect.spawn(tccg_binary)
        print "starting tccg as a server with this path: %s" % tccg_binary
        os.chdir(current_dir)
        print "checking tccg settings ..."
        self._server.expect("\ntccg>") # wait for the tccg input prompt
        print "Okay, here you go."
        print "current settings:\n{0}".format(self.parse(":sh"))

    def parse(self, text, verbose=True, raw_output=True):
        """
        This is the core interaction with the parser. 

        It returns a Python data-structure, while the parse()
        function returns a JSON object
        
        @return: if raw_output=True, the raw response string from the server 
        will be returned. otherwise, a list of dictionaries will be returned 
        (one for each input sentence).
        @rtype: C{str} OR C{list} of C{dict}s
        """
        # clean up anything leftover
        while True:
            try:
                # the second argument is a forced delay (in seconds)
                # EVERY parse must incur.  
                # TODO make this as small as possible.
                ch = self._server.read_nonblocking (4000, 3) #originally: 0.3s
            except pexpect.TIMEOUT:
                break

        self._server.sendline(text)
        # How much time should we give the parser to parse it?
        max_expected_time = 20.0
        if verbose:
            print "Timeout", max_expected_time
        end_time = time.time() + max_expected_time 
        incoming = ""
        while True: 
            # Time left, read more data
            try:
                ch = self._server.read_nonblocking (2000, 2)
                freshlen = len(ch)
                time.sleep (0.0001)
                incoming = incoming + ch
                if "\ntccg>" in incoming:
                    break
            except pexpect.TIMEOUT:
                if verbose:
                    print "Timeout" 
                if end_time - time.time() < 0:
                    return {'error': "timed out after %f seconds" % max_expected_time, 
                            'input': text,
                            'output': incoming}
                else:
                    continue
            except pexpect.EOF:
                break

        if raw_output == True: # plain text results returned by I{tccg}
            return incoming

        else: # return parsed results
            return "I can't parse tccg's output, yet!"

    def realize(self, featstruct, raw_output=True):
        """
        converts a C{Diamond} or C{Sentence} feature structure into HLDS-XML,
        write it to a temporary file, realizes this file with I{tccg} and
        parses the output it returns.

        @type featstruct: C{Diamond} or C{Sentence}
        """
        temp_sentence = deepcopy(featstruct)
        
        if isinstance(featstruct, Diamond):
            temp_sentence = diamond2sentence(temp_sentence)

        add_nom_prefixes(temp_sentence)
        sentence_xml_str = create_hlds_file(temp_sentence, mode="realize",
                                            output="xml")
    
        tmp_file = open("pypolibox-tccg.tmp", "w")
        tmp_file.write(sentence_xml_str)
        tmp_file.close()
        tmp_file_path = os.path.abspath(tmp_file.name)
        self.tccg_output = self.realize_hlds(tmp_file_path)
        #os.remove(tmp_file_path)
        return parse_tccg_generator_output(self.tccg_output)

    def realize_hlds(self, hlds_xml_filename):
        tccg_command_string = ":r {0}".format(hlds_xml_filename)
        return self.parse(tccg_command_string, verbose=False)

    def terminate(self):
        self._server.terminate()


def parse_tccg_generator_output(tccg_output):
    """
    parses the output string returned from tccg's interactive generator
    shell.
    """
    results = []
    output_lines = tccg_output.splitlines()[1:-1] #remove 1st + last line
    result_regex = re.compile("\[\d\.\d+\] (.*?) :-")
    for line in output_lines:
        match = result_regex.match(line)
        if match:
            results.append(match.groups()[0])
        else:
            raise Exception, "Can't parse tccg output line:\n{0}".format(line)
    return sorted(set(results))
