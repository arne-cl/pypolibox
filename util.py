# Author: Arne Neumann <arne-neumann@web.de>

"""
The C{util} module contains a number of 'bread and butter' functions that are 
needed to run pypolibox, but are not particularly interesting (e.g. format 
converters, existence checks etc.).
"""

import re
import cPickle as pickle

def ensure_utf8(string):
    """
    ensures that a string does not use unicode but UTF8
    """
    if type(string) == unicode:
        string = string.encode("UTF8")
    return string

def ensure_unicode(string):
    """
    ensures that a string does use unicode instead of UTF8
    """
    if type(string) != unicode:
        string = string.decode("UTF8")
    return string


def flatten(nested_list):
    """flattens a list, where each list element is itself a list
    
    @param nested_list: the nested list
    @type nested_list: list
    @return: flattened list
    """
    flattened_list = []
    for element in nested_list:
        flattened_list.extend(element)
    return flattened_list

def sql_array_to_set(sql_array):
    """ converts SQL string "arrays" into a set of strings
    
    our book database uses '[' and ']' to handle attributes w/ more than one 
    value: e.g. authors = '[Noam Chomsky][Alan Touring]'

    this function turns those multi-value strings into a set with separate 
    values

    @type sql_array: C{str}    
    @param sql_array: a string from the database that represents one or 
    more items delimited by '[' and ']', e.g. "[Noam Chomsky]" or "[Noam 
    Chomsky][Alan Touring]"
    
    @rtype: C{set} of C{str}
    
    @return: a set of strings, where each string represents one item from 
    the database, e.g. ["Noam Chomsky", "Alan Touring"]    
    """
    item = re.compile("\[(.*?)\]")
    items = item.findall(sql_array)
    item_set = set()
    for i in items:
        item_set.add(i)
    return item_set

def sql_array_to_list(sql_array):
    """ converts SQL string "arrays" into a list of strings
    
    Our book database uses '[' and ']' to handle attributes w/ more than one
    value: e.g. authors = '[Noam Chomsky][Alan Touring]'. This function 
    turns those multi-value strings into a set with separate values.

    @type sql_array: C{str}    
    @param sql_array: a string from the database that represents one or 
    more items delimited by '[' and ']', e.g. "[Noam Chomsky]" or "[Noam 
    Chomsky][Alan Touring]"
    
    @rtype: C{list} of C{str}
    @return: a list of strings, where each string represents one item from 
    the database, e.g. ["Noam Chomsky", "Alan Touring"]    
    """
    item = re.compile("\[(.*?)\]")
    return item.findall(sql_array)



def exists(thing, namespace):
    """checks if a variable/object/instance exists in the given namespace
    
    @type thing: C{str}
    @type namespace: C{dict}
    @rtype: C{bool}
    """
    if namespace.has_key(thing):
        return True
    else:
        return False

def msgs_instance_to_list_of_msgs(messages_instance):
    return [message for message in messages_instance.messages.values()]
    
def freeze_all_messages(message_list):
    """
    makes all messages (C{FeatDict}s) immutable, which is necessary for turning
    them into sets
    """
    for message in message_list:
        message.freeze()
    return message_list

def write_to_file(str_or_obj, file_path):
    """
    takes a string and writes it to a file or takes any other object, pickles 
    it and writes it to a file
    """
    f = open(file_path, "w")
    if type(str_or_obj) is str:
        f.write(str_or_obj)
    else:
        pickle.dump(str_or_obj, f)
    f.close()
    
