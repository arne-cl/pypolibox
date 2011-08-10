#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <arne-neumann@web.de>

"""
HLDS (Hybrid Logic Dependency Semantics) is the format internally used by the 
OpenCCG realizer. This module shall allow the conversion between HLDS-XML 
files and NLTK feature structures.

Sentences are represented as <item> structures in HLDS::
        
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
                        ...
                    </diamond>
                    <diamond mode="PATIENS">
                        <nom name="x2:sem-obj"/>
                        <diamond mode="PRO">
                            <prop name="perspro"/>
                        </diamond>
                        ...
                    </diamond>
                </satop>
            </lf>
            <!--<target>er beschreibt sie</target>-->
        </xml>
    </item>
"""

import random
from nltk.featstruct import Feature, FeatDict
from lxml import etree
from lxml.builder import ElementMaker
from util import ensure_utf8, ensure_unicode

testbed_file = "testbedHLDS.xml"

class HLDSReader():
    """ 
    represents a list of sentences (as NLTK feature structures) parsed from 
    an HLDS XML testbed file.
    """
    def __init__(self, hlds, input_format="file"):
        """
        @type hlds: C{str} or C{file}
        @param hlds: an HLDS XML testbed file (either a file object or a 
        string, depending on the input_format parameter)
        
        @type input_format: C{str}
        @param input_format: "string" or "file"
        """
        self.sentences = []
        
        if input_format == "string":
            tree = etree.fromstring(hlds)
            self.parse_sentences(tree)
            
        elif input_format == "file":
            tree = etree.parse(hlds)
            self.parse_sentences(tree)
        
    def parse_sentences(self, tree):
        """
        Parses all sentences (represented as HLDS XML <item> structures) 
        into feature structures. These structures are saved as a list of 
        C{Sentence}s in self.sentences.
        
        @type tree: C{etree._ElementTree}
        @param tree: an etree tree element
        """
        self.xml_sentences = tree.findall("item")
        
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
            
            for element in root.findall("diamond"):
                diamond = Diamond(element)
                elements.append(diamond)

            sentence_tuple = (sentence_string, expected_parses, root_name, 
                              root_id, elements)
            parsed_sentence = Sentence(sentence_tuple)
            self.sentences.append(parsed_sentence)
            

class Sentence(FeatDict):
    """
    represents an HLDS sentence as an NLTK feature structure.
    
    TODO: rewrite __new__() to accept more than one parameter. Since 
    C{Sentence} inherits its features from C{FeatDict}, we can't feed as 
    many parameters to __init__() as we'd like to.
    """
    def __init__(self, sent_tuple):
        """         
        __init__ wraps all C{Diamond}s that were already constructed by 
        HLDSReader.parse_sentences() plus some meta data (root verb etc.) 
        into a NLTK feature structure that represents a complete sentence.
                
        @type sent_tuple: C{tuple} of (C{str}, C{int}, C{str}, C{str}, 
        C{list}), where C{list} contains C{Diamond}s
        
        @param sent_tuple: a 5-tuple containing the text that should be 
        generated (C{str}), the expected number of parses (C{int}), the 
        root verb of that sentence (root_name: C{str}), the root (verb) 
        category (root_id: C{str}, e.g. "b1:handlung") and a list of the 
        diamonds that are contained in the sentence (elements: C{list} of 
        C{Diamond}s). 
        
        TODO: rewrite __new__(), so we don't have to put all those 
        parameters into one tuple.                
        """
        sent_str, expected_parses, root_name, root_id, elements = sent_tuple
        self.update({Feature("text"): sent_str})
        self.update({Feature("expected_parses"): int(expected_parses)})
        self.update({Feature("root_name"): root_name}) 
        self.update({Feature("root_id"): root_id})
        
        for element in elements: # these are C{Diamond}s
            self.update({element[Feature("mode")]: element})
    
        
class Diamond(FeatDict):
    """
    A {Diamond} represents an HLDS diamond in form of a (nested) feature 
    structure containing the elements nom? prop? diamond* ::

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
        __init__ transforms a HLDS XML <diamond>...</diamond> structure 
        (that was parsed into an etree element) into an NLTK feature structure.
        
        @type diamond: C{etree._Element}
        @param diamond: a diamond etree element
        """
        self[Feature('mode')] = ensure_utf8(diamond.attrib["mode"])
        
        for child in diamond.getchildren():
            if child.tag == "diamond":
                nested_diamond = Diamond(child)
                self.update({nested_diamond[Feature("mode")]: nested_diamond})

            else: # children with .tag 'nom' or 'prop'
                child_tag = ensure_utf8(child.tag)
                child_name = ensure_utf8(child.attrib["name"])
                self.update({child_tag: child_name})

 
def create_hlds_testbed(sentence_list, output="etree"):
    """
    this function transforms C{Sentence}s into a a valid HLDS XML testbed file
    
    @type sentence_list: C{list} of C{Sentence}s
    @param sentence_list: a list of C{Sentence} feature structures
    
    @type output: C{str}
    @param output: "etree" (etree element) or "xml" (formatted, valid xml 
    document as a string)
    
    @rtype: C{str}
    """
    root = etree.Element("regression")
    doc = etree.ElementTree(root)
    
    etree_sentences = []
    for sentence in sentence_list:
        item = __sentence_fs2xml(sentence)
        etree_sentences.append(item)
    
    for sentence_tree in etree_sentences:
        final_position = len(root)
        root.insert(final_position, sentence_tree)
            
    if output == "etree":
        return doc
    elif output == "xml":
        return etree.tostring(doc, encoding="utf8", 
                              xml_declaration=True, pretty_print=True)

def __sentence_fs2xml(sentence):
    """    
    transforms a sentence (in NLTK feature structure notation) into its 
    corresponding HLDS XML <item></item> structure.
    
    @type sentence: C{Sentence}
    @param sentence: a sentence in NLTK feature structure notation
    
    @rtype: C{etree._Element}
    @return: the input sentence in HLDS XML format (represented as an etree 
    element)
    """
    expected_parses = sentence[Feature("expected_parses")]
    text = sentence[Feature("text")]
    
    item = etree.Element("item", numOfParses=str(expected_parses),
                         string=ensure_unicode(text))
    
    xml = etree.SubElement(item, "xml")
    lf = etree.SubElement(xml, "lf")
    
    root_id = sentence[Feature("root_id")]
    satop = etree.SubElement(lf, "satop", nom=root_id)
    
    root_name = sentence[Feature("root_name")]
    etree.SubElement(satop, "prop", name=root_name)
    
    diamonds = []
    for key, val in sentence.items():
        if type(val) is Diamond:
            diamonds.append(sentence[key])
    
    etree_diamonds = []
    for diamond in diamonds:
        etree_diamonds.append(__diamond_fs2xml(diamond))
        
    for diamond in etree_diamonds:
        final_position = len(diamond)
        satop.insert(final_position, diamond)
    
    return item
 
def __diamond_fs2xml(diamond):
    """
    converts a {Diamond} feature structure into its corresponding HLDS 
    XML structure (stored in an etree element).
    
    @type diamond: C{Diamond}
    @param diamond: a Diamond feature structure containing nom? prop? diamond* 
    elements
    
    @rtype: C{etree._Element}
    @return: a Diamond in HLDS XML tree notation, represented as an etree 
    element
    """
    E = ElementMaker()
    NOM = E.nom
    PROP = E.prop
    DIAMOND = E.diamond

    diamond_etree = DIAMOND(mode=ensure_unicode(diamond[Feature("mode")]))
    
    if "nom" in diamond:
        diamond_etree.insert(0, NOM(name=ensure_unicode(diamond["nom"])) )
    if "prop" in diamond:    
        diamond_etree.insert(0, PROP(name=ensure_unicode(diamond["prop"])) )
        
    subdiamonds = []    
    for key, value in diamond.items():
        if type(value) is Diamond:
            subdiamonds.append(diamond[key])
    
    etree_subdiamonds = []    
    for subdiamond in subdiamonds:
        etree_subdiamonds.append(__diamond_fs2xml(subdiamond))
        
    for subdiamond in etree_subdiamonds:
        final_position = len(subdiamond)
        diamond_etree.insert(final_position, subdiamond)
        
    return diamond_etree

def test_conversion():
    """    
    tests HLDS XML <-> NLTK feature structures conversions. converts an 
    HLDS XML testbed file into a list of sentences in NLTK feature 
    structure. picks one of these sentences randomly and converts it back 
    to HLDS XML. prints boths versions of this sentence. returns an 
    HLDSReader instance (containing a list of C{Sentence}s in NLTK feature 
    structure notation) and a HLDS XML testbed file (as a string) created 
    from those feature structures.
    
    @rtype: C{tuple} of (C{HLDSReader}, C{str}) 
    @return: a tuple containing an HLDSReader instance and a string 
    representation of an HLDS XML testbed file
    """
    hlds_reader = HLDSReader(testbed_file, input_format="file")
    random_sent_fs = \
        hlds_reader.sentences[random.randrange(0, len(hlds_reader.sentences))]
    random_sent_xml = create_hlds_testbed([random_sent_fs], output="xml")
    all_sents_xml = create_hlds_testbed(hlds_reader.sentences, output="xml")
                                              
    print random_sent_fs, "\n" * 3, random_sent_xml
    return hlds_reader, all_sents_xml 


def eprint(element):
    """pretty print function for etree trees or elements
    
    @type element: C{etree._ElementTree} or C{etree._Element}
    """
    print etree.tostring(element, pretty_print=True, encoding="utf8")
    
if __name__ == "__main__":
    fs_sents, xml_sents = test_conversion()
    
    
