#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <arne-neumann@web.de>

r"""
HLDS (Hybrid Logic Dependency Semantics) is the format internally used by the 
OpenCCG realizer. This module shall allow the conversion between HLDS-XML 
files and NLTK feature structures. In addition, it can also be used as a
commandline to convert HLDS-XML files in printable versions of
C{nltk.FeatStruct}s. The following command produces a LaTeX file that can be
compiled into a PDF::

    python hlds.py --format latex --outfile output.tex input1.xml input2.xml

Alternatively, you can also produce 'ASCII art' with this command::

    python hlds.py --format nltk --outfile output.tex input1.xml input2.xml

This way, the phrase 'das Buch' can be transformed from this HLDS-XML
representation::

    <?xml version="1.0" encoding="UTF-8"?>
    <xml>
      <lf>
        <satop nom="b1:artefaktum">
          <prop name="Buch"/>
          <diamond mode="NUM">
            <prop name="sing"/>
          </diamond>
          <diamond mode="ART">
            <nom name="d1:sem-obj"/>
            <prop name="def"/>
          </diamond>
        </satop>
      </lf>
      <target>das Buch</target>
    </xml>

To this attribute-value matrix (LaTeX)::

    \begin{avm}
        \[ $*$nom$*$  & `b1:artefaktum' \\
           $*$prop$*$ & `Buch' \\
           $*$text$*$ & `das Buch' \\
           NUM        & \[ prop & `sing' \] \\
           ART        & \[ nom  & `d1:sem-obj' \\
                           prop & `def' \] \\
        \]
    \end{avm}

or this one (plain text)::

    [ *root_nom*        = 'b1:artefaktum'           ]
    [ *root_prop*       = 'Buch'                    ]
    [ *text*            = 'das Buch'                ]
    [                                               ]
    [ 00__NUM           = [ *mode* = 'NUM'  ]       ]
    [                     [ prop   = 'sing' ]       ]
    [                                               ]
    [                     [ *mode* = 'ART'        ] ]
    [ 01__ART           = [ nom    = 'd1:sem-obj' ] ]
    [                     [ prop   = 'def'        ] ] 
"""

import argparse
import sys
import re
import random
from collections import defaultdict
from operator import itemgetter
from lxml import etree
from lxml.builder import ElementMaker
import nltk
from nltk.featstruct import Feature, FeatDict
from util import ensure_utf8, ensure_unicode, write_to_file


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
            root = sentence.getroottree()
            target_element = root.find("target")
                        
            if target_element is not None:
                sentence_string = target_element.text
            else:
                sentence_string = ""
            
            expected_parses = 1 
                
        # <satop nom="b1:handlung">
        #   <prop name="beschreiben"/>
        root_prop = "" # some HLDS satop structures don't have a <prop> tag
        if satop.find("prop") is not None:
            root_prop = satop.find("prop").attrib["name"]
        root_nom = satop.attrib["nom"]
        elements = []
        
        for element in satop.findall("diamond"):
            diamond = convert_diamond_xml2fs(element)
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
                        diamonds):
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
        
        @type diamonds: C{list} of C{Diamond}s        
        @param diamonds: a list of the diamonds that are contained in the 
        sentence 
        """
        
        self.update({Feature("text"): sent_str})
        self.update({Feature("expected_parses"): int(expected_parses)})
        self.update({Feature("root_nom"): root_nom})
        if root_prop: # not always present, e.g. when realizing a pronoun
            self.update({Feature("root_prop"): root_prop}) 


        if diamonds:
            for i, diamond in enumerate(diamonds):
                identifier = "{0}__{1}".format(str(i).zfill(2), 
                                               diamond[Feature("mode")])
                self.update({identifier: diamond})

        
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
    def append_subdiamond(self, subdiamond, mode=None):
        """
        appends a subdiamond structure to an existing diamond structure, while 
        allowing to change the mode of the subdiamond
        
        @type mode: C{str} or C{NoneType}
        @param mode: the mode that the subdiamond shall have. this will 
        also be used to determine the subdiamonds identifier. if the 
        diamond already has two subdiamonds (e.g. "00__AGENS" and 
        "01__PATIENS") and add a third subdiamond with mode "TEMP", its 
        identifier will be "02__TEMP". if mode is None, the subdiamonds 
        mode will be left untouched.
        """
        index = last_diamond_index(self) + 1
        
        if mode: #change mode only if not None
            subdiamond.update({Feature("mode"): mode})

        identifier = "{0}__{1}".format(str(index).zfill(2), 
                                       subdiamond[Feature("mode")])
        self.update({identifier: subdiamond})

    def prepend_subdiamond(self, subdiamond_to_prepend, mode=None):
        """
        prepends a subdiamond structure to an existing diamond structure, while 
        allowing to change the mode of the subdiamond
        
        @type subdiamond_to_prepend: C{Diamond}
        
        @type mode: C{str} or C{NoneType}
        @param mode: the mode that the subdiamond shall have. this will 
        also be used to determine the subdiamonds identifier. if the 
        diamond already has two subdiamonds (e.g. "00__AGENS" and 
        "01__PATIENS") and we'll prepend a third subdiamond with mode 
        "TEMP", its identifier will be "00__TEMP", while the remaining two 
        subdiamond identifiers will will be incremented by 1, e.g. 
        "01__AGENS" and "02__PATIENS". if mode is None, the subdiamonds 
        mode will be left untouched.
        """
        if mode: #change mode only if not None
            subdiamond_to_prepend.update({Feature("mode"): mode})

        # a featstruct is essentially a dictionary, so we'll need to sort it!
        existing_subdiamonds = sorted([(dkey,d) for (dkey,d) in self.items() 
                                            if isinstance(d, Diamond)], 
                                      key=itemgetter(0))
        
        prefixless_subdiamonds = []
        for diamond_key, diamond in existing_subdiamonds:
            prefixless_subdiamonds.append(diamond)
            self.pop(diamond_key)
            
        self.append_subdiamond(subdiamond_to_prepend)
        for diamond in prefixless_subdiamonds:
            self.append_subdiamond(diamond)

    def insert_subdiamond(self, index, subdiamond_to_insert, mode=None):
        """
        insert a C{Diamond} into this one before the index, while 
        allowing to change the mode of the subdiamond.
        
        @type index: C{int}
        @type subdiamond_to_insert: C{Diamond}

        @type mode: C{str} or C{NoneType}
        @param mode: the mode that the subdiamond shall have. this will 
        also be used to determine the subdiamonds identifier. if the 
        diamond already has two subdiamonds (e.g. "00__AGENS" and 
        "01__PATIENS") and we'll insert a third subdiamond at index '1' 
        with mode "TEMP", its identifier will be "01__TEMP", while the 
        remaining two subdiamond identifiers will will be changed 
        accordingly, e.g. "00__AGENS" and "02__PATIENS".
        if mode is None, the subdiamonds mode will be left untouched.
        """
        if mode: #change mode only if not None
            subdiamond_to_insert.update({Feature("mode"): mode})

        # a featstruct is essentially a dictionary, so we'll need to sort it!
        existing_subdiamonds = sorted([(dkey,d) for (dkey,d) in self.items() 
                                            if isinstance(d, Diamond)], 
                                      key=itemgetter(0))
        
        prefixless_subdiamonds = []
        for diamond_key, diamond in existing_subdiamonds:
            prefixless_subdiamonds.append(diamond)
            self.pop(diamond_key)
            
        prefixless_subdiamonds.insert(index, subdiamond_to_insert)
        for diamond in prefixless_subdiamonds:
            self.append_subdiamond(diamond)

    def change_mode(self, mode):
        """
        changes the mode of a C{Diamond}, which is sometimes needed when 
        embedding it into another C{Diamond} or C{Sentence}.
        
        @type mode: C{str}
        """
        self[Feature('mode')] = mode


def create_diamond(mode, nom, prop, nested_diamonds_list):
    """
    creates an HLDS feature structure from scratch (in contrast to 
    convert_diamond_xml2fs, which converts an HLDS XML structure into 
    its corresponding feature structure representation)
    
    NOTE: I'd like to simply put this into __init__, but I don't know how 
    to subclass FeatDict properly. FeatDict.__new__ complains about 
    Diamond.__init__(self, mode, nom, prop, nested_diamonds_list) having 
    too many arguments.
    
    @type mode: C{Str}
    @type nom: C{Str}
    @type prop: C{Str}
    @type nested_diamonds_list: C{list}
    """
    diamond = Diamond()
    diamond[Feature('mode')] = mode

    if nom:
        diamond.update({"nom": nom})
    if prop:
        diamond.update({"prop": prop})
    if nested_diamonds_list:
        for i, nested_diamond in enumerate(nested_diamonds_list):
            identifier = "{0}__{1}".format(str(i).zfill(2), 
                                           nested_diamond[Feature("mode")])
            diamond.update({identifier: nested_diamond})
    return diamond


def convert_diamond_xml2fs(etree):
    """
    transforms a HLDS XML <diamond>...</diamond> structure 
    (that was parsed into an etree element) into an NLTK feature structure.

    @type etree_or_tuple: C{etree._Element}
    @param etree_or_tuple: a diamond etree element
    
    @rtype: C{Diamond}
    """
    mode = ensure_utf8(etree.attrib["mode"])

    nested_diamonds = []
    nom = "" # default value
    prop = "" # default value
    
    for child in etree.getchildren():
        if child.tag == "diamond":
            nested_diamond = convert_diamond_xml2fs(child)
            nested_diamonds.append(nested_diamond)
        elif child.tag == "nom":
            nom = ensure_utf8(child.attrib["name"])
        elif child.tag == "prop":
            prop = ensure_utf8(child.attrib["name"])

    return create_diamond(mode, nom, prop, nested_diamonds)
 

def hlds2xml(featstruct):
    """
    debug function that returns the string representation of a feature 
    structure (Diamond or Sentence) and its HLDS XML equivalent.
    
    @type featstruct: C{Diamond} or C{Sentence}
    @rtype: C{str}
    """
    assert isinstance(featstruct, (Diamond, Sentence))
    input_str = featstruct.__str__()
    
    if isinstance(featstruct, Diamond):
        sentence = diamond2sentence(featstruct)
        output_str = create_hlds_file(sentence, mode="realize", 
                                         output="xml")
    
    if isinstance(featstruct, Sentence):
        output_str = create_hlds_file(featstruct, mode="realize", 
                                         output="xml")
 
    return "Input:\n\n{0}\n\nOutput:\n\n{1}".format(input_str, output_str)


def create_hlds_file(sent_or_sent_list, mode="test", output="etree"):
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
        return etreeprint(doc, debug=False)


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
    else: # mode is "realize"
        lf = etree.Element("lf")
    
    root_nom = sentence[Feature("root_nom")]
    satop = etree.SubElement(lf, "satop", nom=root_nom)

    if Feature("root_prop") in sentence:
        root_prop = sentence[Feature("root_prop")]
        etree.SubElement(satop, "prop", name=root_prop)
    
    diamonds = []
    for key in sorted(sentence.keys()):
    # keys need to be sorted, otherwise Diamonds within a Sentence will have a
    # different order than before. Diamond keys seem ordered, but they aren't
    # (keys beginning with numbers seem to be in descending order, those 
    # beginning with letters in ascending order)
        if isinstance(sentence[key], Diamond):
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
    for key in sorted(diamond.keys()):
    # keys need to be sorted, otherwise Diamonds within a Sentence will have a
    # different order than before. Diamond keys seem ordered, but they aren't
    # (keys beginning with numbers seem to be in descending order, those 
    # beginning with letters in ascending order)
        if isinstance(diamond[key], Diamond):
            subdiamonds.append(diamond[key])
    
    etree_subdiamonds = []    
    for subdiamond in subdiamonds:
        etree_subdiamonds.append(__diamond_fs2xml(subdiamond))
        
    for subdiamond in etree_subdiamonds:
        final_position = len(diamond_etree)
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
    matter how complex) is labelled as a <diamond>.
    
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

    nested_diamonds = []
    for key in sorted(diamond.keys()):
    # keys need to be sorted, otherwise Diamonds within a Sentence will have a
    # different order than before. Diamond keys seem ordered, but they aren't
    # (keys beginning with numbers seem to be in descending order, those 
    # beginning with letters in ascending order)
        if isinstance(diamond[key], Diamond):
            nested_diamonds.append(diamond[key])

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
    random_sent_xml = create_hlds_file([random_sent_fs], output="xml")
    all_sents_xml = create_hlds_file(hlds_reader.sentences, output="xml")
                                              
    print "random sentence: %i\n" % random_sent_index, random_sent_fs, \
          "\n" * 3, random_sent_xml
    return hlds_reader, all_sents_xml 


def add_mode_suffix(diamond, mode="N"):
    matching_subdiamond_keys = []
    for key in diamond.keys():
        if isinstance(key, str) and key.endswith(mode):
            if diamond[key][Feature("mode")] == mode:
                matching_subdiamond_keys.append(key)
                
    sorted_subdiamond_keys = sorted(matching_subdiamond_keys)
    for i, key in enumerate(sorted_subdiamond_keys):
        diamond[key][Feature("mode")] = "{0}{1}".format(mode, i+1)

    for key, value in diamond.items():
        if isinstance(value, Diamond):
            add_mode_suffix(value, mode)


def add_nom_prefixes(diamond):
    """
    Adds a prefix/index to the name attribute of every <nom> tag of a 
    C{Diamond} or C{Sentence} structure. Without this, I{ccg-realize} will 
    only produce gibberish.
    
    Every <nom> tag has a 'name' attribute, which contains a category/type-like
    description of the corresponding <prop> tag's name attribute, e.g.::
    
        <diamond mode="PRÄP">
            <nom name="v1:zugehörigkeit"/>
            <prop name="von"/>
        </diamond>

    Here 'zugehörigkeit' is the name of a category that the preposition 
    'von' belongs to. usually, the nom prefix is the first character of the 
    prop name attribute with an added index. index iteration is done by a 
    depth-first walk through all diamonds contained in the given feature 
    structure. In this example 'v1:zugehörigkeit' means, that "von" is the 
    first C{diamond} in the structure that starts with 'v' and belongs to 
    the category 'zugehörigkeit'.
    """
    prop_dict = defaultdict(int)
    elements = [element for element in diamond.walk()]

    for e in elements:
        if type(e) is Diamond:
            if "nom" in e.keys():
                nom_prefix_char = __determine_nom_prefix(e)
                    
                prop_dict[nom_prefix_char] += 1
                nom_without_prefix = e["nom"]
                nom_type = type(nom_without_prefix)
                e["nom"] = "{0}{1}:{2}".format(ensure_utf8(nom_prefix_char), 
                                               prop_dict[nom_prefix_char],
                                               ensure_utf8(nom_without_prefix))
                if nom_type == unicode:
                # preserve unicode, if the string was unicode encoded before
                    e["nom"] = ensure_unicode(e["nom"])


def __determine_nom_prefix(diamond):
    """
    determines, which character will be used as a prefix for <nom> tags. 
    usually, its the first character used in the corresponding <prop> tag, 
    (e.g. prop = "und" will turn nom = "konjunktion" into nom = 
    "u1:konjunktion", iff its the 1st "konjunktion" beginning with "u" in 
    that sentence).
    
    @type diamond: C{Diamond}
    
    @rtype: C{str}
    @return: a single character
    """
    numbers_only = re.compile("\d+$")
    
    if "prop" in diamond.keys():
        prop = ensure_utf8(diamond["prop"])
        if numbers_only.match(prop):
            nom_prefix_char = "n"
        else: # <prop> doesn't represent a year, page count etc.
            nom_prefix_char = diamond["prop"].lower()[0]
        
    else: #if there's no <prop> tag
        nom_prefix_char = "x"
    
    return ensure_utf8(nom_prefix_char)
    

def remove_nom_prefixes(diamond):
    prop_dict = defaultdict(int)
    elements = [element for element in diamond.walk()]
    prefix = re.compile("\w\d+:")

    for e in elements:
        if type(e) is Diamond:
            if "nom" in e.keys():
                if prefix.match(e["nom"]):
                    e["nom"] = prefix.split(e["nom"], maxsplit=1)[1]


def last_diamond_index(featstruct):
    """
    Returns the highest index currently used withing a given C{Diamond} or 
    C{Sentence}. E.g., if this structure contains three diamonds 
    ("00__ART", "01__NUM" and "02__TEMP"), the return value will be 2. The 
    return value is -1, if the feature structure doesn't contain any 
    C{Diamond}s.
    
    @type featstruct: C{Diamond} or C{Sentence}
    @rtype: C{int}
    """
    diamond_keys = [k for (k,v) in featstruct.items() if isinstance(v, Diamond)]
    return len(diamond_keys) - 1


def featstruct2avm(featstruct, mode="non-recursive"):
    """
    converts an NLTK feature structure into an attribute-value matrix
    that can be printed with LaTeX's avm environment.

    @type featstruct: C{nltk.featstruct} or C{Diamond} or C{Sentence}
    @rtype: C{str}
    """
    ret_str = "\[ "
    for key, val in sorted(featstruct.items()):

        if isinstance(val, Diamond): #handles nested Diamond structures
            diamond_key = val[Feature("mode")]
            diamond_val = featstruct2avm(val, mode="recursive")
            ret_str += "{0} & {1} \\\\\n".format( ensure_utf8(diamond_key),
                                                  ensure_utf8(diamond_val))

        elif isinstance(val, nltk.FeatStruct):
        #every other subclass of FeatStruct incl. FeatStruct
            nested_featstruct = featstruct2avm(val, mode="recursive")
            ret_str += "{0} & {1} \\\\\n".format( ensure_utf8(key),
                                                  ensure_utf8(nested_featstruct))
            
            
        else: # normal key, value pairs within a FeatStruct
            if key in (Feature("mode"), Feature("expected_parses")):
                continue # don't print "mode" or "expected_parses" keys
            elif key == Feature("root_nom"):
                key = Feature("nom")
            elif key == Feature("root_prop"):
                key = Feature("prop")

            ret_str += "{0} & `{1}' \\\\\n".format( ensure_utf8(key),
                                                    ensure_utf8(val))

    ret_str += " \]\n"

    if mode == "non-recursive":
        clean_ret_str = ret_str.replace("*", "$*$").replace("_", "\_")
        ret_str = "{0}\n{1}{2}".format('\\begin{avm}', clean_ret_str, '\\end{avm}')
    return ret_str


def etreeprint(element, debug=True, raw=False):
    """pretty print function for etree trees or elements
    
    @type element: C{etree._ElementTree} or C{etree._Element}
    @param debug: if True: not only return the XML string, but also print it to
    stdout. if False: only return the XML string
    
    @param raw: if True: just transform the etree (element) into a string, 
    don't add or prettify anything. if False: add an XML declaration and use
    pretty print to make the output more readable for humans.
    """
    if raw is False:
        xml_string = etree.tostring(element, xml_declaration=True, 
                                    pretty_print=True, encoding="UTF-8")
    else:
        xml_string = etree.tostring(element, xml_declaration=False, 
                                    pretty_print=False, encoding="UTF-8")        
        
    if debug is True:
        print xml_string
    return xml_string


parser = argparse.ArgumentParser(description='convert HLDS XML to nltk.FeatStructs or LaTeX AVMs')
parser.add_argument('files', metavar='FILE', type=str, nargs='+',
                    help='one or more HLDS XML files to be processed')
parser.add_argument('-f', '--format', dest='output_format', action='store',
                    default='nltk',
                    help='choose between nltk or latex')
parser.add_argument('-o', '--outfile', nargs='?',
                    type=argparse.FileType('w'), default=sys.stdout,
                    help='file to write the output to (default: stdout)')

LATEX_AVM_HEADER = r"""
\documentclass[10pt]{article}
\usepackage{graphicx}
\usepackage{avm}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[ngerman]{babel}
\begin{document}

"""


if __name__ == "__main__":
    args = parser.parse_args(sys.argv[1:])
    if args.output_format == 'latex':
        args.outfile.write(LATEX_AVM_HEADER)
        for filename in args.files:
            hlds_reader = HLDSReader(filename, input_format="file")
            for sentence in hlds_reader.sentences:
                avm = featstruct2avm(sentence)
                args.outfile.write(avm)
                args.outfile.write("\n\n")
        args.outfile.write("\end{document}")

    elif args.output_format == 'nltk':
        for filename in args.files:
            hlds_reader = HLDSReader(filename, input_format="file")
            for sentence in hlds_reader.sentences:
                print >>args.outfile, sentence, "\n\n"

    args.outfile.close()
