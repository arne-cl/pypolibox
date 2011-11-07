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

from util import load_settings
from hlds import (Diamond, Sentence, diamond2sentence, add_nom_prefixes,
                  create_hlds_file)


SETTINGS = load_settings()


class OpenCCG(object):
    """
    command-line interaction with OpenCCG's I{tccg} parser/generator, which
    can either be run as a JSON-RPC server or simply imported as a Python
    module.
    """
    def __init__(self, SETTINGS):
        """
        spawns the OpenCCG/tccg server as a process

        @param SETTINGS: the content of the settings file pypolibox.yml
        """
        current_dir = os.getcwd()
        openccg_bin_path = SETTINGS["OPENCCG_BIN_PATH"]
        grammar_path = SETTINGS["GRAMMAR_PATH"]
        tccg_binary = os.path.join(openccg_bin_path, "tccg")

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
        # the idea here is that you increase the timeout as a 
        # function of the text's length.
        
        # anything longer than 5 seconds requires that you also
        # increase timeout=5 in jsonrpc.py
        max_expected_time = 20.0
        #max_expected_time = min(10, 3 + len(text) / 20.0)
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

        if raw_output == True: # plain text results returned by CoreNLP
            return incoming

        else: # return parsed results
            return "I can't parse tccg's output, yet!"

    def realize(self, featstruct, raw_output=True):
        """
        convert featstruct to hlds-xml,
        write xml to tempfile,
        realize tempfile from within tccg w/ 'r: /path/to/tempfile',
        get tccg output via pexpect.read_nonblocking,
        parse output

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
    parses the output string returned from tccg's interactive generator shell
    """
    results = []
    output_lines = tccg_output.splitlines()[1:-1] #remove 1st + last line
    result_regex = re.compile("{\d\.\d+} \[\d\.\d+\] (.*?) :-")
    for line in output_lines:
        match = result_regex.match(line)
        if match:
            results.append(match.groups()[0])
        else:
            raise Exception, "Can't parse tccg output line:\n{0}".format(line)
    return sorted(set(results))


### realize() opens a new instance of ccg-realize for EVERY query! please use
### OpenCCG.realize() instead

#~ def realize(sentence, results="all"):
    #~ """
    #~ realizes a sentence by calling OpenCCG's I{ccg-realize} binary.
#~ 
    #~ @type sentence: C{str} or C{Diamond} or C{Sentence}
    #~ @param sentence:
     #~ - a string: the path to an HLDS XML sentence file (absolute path or
       #~ relative to GRAMMAR_PATH)
     #~ - a Diamond instance
     #~ - a Sentence instance
#~ 
    #~ @type results: C{str}
    #~ @param results:
    #~ - "debug": return the raw results from ccg-realize
    #~ - "all": return all strings that ccg-realize could produce ("Complete
      #~ Edges")
    #~ - "best": return only the best result from ccg-realize ("Best Edge")
#~ 
    #~ @rtype: C{str} or C{list} of C{str}
    #~ @return: a string (the "best" result from OpenCCG) OR a list of string,
    #~ containing "all" results that could be realized by OpenCCG
    #~ """
    #~ current_dir = os.getcwd()
#~ 
    #~ try:
        #~ os.chdir(SETTINGS["GRAMMAR_PATH"])
        #~ grammar_abspath = os.getcwd()
        #~ realizer = os.path.join(SETTINGS["OPENCCG_BIN_PATH"], "ccg-realize")
    #~ 
        #~ if isinstance(sentence, str): # sentence is a file path
            #~ status, output = __realize_from_file(sentence, grammar_abspath, 
                                                 #~ realizer)
    #~ 
        #~ elif isinstance(sentence, Diamond):
            #~ temp_sentence = deepcopy(sentence)
            #~ temp_sentence = diamond2sentence(temp_sentence)
            #~ status, output = __realize_from_sentence_fs(temp_sentence, 
                                                        #~ realizer)
            #~ 
        #~ elif isinstance(sentence, Sentence):
            #~ temp_sentence = deepcopy(sentence)
            #~ status, output = __realize_from_sentence_fs(temp_sentence, 
                                                        #~ realizer)
            #~ 
        #~ else:
            #~ status = -1
            #~ output = "Sorry, I can only realize HLDS XML sentence files," \
                     #~ " Sentence and Diamond instances. " \
                     #~ "Your input has this type: " \
                     #~ "{0} and looks like this:\n{1}".format(type(sentence), 
                                                            #~ sentence)
    #~ finally: #NEVER ever stay in the openccg directory
        #~ os.chdir(current_dir)
#~ 
    #~ if status == 0: # OpenCCG didn't return any errors
        #~ return __parse_ccg_output(output, results)
    #~ else:
        #~ raise Exception, "Error: Can't run ccg-realize properly. " \
            #~ "The error message is:\n\n{0}".format(output)
#~ 
#~ 
#~ def __realize_from_file(file_name, grammar_abspath, realizer):
    #~ """
    #~ loads an HLDS XML sentence from a file and realizes it with I{ccg-realize}.
    #~ """
    #~ file_path = os.path.join(grammar_abspath, file_name)
    #~ if os.path.isfile(file_path):
        #~ status, output = getstatusoutput("{0} {1}".format(realizer,
                                                          #~ file_path))
    #~ else:
        #~ status = -1
        #~ output = "{0} is not a file.\n" \
            #~ "Please use an absolute path or one that is relative to:\n" \
            #~ "{1}".format(file_path, grammar_abspath)
    #~ return status, output
#~ 
#~ 
#~ def __realize_from_sentence_fs(sentence, realizer):
    #~ """
    #~ realizes a C{Sentence} with I{ccg-realize}.
    #~ 
    #~ @type sentence: C{Sentence}
    #~ @type realizer: C{str}
    #~ @param realizer: path to ccg-realizer executable
    #~ """
    #~ add_nom_prefixes(sentence)
    #~ sentence_xml_str = create_hlds_file(sentence, mode="realize", output="xml")
#~ 
    #~ tmp_file = NamedTemporaryFile(mode="w", delete=False)
    #~ tmp_file.write(sentence_xml_str)
    #~ tmp_file.close()
#~ 
    #~ status, output = getstatusoutput("{0} {1}".format(realizer, tmp_file.name))
    #~ return status, output
#~ 
#~ 
#~ def __parse_ccg_output(output, results="all"):
    #~ """ 
    #~ parses the output of I{ccg-realize} and returns the sentence strings 
    #~ that it could produce.
    #~ 
    #~ NOTE: if parsing should fail, try to reset I{OpenCCG} settings by 
    #~ calling I{tccg} and entering I{:reset}.
    #~ 
    #~ @type output: C{str}
    #~ @param output: the output string that I{ccg-realize} returned
    #~ 
    #~ @type results: C{str}
    #~ @param results:
    #~ - "debug": return the raw results from ccg-realize
    #~ - "all": return all strings that ccg-realize could produce ("Complete
      #~ Edges")
    #~ - "best": return only the best result from ccg-realize ("Best Edge")    
    #~ """
    #~ if results == "debug":
        #~ return output
        #~ 
    #~ res = re.compile("Complete Edges \(sorted\):\n")
    #~ complete_vs_best = re.compile("\nBest Edge:\n")
    #~ sentence_header = re.compile("\{.*?\} \[.*?\] ")
    #~ sentence_tail = re.compile(" :- ")
#~ 
    #~ _, results_str = res.split(output)
    #~ complete_edges_str, best_edge = complete_vs_best.split(results_str)
#~ 
    #~ if not complete_edges_str: #if there are no complete edges
        #~ best_vs_best_joined = re.compile("\nBest Joined Edge:\n")
        #~ best_edge, best_joined = best_vs_best_joined.split(best_edge)
#~ 
    #~ if results == "best":
        #~ _, best_edge_and_tail = sentence_header.split(best_edge)
        #~ best_result, _ = sentence_tail.split(best_edge_and_tail)
        #~ return best_result
#~ 
    #~ elif results == "all":
        #~ if complete_edges_str:
            #~ complete_edges_list = complete_edges_str.splitlines()
            #~ result_edges = []
            #~ for complete_edge in complete_edges_list:
                #~ # maxsplit=1 is needed if there are 'Best Joined Edges'
                #~ _, edge_and_tail = sentence_header.split(complete_edge,
                                                         #~ maxsplit=1)
                #~ edge, _ = sentence_tail.split(edge_and_tail, maxsplit=1)
                #~ result_edges.append(edge)
            #~ return sorted(list(set(result_edges)))
            #~ # remove duplicates, return a sorted list
        #~ else:
            #~ # if there are no complete edges
            #~ _, best_edge_and_tail = sentence_header.split(best_edge)
            #~ best_edge_result, _ = sentence_tail.split(best_edge_and_tail)
            #~ _, best_joined_and_tail = sentence_header.split(best_joined)
            #~ best_joined_result, _ = sentence_tail.split(best_joined_and_tail)
            #~ return sorted([best_edge_result, best_joined_result])
#~ 
