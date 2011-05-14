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
