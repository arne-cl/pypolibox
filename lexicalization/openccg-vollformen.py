#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <arne-neumann@web.de>

"""
This script extracts all lexemes from the OpenCCG JPolibox lexicon.
"""
import sys
import codecs
import re
from collections import defaultdict
from lxml import etree
from pypolibox.util import ensure_utf8, ensure_unicode

#reload(sys) #hack that re-enables setdefaultencoding()
#sys.setdefaultencoding("utf-8")

#filename = "/media/sync/current/nlg/openccg-jpolibox/dict.xml"
#xml_no_encoding = "/media/sync/current/nlg/openccg-jpolibox/dict-no-encoding.xml"

str_openccg = open("/media/sync/current/nlg/openccg-jpolibox/dict.xml",
               "r")

#unicode_openccg = codecs.open("/media/sync/current/nlg/openccg-jpolibox/dict.xml",
#                      "r", encoding="utf-8")

class Lexicon():
    def __init__(self, lexicon_file):
        self.lexicon = lexicon_file.read()
        self.tree = etree.fromstring(self.lexicon)
        #self.utf8_lexicon = ensure_utf8(self.lexicon)
        #utf8_parser = etree.XMLParser(encoding='utf-8')
        #self.utf8_tree = etree.fromstring(self.utf8_lexicon, parser=utf8_parser)

        self.entries = self.tree.findall("entry")

        self.pos_dict = defaultdict(list)
        for entry in self.entries:
            pos = ensure_utf8(entry.attrib["pos"])
            stem = ensure_utf8(entry.attrib["stem"])
            self.pos_dict[pos].append(stem)

    def __str__(self):
        ret_str = ""
        for key in lexicon.pos_dict.keys():
            ret_str += "{0}:\n".format(key)
            for i in lexicon.pos_dict[key]:
                ret_str += "{0} ".format(i)
            ret_str += "\n\n"
        return ret_str
        
def extract_entities(lexicon_file, entity="lexemes", sort=True):
    lexicon = lexicon_file.readlines()
    entities = []
    lex_regex = re.compile('form=\"(.+?)\"')
    lemma_regex = re.compile('stem=\"(.+?)\"')
    for line in lexicon:
        if entity == "lexemes":
            findings = lex_regex.findall(line)
            # findall returns a list (could possibly contain more than 1 item) 
            # --> list.extend instead of list.append
        elif entity == "lemmas":
            findings = lemma_regex.findall(line)
        else:
            print "This function only extracts 'lexemes' or 'lemmas'."
        entities.extend(findings)
    return sorted(set(entities)) if sort == True else set(entities)

   
def write_to_file(word_list, file_name):
    """write a list of words to a file, one word per line"""
    word_file = open(file_name, "w")
    for line in word_list:
            word_file.write("{0}\n".format(line))
    word_file.close()


if __name__ == "__main__":
    lexicon = Lexicon(str_openccg)
