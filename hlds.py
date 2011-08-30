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

import sys
import re
import random
from collections import defaultdict
from lxml import etree
from lxml.builder import ElementMaker
from nltk.featstruct import Feature, FeatDict
from util import ensure_utf8, ensure_unicode, write_to_file

testbed_file = "openccg-jpolibox/testbedHLDS.xml"

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
        if input_format == "string":
            tree = etree.fromstring(hlds)
            self.parse_sentences(tree)
            
        elif input_format == "file":
            tree = etree.parse(hlds)
            self.parse_sentences(tree)
        
    def parse_sentences(self, tree):
        """
        Parses all sentences (represented as HLDS XML structures) 
        into feature structures. These structures are saved as a list of 
        C{Sentence}s in self.sentences.
        
        If there's only one sentence in a file, it's root element is <xml>. 
        If there's more than one, they are each <xml> sentence "roots" is 
        wrapped in an <item>...</item> (and <regression> becomes the root 
        tag of the document).
        
        @type tree: C{etree._ElementTree}
        @param tree: an etree tree element
        """
        self.sentences = []
        
        self.xml_sentences = tree.findall("item")
        if self.xml_sentences: # there are multiple sentences            
            for sent in self.xml_sentences:
                self.sentences.append(self.parse_sentence(sent, 
                                                          single_sent=False))
                
        else: # no <item> tag --> file contains just one sentence
            root = tree.find("lf/satop") # root (verb) of the sentence
            self.sentences = [self.parse_sentence(root, single_sent=True)]
            
    def parse_sentence(self, sentence, single_sent=True):
        if single_sent is False:
            item = sentence
            satop = item.find("xml/lf/satop") # root (verb) of the sentence

            # <item numOfParses="4" string="er beschreibt sie">
            sentence_string = ensure_utf8(item.attrib["string"])
            expected_parses = item.attrib["numOfParses"]

        elif single_sent is True:
            satop = sentence
            sentence_string = "" #TODO: parse str from xml comment w/ iterparse
            expected_parses = 1 
                
        # <satop nom="b1:handlung">
        #   <prop name="beschreiben"/>
        root_prop = satop.find("prop").attrib["name"]
        root_nom = satop.attrib["nom"]
        elements = []
        
        for element in satop.findall("diamond"):
            diamond = Diamond()
            diamond.convert_diamond_xml2fs(element)
            elements.append(diamond)

        sentence = Sentence()
        sentence.create_sentence(sentence_string, expected_parses, 
                                root_nom, root_prop, elements)
        return sentence


class Sentence(FeatDict):
    """
    represents an HLDS sentence as an NLTK feature structure.
    """
    def create_sentence(self, sent_str, expected_parses, root_nom, root_prop, 
                        elements):
        """         
        wraps all C{Diamond}s that were already constructed by 
        HLDSReader.parse_sentences() plus some meta data (root verb etc.) 
        into a NLTK feature structure that represents a complete sentence.
        
        @type sent_str: C{str}
        @param sent_str: the text that should be generated
        
        @type expected_parses: C{int}
        @param expected_parses: the expected number of parses
        
        @type root_prop: C{str}
        @param root_prop: the root element of that text (in case we're 
        actually generating a sentence: the main verb)
        
        @type root_nom: C{str}
        @param root_nom: the root (element/verb) category, e.g. "b1:handlung"
        
        @type elements: C{list} of C{Diamond}s        
        @param elements: a list of the diamonds that are contained in the 
        sentence 
        """
        
        self.update({Feature("text"): sent_str})
        self.update({Feature("expected_parses"): int(expected_parses)})
        self.update({Feature("root_prop"): root_prop}) 
        self.update({Feature("root_nom"): root_nom})
        
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
    #~ def __init__(self):
        #~ """        
        #~ """
        
    def convert_diamond_xml2fs(self, etree):
        """
        transforms a HLDS XML <diamond>...</diamond> structure 
        (that was parsed into an etree element) into an NLTK feature structure.

        @type etree_or_tuple: C{etree._Element}
        @param etree_or_tuple: a diamond etree element
        """
        self[Feature('mode')] = ensure_utf8(etree.attrib["mode"])
        
        for child in etree.getchildren():
            if child.tag == "diamond":
                nested_diamond = Diamond()
                nested_diamond.convert_diamond_xml2fs(child)
                self.update({nested_diamond[Feature("mode")]: nested_diamond})

            else: # children with .tag 'nom' or 'prop'
                child_tag = ensure_utf8(child.tag)
                child_name = ensure_utf8(child.attrib["name"])
                self.update({child_tag: child_name})
    
    def create_diamond(self, mode, nom, prop, nested_diamonds_list):
        """
        creates an HLDS feature structure from scratch (in contrast to 
        convert_diamond_xml2fs, which converts an HLDS XML structure into 
        its corresponding feature structure representation)
        
        @type mode: C{Str}
        @type nom: C{Str}
        @type prop: C{Str}
        @type nested_diamonds_list: C{list}
        """
        self[Feature('mode')] = mode
        if prop:
            self.update({"prop": prop})
        if nom:
            self.update({"nom": nom})
        if nested_diamonds_list:
            for nested_diamond in nested_diamonds_list:
                #print "debug. type(nested_diamond): {0}\nnested diamond: {1}".format(type(nested_diamond), nested_diamond) #TODO: dbg, rm
                self.update({nested_diamond[Feature("mode")]: nested_diamond})
 

def create_hlds_testbed(sent_or_sent_list, mode="test", output="etree"):
    """
    this function transforms C{Sentence}s into a a valid HLDS XML testbed file
    
    @type sent_or_sent_list: C{Sentence} or C{list} of C{Sentence}s
    @param sent_or_sent_list: a C{Sentence} or a list of C{Sentence}s

    @type mode: C{str}    
    @param mode: "test", if the sentence will be part of a (regression) 
    testbed file (ccg-test). "realize", if the sentence will be put in a 
    file on its own (ccg-realize).
    
    @type output: C{str}
    @param output: "etree" (etree element) or "xml" (formatted, valid xml 
    document as a string)
    
    @rtype: C{str}
    """
    if mode is "test":
        root = etree.Element("regression")
        doc = etree.ElementTree(root)
    
        etree_sentences = []
        
        if type(sent_or_sent_list) is list:
            for sentence in sent_or_sent_list:
                item = __sentence_fs2xml(sentence, mode="test")
                etree_sentences.append(item)
        
            for sentence_etree in etree_sentences:
                final_position = len(root)
                root.insert(final_position, sentence_etree)
            
        elif type(sent_or_sent_list) is Sentence:
            sentence_etree = __sentence_fs2xml(sent_or_sent_list, mode="test")
            final_position = len(root)
            root.insert(final_position, sentence_etree)

    elif mode is "realize":
        root = etree.Element("xml")
        doc = etree.ElementTree(root)
        
        if type(sent_or_sent_list) is Sentence:
            sentence_etree = __sentence_fs2xml(sent_or_sent_list, 
                                               mode="realize")
        elif type(sent_or_sent_list) is list and len(sent_or_sent_list) == 1:
            sentence_etree = __sentence_fs2xml(sent_or_sent_list[0], 
                                               mode="realize")
        else:
            raise Exception, \
                "ValueError: in 'realize' mode, sent_or_sent_list should be " \
                "one Sentence or a list containing only one Sentence."
        root.insert(0, sentence_etree)
        
    if output == "etree":
        return doc
    elif output == "xml":
        return etree.tostring(doc, encoding="utf8", 
                              xml_declaration=True, pretty_print=True)


def __sentence_fs2xml(sentence, mode="test"):
    """    
    transforms a sentence (in NLTK feature structure notation) into its 
    corresponding HLDS XML <item></item> structure.
    
    @type sentence: C{Sentence}
    @param sentence: a sentence in NLTK feature structure notation
    
    @type mode: C{str}    
    @param mode: "test", if the sentence will be part of a (regression) 
    testbed file (ccg-test). "realize", if the sentence will be put in a 
    file on its own (ccg-realize).
    
    @rtype: C{etree._Element}
    @return: the input sentence in HLDS XML format (represented as an etree 
    element)
    """
    if mode is "test":
        expected_parses = sentence[Feature("expected_parses")]
        text = sentence[Feature("text")]
        item = etree.Element("item", numOfParses=str(expected_parses),
                             string=ensure_unicode(text))
        xml = etree.SubElement(item, "xml")
        lf = etree.SubElement(xml, "lf")
    else:
        lf = etree.Element("lf")
    
    root_nom = sentence[Feature("root_nom")]
    satop = etree.SubElement(lf, "satop", nom=root_nom)
    
    root_prop = sentence[Feature("root_prop")]
    etree.SubElement(satop, "prop", name=root_prop)
    
    diamonds = []
    for key, val in sentence.items():
        if type(val) is Diamond:
            diamonds.append(sentence[key])
    
    etree_diamonds = []
    for diamond in diamonds:
        etree_diamonds.append(__diamond_fs2xml(diamond))
        
    for diamond in etree_diamonds:
        final_position = len(satop)
        satop.insert(final_position, diamond)
   
    if mode is "test":
        return item
    else:
        return lf
 
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
    
    if "prop" in diamond:    
        diamond_etree.insert(0, PROP(name=ensure_unicode(diamond["prop"])) )
    if "nom" in diamond:
    # if present, nom(inal) has to be the first argument/sub tag of a diamond
        diamond_etree.insert(0, NOM(name=ensure_unicode(diamond["nom"])) )

        
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

def diamond2sentence(diamond):
    """
    Converts a Diamond feature structure into a Sentence feature structure. 
    This becomes necessary whenever we want to realize a short utterance, e.g. 
    "die Autoren" or "die Themen Syntax und Pragmatik". 
    
    Note: OpenCCG does not really distinguish between a sentence and smaller 
    units of meaning. It simply assigns the <sentence> tag to every HLDS 
    structure it realizes, whereas each substructure of this "sentence" (no 
    matter how complex) is labelled as <diamond>.
    
    @type diamond: C{Diamond}
    @rtype: C{Sentence}
    """
    nom = ""
    prop = ""
    sentence = Sentence()
    if "nom" in diamond:
        nom = diamond["nom"]
    if "prop" in diamond:
        prop = diamond["prop"]
    nested_diamonds = [val for (key, val) in diamond.items() 
                           if type(val) is Diamond]
    sentence.create_sentence("", 1, nom, prop, nested_diamonds)
    return sentence

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
    random_sent_index = random.randrange(0, len(hlds_reader.sentences))
    random_sent_fs = \
        hlds_reader.sentences[random_sent_index]
    random_sent_xml = create_hlds_testbed([random_sent_fs], output="xml")
    all_sents_xml = create_hlds_testbed(hlds_reader.sentences, output="xml")
                                              
    print "random sentence: %i\n" % random_sent_index, random_sent_fs, \
          "\n" * 3, random_sent_xml
    return hlds_reader, all_sents_xml 


def add_nomprefixes(sentence):
    prop_dict = defaultdict(int)
    elements = [element for element in sentence.walk()]

    for e in elements:
        if type(e) is Diamond:
            if "nom" in e.keys():
                if "prop" in e.keys():
                    nom_prefix_char = e["prop"].lower()[0]
                else: #if there's no <prop> tag
                    nom_prefix_char = "x"
                    
                prop_dict[nom_prefix_char] += 1
                nom_without_prefix = e["nom"]
                e["nom"] = "{0}{1}:{2}".format(nom_prefix_char, 
                                               prop_dict[nom_prefix_char],
                                               nom_without_prefix)

def remove_nomprefixes(sentence):
    prop_dict = defaultdict(int)
    elements = [element for element in sentence.walk()]
    prefix = re.compile("\w\d+:")

    for e in elements:
        if type(e) is Diamond:
            if "nom" in e.keys():
                if prefix.match(e["nom"]):
                    e["nom"] = prefix.split(e["nom"], maxsplit=1)[1]

def etreeprint(element):
    """pretty print function for etree trees or elements
    
    @type element: C{etree._ElementTree} or C{etree._Element}
    """
    xml_string = etree.tostring(element, pretty_print=True, encoding="utf8")
    print xml_string
    return xml_string
    
    
if __name__ == "__main__":
    if len(sys.argv) > 1:
    # given an HLDS XML file as a command line argument, print a feature 
    # structure representation of the sentence(s) it contains
        for arg in sys.argv[1:]:
            hlds_reader = HLDSReader(arg, input_format="file")
            for sentence in hlds_reader.sentences:
                print sentence, "\n\n"
    else:
    # test functionality on a random testbed sentence
        fs_sents, xml_sents = test_conversion()
