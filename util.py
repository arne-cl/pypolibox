# Author: Arne Neumann <arne-neumann@web.de>

"""
The C{util} module contains a number of 'bread and butter' functions that are 
needed to run pypolibox, but are not particularly interesting (e.g. format 
converters, existence checks etc.).
"""

import re

def ensure_utf8(string):
    """
    ensures that a string does not use unicode but UTF8
    """
    if type(string) == unicode:
        string = string.encode("UTF8")
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
    """
    item = re.compile("\[(.*?)\]")
    items = item.findall(sql_array)
    item_set = set()
    for i in items:
        item_set.add(i)
    return item_set

def exists(thing, namespace):
    '''checks if a variable/object/instance exists in the given namespace
    
    @type thing: C{str}
    @type namespace: C{dict}
    @rtype: C{bool}
    '''
    if namespace.has_key(thing):
        return True
    else:
        return False

def messages_instance_to_list_of_message_instances(messages_instance):
    return [message for message in messages_instance.messages.values()]
    
def freeze_all_messages(message_list):
    '''
    makes all messages (C{FeatDict}s) immutable, which is necessary for turning
    them into sets
    '''
    for message in message_list:
        message.freeze()
    return message_list
