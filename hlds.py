#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <arne-neumann@web.de>

"""
HLDS (Hybrid Logic Dependency Semantics) is the format internally used by the 
OpenCCG realizer. This module shall allow the conversion between HLDS-XML 
files and Python data structures.
"""

from nltk.featstruct import Feature, FeatDict
from lxml import etree
from util import ensure_utf8

TEST = "testbedHLDS.xml" #TODO: remove after debugging

class HLDSReader():
    """
    represents a list of sentences parsed from a testbed file
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
        """
        A sentence is represented as an <item> structure::
        
            <item numOfParses="4" string="er beschreibt sie">
                <xml>
                    <lf>
                        <satop nom="b1:handlung">
                            <prop name="beschreiben"/>
                            <diamond mode="TEMP">
                                <prop name="präs"/>
                            </diamond>
                            <diamond mode="AGENS">
                                <nom name="x1:sem-obj"/>
                                <diamond mode="PRO">
                                    <prop name="perspro"/>
                                </diamond>
                                <diamond mode="GEN">
                                    <prop name="mask"/>
                                </diamond>
                                <diamond mode="PERS">
                                    <prop name="3te"/>
                                </diamond>
                                <diamond mode="NUM">
                                    <prop name="sing"/>
                                </diamond>
                            </diamond>
                            <diamond mode="PATIENS">
                                <nom name="x2:sem-obj"/>
                                <diamond mode="PRO">
                                    <prop name="perspro"/>
                                </diamond>
                                <diamond mode="GEN">
                                    <prop name="fem"/>
                                </diamond>
                                <diamond mode="PERS">
                                    <prop name="3te"/>
                                </diamond>
                                <diamond mode="NUM">
                                    <prop name="sing"/>
                                </diamond>
                            </diamond>
                        </satop>
                    </lf>
                    <!--<target>er beschreibt sie</target>-->
                </xml>
            </item>
        """

        self.test_sentences = self.tree.findall("item")
        self.sentences = []
        
        for sentence in self.test_sentences:
            root = sentence.find("xml/lf/satop") # root (verb) of the sentence
            
            # <item numOfParses="4" string="er beschreibt sie">
            sentence_string = ensure_utf8(sentence.attrib["string"])
            expected_parses = sentence.attrib["numOfParses"]

            # <satop nom="b1:handlung">
            #   <prop name="beschreiben"/>
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
    represents a HLDS diamond. Each diamond has an attribute 'mode' and a 
    'prop' child. Additionally, a diamond can have a 'nom' child and any 
    number 'diamond' children.
    
        <diamond mode="AGENS">
            <nom name="s1:addition"/>
            <prop name="sowohl"/>
            <diamond mode="NP1">
                <nom name="h1:nachname"/>
                <prop name="Hausser"/>
            </diamond>
            ...
        </diamond>
    """    
    def __init__(self, diamond_etree_element):
        self.mode = diamond_etree_element.attrib["mode"]
        self.elements = []
        
        for child in diamond_etree_element.getchildren():
            if child.tag == "diamond":
                diamond = Diamond(child)
                self.elements.append(diamond)
            else: # children with .tag 'nom' or 'prop'
                setattr(self, child.tag, child.attrib["name"])
        
        if len(self.elements) == 0: # if there are no nested diamonds
            del self.elements
        
    def __str__(self):
        ret_str = ""
        for (key, value) in self.__dict__.items():
            ret_str += "{0}: {1}\n".format(ensure_utf8(key), 
                                           ensure_utf8(value))
        return ret_str
        
class DiamondFS(FeatDict):
    """
    A {DiamondFS} represents an HLDS diamond in form of a (nested) feature 
    structure. 

        <diamond mode="AGENS">
            <nom name="s1:addition"/>
            <prop name="sowohl"/>
            <diamond mode="NP1">
                <nom name="h1:nachname"/>
                <prop name="Hausser"/>
            </diamond>
            ...
        </diamond>
    """
    def __init__(self, diamond):
        """
        @param diamond: a diamond etree element
        """
        self[Feature('mode')] = diamond.attrib["mode"]
        self.nested_diamonds = []
        
        for child in diamond.getchildren():
            if child.tag == "diamond":
                diamond = DiamondFS(child)
                self.nested_diamonds.append(diamond)
            else: # children with .tag 'nom' or 'prop'
                #setattr(self, child.tag, child.attrib["name"])
                self.update({child.tag: child.attrib["name"]})
        
        if len(self.nested_diamonds) == 0:
            del self.nested_diamonds
        
    #def __str__(self):
        #ret_str = ""
        #for (key, value) in self.__dict__.items():
            #ret_str += "{0}: {1}\n".format(ensure_utf8(key), 
                                           #ensure_utf8(value))
        #return ret_str


 
        
if __name__ == "__main__":
    hlds = HLDSReader(TEST, input_format="file")
