import string

def all_words(ls):
    words = set([])
    
    for t in map(string.split, ls):
        words |= set(t)

    return words

def index_sets(a): #TODO: delete
    """
    cartesian product (reimplementation of itertools.product)
    """
    r=[[]]
    for x in a:
        t = []
        for y in x:
            for i in r:
                t.append(i+[y])
        r = t
    return map(tuple, r)

def flatten(lst):
    """
    Flatten a list that contains nested lists
    
    @param lst: The source list
    @type lst: list
    @return: flat list
    """
    ret = []

    for s in lst:
        map(lambda x: ret.append(x), s)

    return ret

#K_Subsets and K_Subsets_I taken from http://code.activestate.com/recipes/500268/
def k_subsets_i(n, k):
    '''
    Yield each subset of size k from the set of intergers 0 .. n - 1
    n -- an integer > 0
    k -- an integer > 0
    '''
    # Validate args
    if n < 0:
        raise ValueError('n must be > 0, got n=%d' % n)
    if k < 0:
        raise ValueError('k must be > 0, got k=%d' % k)
    # check base cases
    if k == 0 or n < k:
        yield set()
    elif n == k:
        yield set(range(n))

    else:
        # Use recursive formula based on binomial coeffecients:
        # choose(n, k) = choose(n - 1, k - 1) + choose(n - 1, k)
        for s in k_subsets_i(n - 1, k - 1):
            s.add(n - 1)
            yield s
        for s in k_subsets_i(n - 1, k):
            yield s

def k_subsets(s, k):
    '''
    Yield all subsets of size k from set (or list) s
    s -- a set or list (any iterable will suffice)
    k -- an integer > 0
    '''
    s = list(s)
    n = len(s)
    for k_set in k_subsets_i(n, k):
        yield set([s[i] for i in k_set])

def lcount(string, c):
    count = 0
    while string[0] == c:
        count += 1
        string = string[1:]
    return count

def first_index(enum, func):
    for n in range(len(enum)):
        if func(enum[n]):
            return n
    return len(enum)
