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
    
    our book database uses '[' and ']' to handle attributes w/ more than one value:
    e.g. authors = '[Noam Chomsky][Alan Touring]'

    this function turns those multi-value strings into a set with separate values
    """
    item = re.compile("\[(.*?)\]")
    items = item.findall(sql_array)
    item_set = set()
    for i in items:
        item_set.add(i)
    return item_set
