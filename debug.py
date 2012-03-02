#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Arne Neumann <arne-neumann@web.de>

"""
The I{debug} module contains a number of functions, which can be used to test 
the behaviour of pypolibox' classes, test its error handling or simply 
provides short cuts to generate frequently needed data.
"""

from lxml import etree
from nltk.featstruct import Feature

from database import Query, Results, Books
from facts import AllFacts
from propositions import AllPropositions
from textplan import TextPlan, TextPlans
from messages import Message, Messages, AllMessages
from rules import Rules, ConstituentSet
import util
import hlds


def compare_hlds_variants():
    """
    TODO: kill bugs
    
    BUG1: sentence001-original-test contains 2(!) <item> sentences.
    
    """
    hlds_reader = hlds.HLDSReader(hlds.testbed_file)
    for i, sentence in enumerate(hlds_reader.sentences):
        xml_sentence_test = hlds.create_hlds_file(sentence, mode="test", 
                                                     output="xml")
        util.write_to_file(xml_sentence_test, 
                      "xmltest/sentence{0}-converted-test.xml".format(str(i).zfill(3)))

        xml_sentence_realize = hlds.create_hlds_file(sentence, mode="test", 
                                                        output="xml")        
        util.write_to_file(xml_sentence_test, 
                      "xmltest/sentence{0}-converted-realize.xml".format(str(i).zfill(3)))

    for i, item_etree in enumerate(hlds_reader.xml_sentences):
        root = etree.Element("regression")
        doc = etree.ElementTree(root)
        root.insert(0, item_etree)
        xml_sentence_original = hlds.etreeprint(doc)
        util.write_to_file(xml_sentence_original, 
                      "xmltest/sentence{0}-original-test.xml".format(str(i).zfill(3)))


                
def genprops(querynumber=10):
    """    
    generates all propositions for all books in the database concerning a 
    specific query.
    
    @type querynumber: C{int}
    @param querynumber: the index of a query from the predefined list of 
    test queries (named 'testqueries')
    
    @rtype: C{AllPropositions}
    """    
    books = Books(Results(Query(testqueries[querynumber])))
    return AllPropositions(AllFacts(books))
    
def genmessages(booknumber=0, querynumber=10):
    """
    generates all messages for a book regarding a specific database query.
    
    @type booknumber: C{int}
    @param booknumber: the index of the book from the results list ("0" 
    would be the first book with the highest score)
    
    @type querynumber: C{int}
    @param querynumber: the index of a query from the predefined list of 
    test queries (named 'testqueries')
    
    @rtype: C{list} of C{Message}s
    """
    books = Books(Results(Query(testqueries[querynumber])))
    am = AllMessages(AllPropositions(AllFacts(books)))  
    
    for message in am.books[booknumber].messages.values(): 
        message.freeze()
        #freeze messages, so Rule()s can be tested against them
    return am.books[booknumber].messages.values()

def genallmessages(query):
    """
    debug function: generates all messages plans for a query.
    
    @type query: C{int} or C{list} of C{str}
    @param query: can be the index of a test query (e.g. 4) OR a list of 
    query parameters (e.g. ["-k", "phonology", "-l", "German"])
    
    @rtype: C{AllMessages}
    @return: all messages that could be generated for the query
    """
    if isinstance(query, int):
        books = Books(Results(Query(testqueries[query])))
        return AllMessages(AllPropositions(AllFacts(books)))
    elif isinstance(query, list):
        books = Books(Results(Query(query)))
        return AllMessages(AllPropositions(AllFacts(books)))
    elif isinstance(query, Query):
        books = Books(Results(query))
        return AllMessages(AllPropositions(AllFacts(books)))

def gen_all_messages_of_type(msg_type):
    """
    generate all messages for all books from all testqueries, but return
    only those which match the given message type, e.g. 'id' or 'extra'.

    @type msg_type: C{str}
    """
    all_msg_of_type = []
    for i in range(len(testqueries)):
        all_msg_of_query_i = genallmessages(i)
        for book in all_msg_of_query_i.books:
            if msg_type in book.messages:
                all_msg_of_type.append(book.messages[msg_type])
    return all_msg_of_type
    
def gen_textplans(query):
    """
    debug function: generates all text plans for a query.
    
    @type query: C{int} or C{list} of C{str}
    @param query: can be the index of a test query (e.g. 4) OR a list of 
    query parameters (e.g. ["-k", "phonology", "-l", "German"])
    
    @rtype: C{TextPlans}
    @return: a C{TextPlans} instance, containing a number of text plans
    """
    textplans = []
    if type(query) is int:
        books = Books(Results(Query(testqueries[query])))
        return TextPlans(AllMessages(AllPropositions(AllFacts(books))))
    if type(query) is list:
        books = Books(Results(Query(query)))
        return TextPlans(AllMessages(AllPropositions(AllFacts(books))))
        
def gen_all_textplans():
    """
    generates all text plans for each query in the predefined list of test 
    queries.
    
    @rtype: C{list} of C{TextPlan}s or C{str}s
    @return:  
    """
    all_TextPlans = []
    for argnumber, arg in enumerate(testqueries):
        print "generating TextPlans for the query:{0}\n".format(arg)
        TextPlans = gen_textplans(argnumber)
        print "generated {0} TextPlans".format(len(TextPlans.document_plans))
        for i, TextPlan in enumerate(TextPlans.document_plans):
            if TextPlan == None:
                print "When using query argument {0}, no TextPlan could be generated for book {1}".format(arg, i)
        all_TextPlans.append(TextPlans)
    return all_TextPlans
 
def enumprint(obj):
    """
    prints every item of an iterable on its own line, preceded by its index
    """
    for index, item in enumerate(obj):
        if type(item) is unicode:
            print u"{0}:\n{1}\n".format(index, item)
        else:
            print "{0}:\n{1}\n".format(index, item)

def printeach(obj):
    """prints every item of an iterable on its own line"""
    for item in obj:
        print item

def msgtypes(messages):
    """
    print message types / rst relation types, no matter which data 
    structure is used to represent them
    
    @type messages: C{Messages} or 
                    C{list} of C{Message} or 
                    C{Message} or 
                    C{TextPlan} or
                    C{ConstituentSet}
    """
    if isinstance(messages, Messages):
        for i, message in enumerate(messages.messages.values()):
            print i, __msgtype_print(message)    
    elif isinstance(messages, (list, set)):
    # if messages is a list/set of C{Message}/C{ConstituentSet} instances
        for i, message in enumerate(messages):
            print i, __msgtype_print(message)
    elif isinstance(messages, Message):
        print "Message: ", __msgtype_print(messages)
    elif isinstance(messages, TextPlan):
        print "DocumentPlan: ", __msgtype_print(messages["children"])
    elif isinstance(messages, ConstituentSet):
        print "ConstituentSet: ", __msgtype_print(messages)

                
def __msgtype_print(message):
    """    
    recursive helper function for msgtypes(), which prints message types 
    and RST relation types
    
    @type message: C{Message} or C{ConstituentSet}
    @rtype: C{str}
    """
    if isinstance(message, Message):
        return message[Feature("msgType")]
    if isinstance(message, ConstituentSet):
        nucleus = __msgtype_print(message[Feature("nucleus")])
        reltype = message[Feature("relType")]
        satellite = __msgtype_print(message[Feature("satellite")])
        return "{0}({1}, {2})".format(reltype, nucleus, satellite)

#def avm_print(TextPlan):
    #"""unfinished attempt to print textplans as attribute-value matrices in LaTeX"""
    ##TODO: escape "_*"
    #avm_str = ""
    #header = "\begin{avm}\n\\[\n\n"
    #footer = "\n\n\\]\n\end{avm}"
    #content = __avm(TextPlan)
    #avm_str += header + content + footer 
    #return avm_str

#def __avm(message):
    #'''
    #@type: C{Message} or C{ConstituentSet}
    #'''
    #if isinstance(message, Message):
        #msg_content = ""
        #msg_name = message[Feature("msgType")]
        #keys = message.keys()
        #keys.remove(Feature("msgType"))

        #msg_content += "\\[\n"
        #for key in keys:
            #value = message[key]
            #msg_content += "{0} & {1} \\\\\n".format(key, value)
        #msg_content += "\n\\]"

        #message = "{0}\t& {1}".format(msg_name, msg_content)
        #return message
        
    #if isinstance(message, ConstituentSet):
        #rel_name = message[Feature("relType")]
        #nucleus = __avm(message[Feature("nucleus")])
        #satellite = __avm(message[Feature("satellite")])
        #message = "{0}\t& \\[ {1} \n\n {2} \\]".format(rel_name, nucleus, satellite)
        #return message
    
    #if isinstance(message, TextPlan):
        #message = __avm(message["children"])
        #return message
    
    #if isinstance(message, FeatDict):
        #msg_content += "\\[\n"
        #for key in keys:
            #value = message[key]
            #msg_content += "{0} & {1} \\\\\n".format(key, value)
        #msg_content += "\n\\]"
        #return msg_content
        

        
def abbreviate_textplan(textplan):
    """
    recursive helper function that prints only the skeletton of a textplan 
    (message types and RST relations but not the actual message content)
    
    @param textplan: a text plan, a constituent set or a message
    @type textplan: C{TextPlan} or C{ConstituentSet} or C{Message}
    
    @return: a message (without the attribute value pairs stored in it)
    @rtype: C{Message}
    """ 
    if isinstance(textplan, TextPlan):
        score = textplan["title"]["book score"]
        abbreviated_textplan = abbreviate_textplan(textplan["children"])
        return TextPlan(book_score=score, children=abbreviated_textplan)
    if isinstance(textplan, ConstituentSet):
        reltype = textplan[Feature("relType")]
        nucleus = abbreviate_textplan(textplan[Feature("nucleus")])
        satellite = abbreviate_textplan(textplan[Feature("satellite")])
        return ConstituentSet(relType=reltype, nucleus=nucleus, 
                              satellite=satellite)
    if isinstance(textplan, Message):
        msgtype = textplan[Feature("msgType")]
        return Message(msgType=msgtype)
        
def find_applicable_rules(messages):
    """    
    debugging: find out which rules are directly (i.e. without forming ConstituentSets first) applicable to your messages
    
    @type messages: C{list} of C{Message}s or
                    C{Messages}
    """
    if type(messages) is list: # is 'messages' a list of Message() instances?
        pass
    elif isinstance(messages, Messages):
        messages = messages.messages.values()
        
    for name, rule in Rules().rule_dict.iteritems():
        try:
            if rule.get_options(messages) != []:
                nuc_candidates = \
                    [rulename for (rulename, msg) in rule.nucleus]
                sat_candidates = \
                    [rulename for (rulename, msg) in rule.satellite]
                print "{0}: {1} - {2}, {3} - is directly applicable and results in \n\t{4}\n\n".format(name, rule.ruleType, nuc_candidates, sat_candidates, rule.get_options(messages))
        except:
            print "ERROR: Could not check if rule {0} is applicable. Possible solution: test if the rule's conditions are specified appropriately.\n\n".format(name)

        
def findrule(ruletype="", attribute="", value=""):
    """
    debugging: find rules that have a certain ruleType and some 
    attribute-value pair
    
    Example: findrule("Concession", "nucleus", "usermodel_match") finds 
    rules of type 'Concession' where rule.nucleus == 'usermodel_match'.
    """
    rules = Rules().rule_dict
    matching_rules = {}
    
    if ruletype == "":
        for index, (name, rule) in enumerate(rules.iteritems()):
            if getattr(rule, attribute) is value:
                print "rule {0} - {1}:\n{2}".format(index, name, rule)
                matching_rules[name] = rule
    elif attribute == "":
        for index, (name, rule) in enumerate(rules.iteritems()):
            if rule.ruleType is ruletype:
                print "rule {0} - {1}:\n{2}".format(index, name, rule)
                matching_rules[name] = rule
    else:
        for index, (name, rule) in enumerate(rules.iteritems()):
            if rule.ruleType is ruletype and getattr(rule, attribute) is value:
                print "rule {0} - {1}:\n{2}".format(index, name, rule)
                matching_rules[name] = rule
    return matching_rules

def apply_rule(messages, rule_name):
    """
    debugging: take a rule and apply it to your list of messages. 
    
    the resulting C{ConstituentSet} will be added to the list, while the 
    messages involved in its construction will be removed. repeat this step 
    until you've found an erroneous/missing rule.
    """
    options = Rules().rule_dict[rule_name].get_options(messages)
    if options:
        for option in options:
            score, constitutent_set, removes = option
            messages.append(constitutent_set)
            for message in removes:
                messages.remove(message)
            for message in messages:
                message.freeze()
    else:
        print "Sorry, this rule could not be applied to your messages."


def compare_textplans():
    """
    helps to find out how many different text plan structures there are.
    """
    import cPickle as pickle
    f = open("data/alltextplans.pickle", "r")
    # alltextplans.pickle was generated by running test_all_TextPlans()
    
    alltextplans = pickle.load(f)
    
    alltextplans_list = []
    for textplans in alltextplans:
        alltextplans_list.extend(textplans.document_plans)

    frozen_constsets = []
    abbreviated_textplans = []
    for textplan in alltextplans_list:
        abbrev_tp = abbreviate_textplan(textplan)
        abbreviated_textplans.append(abbrev_tp)
        abbrev_constset = abbrev_tp["children"]
        abbrev_constset.freeze()
        frozen_constsets.append(abbrev_constset)
    
    
    return alltextplans_list, abbreviated_textplans, frozen_constsets


testqueries = [ [],
         ["-k", "pragmatics"],
         ["-k", "pragmatics", "-r", "4"],
         ["-k", "pragmatics", "semantics"],
         ["-k", "pragmatics", "semantics", "-r", "7"],
         ["-l", "German"],
         ["-l", "German", "-p", "Lisp"],
         ["-l", "German", "-p", "Lisp", "-k", "parsing"],
         ["-l", "English", "-s", "0", "-c", "1"],
         ["-l", "English", "-s", "0", "-e", "1", "-k", "discourse"],
         ["-k", "syntax", "parsing", "-l", "German", "-p", "Prolog", "Lisp", 
          "-s", "2", "-t", "0", "-e", "1", "-c", "1", "-r", "7"],
            ] # list of possible query arguments for debugging purposes

error_testqueries = [ ["-k", "cheeseburger"], # keyword does not exist
               ["-k", "Pragmatics"], # keyword does exist, but only in lower case
               ["-l", "Luxembourgish"], # db has no books in this language
               ["-l", "Luxembourgish", "-k", "syntax"],
               ["-l", "English", "German"], # our db only lists monolingual books
               ["-p", ""], # should list all books that have no programming language associated with them
               ["-t", "5"], # --target should be a numerical value (int) in range 0..3
               ["-t", "-2"],
               ["-t", "1.0"],
               ["-t", "4.6"],
               ["-t", "foobar"], # --target should be a numerical value
               ["-t", ""],
               ["-s", "5"], # --pagerange should be a numerical value (int) in range 0..2
               ["-s", "-2"],
               ["-s", "1.0"],
               ["-s", "4.6"],
               ["-s", "foobar"], # --pagerange should be a numerical value
               ["-s", ""],
               ["-e", "5"], # --exercises should be 0 or 1
               ["-e", "-2"],
               ["-e", "1.0"],
               ["-e", "4.6"],
               ["-e", "foobar"],
               ["-e", ""],
               ["-c", "5"], # --codeexamples should be 0 or 1
               ["-c", "-2"],
               ["-c", "1.0"],
               ["-c", "4.6"],
               ["-c", "foobar"],
               ["-c", ""],
               ["-r", "5"], # --minresults should be 0 or a positive integer
               ["-r", "-2"],
               ["-r", "1.0"],
               ["-r", "4.6"],
               ["-r", "foobar"],
               ["-r", ""],
        ] # list of (im)possible query arguments for debugging purposes. 
          # TODO: check which query arguments behave unexpectedly

def test_cli(query_arguments=testqueries):
    """run several complex queries and print their results to stdout"""
    for arg in query_arguments:
        book_list = Books(Results(Query(arg)))
        print "{0}:\n\n".format(arg)
        for book in book_list.books:
            print book.title, book.year

