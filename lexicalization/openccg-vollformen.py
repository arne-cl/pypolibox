#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <arne-neumann@web.de>

"""
This script extracts all lexemes from the OpenCCG JPolibox lexicon.
"""

import re

OPENCCG_LEXICON = open("/media/sync/current/nlg/openccg-jpolibox/dict.xml","r").readlines()

def extract_lexemes(lexicon):
    lexemes = []
    lex_regex = re.compile('form=\"(.+?)\"')
    for line in lexicon:
        lexeme = lex_regex.findall(line) 
        # findall returns a list (could possibly contain more than 1 item) 
        # --> list.extend instead of list.append
        lexemes.extend(lexeme)
    return sorted(set(lexemes))

def extract_lemmas(lexicon):
    lemmas = []
    lemma_regex = re.compile('stem=\"(.+?)\"')
    for line in lexicon:
        lemma = lex_regex.findall(line) 
        # findall returns a list (could possibly contain more than 1 item) 
        # --> list.extend instead of list.append
        lemmas.extend(lemma)
    return sorted(set(lemmas))

    
def write_to_file(word_list, file_name):
    """write a list of words to a file, one word per line"""
    word_file = open(file_name, "w")
    for line in word_list:
            word_file.write("{0}\n".format(line))
    word_file.close()
