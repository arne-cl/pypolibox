#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <arne-neumann@web.de>

"""
HLDS (Hybrid Logic Dependency Semantics) is the format internally used by the 
OpenCCG realizer. This module shall allow the conversion between HLDS-XML 
files and Python data structures.
"""

from lxml import etree
from util import ensure_utf8

TEST = "testbedHLDS.xml" #TODO: remove after debugging

class HLDSReader():
    """
    """
    def __init__(self, hlds, input_format="file"):
        self.indentation = -2

        if input_format == "string":
            self.tree = etree.fromstring(hlds)
            self.parse_sentences()
            
        elif input_format == "file":
            self.tree = etree.parse(hlds)
            self.parse_sentences()
            
    def parse_sentences(self):
        self.test_sentences = self.tree.findall("item")
        self.sentences = []
        
        for sentence in self.test_sentences:
            root = sentence.find("xml/lf/satop") # root (verb) of the sentence
            sentence_string = ensure_utf8(sentence.attrib["string"])
            expected_parses = sentence.attrib["numOfParses"]
            root_name = root.find("prop").attrib["name"]
            root_id = root.attrib["nom"]
            elements = []
            
            #print "sentence: %s" % (sentence_string)
            #print "expected parses: %s" % (expected_parses)
            #print "root name: %s" % (root_name)
            #print "root id: %s" % (root_id)
            
            for index, element in enumerate(root.findall("diamond")):
                #self.indentation += 1
                #self.parse_diamond(element)
                #self.indentation -= 1
                diamond = Diamond(element)
                elements.append(diamond)
                
#            print "+++++++++++++++++\n\n"
            
            parsed_sentence = Sentence(sentence_string, expected_parses, 
                                       root_name, root_id, elements)
            self.sentences.append(parsed_sentence)
            
    def parse_diamond(self, diamond):
        """
        diamonds are recursive structures...
        """
        children = diamond.getchildren()
        print "  " * self.indentation, \
              "[element] %s" % (diamond.attrib["mode"])
        
        for child in children:
            if child.tag == "diamond":
                self.indentation += 2
                self.parse_diamond(child)
                self.indentation -= 2
            else:    
                print "  " * int(self.indentation+2), \
                      "%s %s" % (child.tag, child.attrib["name"])

class Sentence():
    """
    represents a test sentence in HLDS notation for OpenCCG regression tests.
    """
    def __init__(self, sentence_string, expected_parses, root_name, root_id, 
                 elements):
        self.text = sentence_string
        self.expected_parses = int(expected_parses)
        self.root_name = root_name
        self.root_id = root_id
        self.elements = elements
    
class Diamond():
    """
    represents a HLDS diamond
    """    
    def __init__(self, diamond_etree_element):
        self.mode = diamond_etree_element.attrib["mode"]
        self.elements = []
        
        for child in diamond_etree_element.getchildren():
            if child.tag == "diamond":
                diamond = Diamond(child)
                self.elements.append(diamond)
            else:
                setattr(self, child.tag, child.attrib["name"])
        
        if len(self.elements) == 0: # if there are no nested diamonds
            del self.elements
        
    def __str__(self):
        ret_str = ""
        for (key, value) in self.__dict__.items():
            ret_str += "{0}: {1}\n".format(ensure_utf8(key), 
                                           ensure_utf8(value))
        return ret_str
        
        
if __name__ == "__main__":
    hlds = HLDSReader(TEST, input_format="file")
