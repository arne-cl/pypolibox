# Author: Arne Neumann <arne-neumann@web.de>

"""
The ``util`` module contains a number of 'bread and butter' functions that are 
needed to run pypolibox, but are not particularly interesting (e.g. format 
converters, existence checks etc.).

There shouldn't be any code in this module that require loading other
modules from pypolibox!
"""

import os
import re
import pickle as pickle
import yaml
from nltk.featstruct import Feature


def ensure_utf8(string_or_int):
    """
    ensures that a string does not use unicode but UTF8.
    converts integer input to a string.
    """
    if isinstance(string_or_int, int):
        string = str(string_or_int).encode("UTF8")
    elif isinstance(string_or_int, str):
        string = string_or_int.encode("UTF8")
    elif isinstance(string_or_int, bytes):
        string = string_or_int
    else:
        print("string_or_int: ", string_or_int)
        raise Exception("can't process input of type {0}".format(type(string_or_int)))
    return string

def ensure_unicode(string_or_int):
    """
    ensures that a string does use unicode instead of UTF8.
    converts integer input to a unicode string.
    """
    if isinstance(string_or_int, int):
        string_or_int = str(string_or_int)

    if isinstance(string_or_int, str):
        string = string_or_int
    else:
        #print "string_or_int: ", string_or_int, " with type: ", type(string_or_int)
        string = string_or_int.decode("UTF8")
    return string


def flatten(nested_list):
    """flattens a list, where each list element is itself a list
    
    :param nested_list: the nested list
    :type nested_list: list
    :return: flattened list
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

    :type sql_array: ``str``    
    :param sql_array: a string from the database that represents one or 
    more items delimited by '[' and ']', e.g. "[Noam Chomsky]" or "[Noam 
    Chomsky][Alan Touring]"
    
    :rtype: ``set`` of ``str``
    
    :return: a set of strings, where each string represents one item from 
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

    :type sql_array: ``str``    
    :param sql_array: a string from the database that represents one or 
    more items delimited by '[' and ']', e.g. "[Noam Chomsky]" or "[Noam 
    Chomsky][Alan Touring]"
    
    :rtype: ``list`` of ``str``
    :return: a list of strings, where each string represents one item from 
    the database, e.g. ["Noam Chomsky", "Alan Touring"]    
    """
    item = re.compile("\[(.*?)\]")
    return item.findall(sql_array)



def msgs_instance_to_list_of_msgs(messages_instance):
    """converts a ``Messages`` instance into a list of ``Message`` instances"""
    return [message for message in list(messages_instance.messages.values())]
    
def freeze_all_messages(message_list):
    """
    makes all messages (``FeatDict``s) immutable, which is necessary for turning
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
    f_obj = open(file_path, "w")
    if type(str_or_obj) is str:
        f_obj.write(str_or_obj)
    else:
        pickle.dump(str_or_obj, f_obj)
    f_obj.close()


def exists(thing, namespace):
    """checks if a variable/object/instance exists in the given namespace
    
    :type thing: ``str``
    :type namespace: ``dict``
    :rtype: ``bool``
    """
    if thing in namespace:
        return True
    else:
        return False
