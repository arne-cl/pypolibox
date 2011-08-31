#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: ianb ???

"""
code stolen from: https://bitbucket.org/formencode/official-formencode/src/883ff9329228/formencode/doctest_xml_compare.py

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

#~ RealOutputChecker = doctest.OutputChecker

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



def debug(*msg):
    import sys
    print >> sys.stderr, ' '.join(map(str, msg))


#~ class HTMLOutputChecker(RealOutputChecker):
#~ 
    #~ def check_output(self, want, got, optionflags):
        #~ normal = RealOutputChecker.check_output(self, want, got, optionflags)
        #~ if normal or not got:
            #~ return normal
        #~ try:
            #~ want_xml = make_xml(want)
        #~ except XMLParseError:
            #~ pass
        #~ else:
            #~ try:
                #~ got_xml = make_xml(got)
            #~ except XMLParseError:
                #~ pass
            #~ else:
                #~ if xml_compare(want_xml, got_xml):
                    #~ return True
        #~ return False
#~ 
    #~ def output_difference(self, example, got, optionflags):
        #~ actual = RealOutputChecker.output_difference(
            #~ self, example, got, optionflags)
        #~ want_xml = got_xml = None
        #~ try:
            #~ want_xml = make_xml(example.want)
            #~ want_norm = make_string(want_xml)
        #~ except XMLParseError, e:
            #~ if example.want.startswith('<'):
                #~ want_norm = '(bad XML: %s)' % e
                #~ #  '<xml>%s</xml>' % example.want
            #~ else:
                #~ return actual
        #~ try:
            #~ got_xml = make_xml(got)
            #~ got_norm = make_string(got_xml)
        #~ except XMLParseError, e:
            #~ if example.want.startswith('<'):
                #~ got_norm = '(bad XML: %s)' % e
            #~ else:
                #~ return actual
        #~ s = '%s\nXML Wanted: %s\nXML Got   : %s\n' % (
            #~ actual, want_norm, got_norm)
        #~ if got_xml and want_xml:
            #~ result = []
            #~ xml_compare(want_xml, got_xml, result.append)
            #~ s += 'Difference report:\n%s\n' % '\n'.join(result)
        #~ return s


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


#~ def make_xml(s):
    #~ return ET.XML('<xml>%s</xml>' % s)
#~ 
#~ 
#~ def make_string(xml):
    #~ if isinstance(xml, (str, unicode)):
        #~ xml = make_xml(xml)
    #~ s = ET.tostring(xml)
    #~ if s == '<xml />':
        #~ return ''
    #~ assert s.startswith('<xml>') and s.endswith('</xml>'), repr(s)
    #~ return s[5:-6]
#~ 
#~ 
#~ def install():
    #~ doctest.OutputChecker = HTMLOutputChecker
#~ 
