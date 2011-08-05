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
            tree = etree.fromstring(hlds)
            self.parse_sentences(tree)
            
        elif input_format == "file":
            tree = etree.parse(hlds)
            self.parse_sentences(tree)
            
    def parse_sentences(self, tree):
        """
        parses all sentences (represented as HLDS XML <item> structures) into 
        feature structures.
        
        @param tree: an etree tree element
        
        A sentence is represented as an <item> structure in HLDS::
        
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

        self.xml_sentences = tree.findall("item")
        self.sentences = []
        
        for sentence in self.xml_sentences:
            root = sentence.find("xml/lf/satop") # root (verb) of the sentence
            
            # <item numOfParses="4" string="er beschreibt sie">
            sentence_string = ensure_utf8(sentence.attrib["string"])
            expected_parses = sentence.attrib["numOfParses"]

            # <satop nom="b1:handlung">
            #   <prop name="beschreiben"/>
            root_name = root.find("prop").attrib["name"]
            root_id = root.attrib["nom"]
            elements = []
            
#            raw_diamonds = [] # TODO: remove after debugging
            for index, element in enumerate(root.findall("diamond")):
                #self.indentation += 1
                #self.parse_diamond(element)
                #self.indentation -= 1
#                raw_diamonds.append(element) # TODO: remove after dbg
                diamond = DiamondFS(element)
                elements.append(diamond)

            sentence_tuple = (sentence_string, expected_parses, root_name, 
                              root_id, elements)
            parsed_sentence = SentenceFS(sentence_tuple)
            self.sentences.append(parsed_sentence)
            
    #def parse_diamond(self, diamond):
        #"""
        #diamonds are recursive structures...
        #"""
        #children = diamond.getchildren()
        #print "  " * self.indentation, \
              #"[element] %s" % (diamond.attrib["mode"])
        
        #for child in children:
            #if child.tag == "diamond":
                #self.indentation += 2
                #self.parse_diamond(child)
                #self.indentation -= 2
            #else:    
                #print "  " * int(self.indentation+2), \
                      #"%s %s" % (child.tag, child.attrib["name"])

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

class SentenceFS(FeatDict):
    """
    represents a sentence in HLDS notation as a feature structure.
    
    TODO: rewrite __new__() to accept more than one parameter. Since 
    C{SentenceFS} inherits its features from C{FeatDict}, we can't feed as 
    many parameters to __init__() as we'd like to
    """
    def __init__(self, sent_tuple):
        sent_str, expected_parses, root_name, root_id, elements = sent_tuple            
        self.update({Feature("text"): sent_str})
        self.update({Feature("expected_parses"): int(expected_parses)})
        self.update({Feature("root_name"): root_name}) 
        self.update({Feature("root_id"): root_id})
        
        for element in elements: # these are C{DiamondFS}s
            self.update({Feature("mode"): element})
    
        
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
        self[Feature('mode')] = ensure_utf8(diamond.attrib["mode"])
        
        for child in diamond.getchildren():
            if child.tag == "diamond":
                nested_diamond = DiamondFS(child)
                self.update({nested_diamond[Feature("mode")]: nested_diamond})

            else: # children with .tag 'nom' or 'prop'
                child_tag = ensure_utf8(child.tag)
                child_name = ensure_utf8(child.attrib["name"])
                self.update({child_tag: child_name})
 
        
if __name__ == "__main__":
    hlds = HLDSReader(TEST, input_format="file")
