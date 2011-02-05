import networkx as nx
import random, string

OUTINDENT = '  '
OUTSPACER = ' '

class MyTree:
    def __init__(self, headnode, bucket=[]):
        self.graph = nx.Graph()
        self.graph.add_node(headnode)
        self.headnode = headnode
        self.dict = {}
        self.dict[headnode] = bucket
    def __str__(self):
        return self.write_hierarchy()

    def write_hierarchy(self, cfs = True):
        st = ''
        dir_graph = nx.dfs_tree(self.graph, source=self.headnode)
        
        def print_graph(graph, node, n):
            ret = OUTINDENT * n  + str(node) 
            if(cfs): ret += OUTSPACER + '[' + string.join(self.dict[node],',') + ']'
            ret += '\n'
            for c in graph.neighbors(node):
                ret += print_graph(graph, c, n+1)
            return ret

        return print_graph(dir_graph, self.headnode, 0)
    
    def add_subnode(self, parent, node, bucket=[]):
        self.graph.add_node(node)
        self.graph.add_edge(parent, node)
        self.dict[node] = bucket

    def distance(self, node1, node2):
        return nx.shortest_path_length(self.graph, node1, node2)

    def find_in_buckets(self, term):
        return filter(lambda x: term in self.dict[x], self.dict.keys())

    def clear_buckets(self):
        for f in self.dict:
            self.dict[f] = []

    def bucket_remove(self, term, val):
        if self.graph.has_node(term) and val in self.dict[term]:
            self.dict[term].remove(val)
        else:
            print "BUCKET REMOVE ERROR"
            return False

    def bucket_add(self, term, val):
        if self.graph.has_node(term):
            self.dict[term].append(val)
            return True
        else:
            print "bucket add Error: term -", term, "does not exist"
            return False

    def get_terms(self):
        return self.dict.keys()

    def get_feat_set(self):
        return list(set(self.get_feats()))

    def get_feats(self):
        ret = []
        for t in self.dict.values():
            ret += t
        return ret

    def non_empty_UDF(self):
        num = 0
        for x in self.dict:
            if not len(self.dict[x]) == 0 and x != self.headnode:
                num += 1
        return num
    
    def get_cfs(self, udf):
        return dict[udf]

    def get_parent(self, udf):
        dir_graph = nx.dfs_tree(self.graph, source=self.headnode)
        return dir_graph.predecessors(udf)
        

def read_hierarchy(infile):
    with open(infile, 'r') as f:
        readlines = f.readlines()

    chunks = readlines[0].strip().split(' - ')
    if len(chunks) > 1:
        bucket = chunks[1].strip()
        bucket = bucket[1:-1]
        bucket = bucket.split(',')
        if '' in bucket: bucket.remove('')
    else:
        bucket = []
    root = chunks[0]
    tree = MyTree(root, bucket = bucket)

    stack = [root]
    last_node = root
    indentation = 0
    for l in readlines[1:]:
        #l = l.lower()
        if l.strip() == '' or l.strip() == '\n':
            continue
        if l[:indentation] == indentation * '\t':
            l = l[indentation:]

            if l[0] == '\t':
                indentation += 1
                l = l[1:]
                stack.append(last_node)
        else:
            while not l[:indentation] == indentation * '\t':
                indentation -= 1
                stack.pop()
        chunks = l.strip().split(' - ')
        term = chunks[0].strip()
        if len(chunks) > 1:
            bucket = chunks[1]
            bucket = bucket[1:-1]
            bucket = bucket.split(',')
            if '' in bucket: bucket.remove('')
        else:
            bucket = []
        tree.add_subnode(stack[-1], term, bucket = bucket)
        last_node = term

    return tree

def write_hierarchy(tree, outfile):
    pass

def random_tree(infile):
    tree = read_hierarchy(infile)
    feats = tree.get_feat_set()
    terms = tree.get_terms()
    tree.clear_buckets()

    for f in feats:
        t = random.choice(terms)
        tree.bucket_add(t, f)

    return tree

def not_placed_tree(infile):
    tree = read_hierarchy(infile)
    feats = tree.get_feat_set()
    tree.clear_buckets()

    for f in feats:
        tree.bucket_add(tree.headnode, f)

    return tree
        
