#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: ianb ???, Arne Neumann

"""
'text_compare' and 'xml_compare' code stolen from: https://bitbucket.org/formencode/official-formencode/src/883ff9329228/formencode/doctest_xml_compare.py

TODO: check source. i think it was originally from ianb's repo
""" 

try:
    import doctest
    doctest.OutputChecker
except AttributeError: # Python < 2.4
    import util.doctest24 as doctest
try:
    import xml.etree.ElementTree as ET
except ImportError:
    import elementtree.ElementTree as ET
from xml.parsers.expat import ExpatError as XMLParseError

import os
import re
from lxml import etree
from commands import getstatusoutput

import util
import hlds
import lexicalization

"""
for fname in origlist:
    file_path = os.path.join("../xmltest", fname)
    if os.path.isfile(file_path):
        tree = etree.parse(file_path)
        xml_etree = tree.find("item/xml")
        f = open("etree.tmp", "w")
        f.write( etreeprint(xml_etree, debug=False) )
        status, output = getstatusoutput("{0} {1}".format(realizer, "etree.tmp"))
        results.append( (status, output) )
        print status
        print output, "\n\n+++\n\n"

--> original-ccg-test-results.pickle
"""

def split_testbed(testbed_file=hlds.testbed_file):
    """
    splits Martin's original testbedHLDS.xml file (which can only be used by 
    I{ccg-test}) into one HLDS file per sentence. These files can be realized 
    with I{ccg-realize}, which offers much better output for debugging 
    purposes.
    """
    with open(testbed_file) as f:
        testbed_tree = etree.parse(f)
    sentences = testbed_tree.findall("item/xml")
    for i, sentence in enumerate(sentences):
        sent_xml_str = hlds.etreeprint(sentence, debug=False, raw=False)
        util.write_to_file(sent_xml_str, 
                           "xmltest/testbed{0}.xml".format(str(i).zfill(3)))


def reconstruct_testbed_files(testbed_file=hlds.testbed_file):
    hlds_reader = hlds.HLDSReader(testbed_file, input_format="file")
    for i, sentence in enumerate(hlds_reader.sentences):
        sent_xml_str = hlds.create_hlds_file(sentence, mode="realize", 
                                                output="xml")
        util.write_to_file(sent_xml_str, 
                           "xmltest/testbed%s-reconstructed.xml"
                                % str(i).zfill(3) )


def realize_testbed_files(list_of_filenames, output_pickle):
    """
    realizes any number of files with I{ccg-realize} and save the output to a 
    pickle.
    
    @type list_of_filenames: C{list} of C{str}
    @param list_of_filenames: list of (absolute) paths to HLDS XML files that 
    will be realized.
    
    @type output_pickle: C{str}
    @param output_pickle: path to the pickle file that the results should be 
    stored in.
    """
    current_dir = os.getcwd()
            
    os.chdir(lexicalization.GRAMMAR_PATH)
    grammar_abspath = os.getcwd()
    realizer = os.path.join(lexicalization.OPENCCG_BIN_PATH, "ccg-realize")

    results = []
    for fname in list_of_filenames:
        file_path = os.path.join(grammar_abspath, fname)
        if os.path.isfile(file_path):
            status, output = getstatusoutput("{0} {1}".format(realizer, 
                                                              file_path))
            print status, "\n", output, "\n\n"
            results.append( (status, output) )
        else:
            os.chdir(current_dir)
            raise Exception, "{0} is not a file.\n" \
                "Please use an absolute path or one that is relative to:\n" \
                "{1}".format(file_path, grammar_abspath)
    
    os.chdir(current_dir)
    util.write_to_file(results, output_pickle)
    return results


def listdir_with_abspath(path, pattern_string):
    """
    lists the absolute path of all files in a directory that match a regex 
    pattern.
    
    @type path: C{str}
    @param path: path to a directory
    
    @type pattern_string: C{str}
    @param pattern_string: a regular expression
    """
    pattern = re.compile(pattern_string)
    fnames = os.listdir(path)
    matching_fnames = [fname for fname in fnames if pattern.search(fname)]
    fnames_with_abspath = [os.path.abspath(os.path.join(path, fname)) 
                            for fname in matching_fnames]
    return sorted(fnames_with_abspath)


def xml_compare(x1, x2, debug=True):
    if x1.tag != x2.tag:
        if debug is True:
            print 'Tags do not match: %s and %s' % (x1.tag, x2.tag)
        return False
    for name, value in x1.attrib.items():
        if x2.attrib.get(name) != value:
            if debug is True:
                print 'Attributes do not match: %s=%r, %s=%r' \
                         % (name, value, name, x2.attrib.get(name))
            return False
    for name in x2.attrib.keys():
        if name not in x1.attrib:
            if debug is True:
                print 'x2 has an attribute x1 is missing: %s' % name
            return False
    if not text_compare(x1.text, x2.text):
        if debug is True:
            print 'text: %r != %r' % (x1.text, x2.text)
        return False
    if not text_compare(x1.tail, x2.tail):
        if debug is True:
            print 'tail: %r != %r' % (x1.tail, x2.tail)
        return False
    cl1 = x1.getchildren()
    cl2 = x2.getchildren()
    if len(cl1) != len(cl2):
        if debug is True:
            print 'children length differs, %i != %i' % (len(cl1), len(cl2))
        return False
    i = 0
    for c1, c2 in zip(cl1, cl2):
        i += 1
        if not xml_compare(c1, c2, debug=debug):
            if debug is True:
                print 'children %i do not match: %s' % (i, c1.tag)
            return False
    return True


def compare_xml_files(fname1, fname2, debug=True):
    with open(fname1, "r") as file1:
        xml_str1 = file1.read()
    with open(fname2, "r") as file2:
        xml_str2 = file2.read()
    
    xml1 = ET.fromstring(xml_str1)
    xml2 = ET.fromstring(xml_str2)
    
    return xml_compare(xml1, xml2, debug)
    
        

def text_compare(t1, t2):
    if not t1 and not t2:
        return True
    if t1 == '*' or t2 == '*':
        return True
    return (t1 or '').strip() == (t2 or '').strip()

