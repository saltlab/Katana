import os, sys, json, csv
import pandas as pd

SEPARATOR = '!#@$'


class AstNode():
    def __init__(self, node_type, value=None):
        self.node_type = node_type
        self.value = value
        self.index = None
        self.parent = None
        self.children = []

    @property
    def is_leaf(self):
        return len(self.children) == 0

    def add_child(self, ch_node, pos=None):
        assert ch_node.parent is None
        if pos is None:
            self.children.append(ch_node)
        else:
            self.children.insert(pos, ch_node)
        ch_node.parent = self

    def child_rank(self, ch_node):
        for i, ch in enumerate(self.children):
            if ch.index == ch_node.index:
                return i
        return None

    def remove_child(self, ch_node):
        found = False
        for i, ch in enumerate(self.children):
            if ch.index == ch_node.index:
                found = True
                del self.children[i]
                break
        assert found

class AST():
    def __init__(self):
        self.nodes = []
        self.root_node = None
        self._edits_made = []

    def append_edit(self, edit):
        if not hasattr(self, '_edits_made'):
            self._edits_made = []
        self._edits_made.append(edit)

    def get_edits(self):
        if not hasattr(self, '_edits_made'):
            return []
        return self._edits_made

    @property
    def num_nodes(self):
        return len(self.nodes)

    def add_node(self, ast_node):
        ast_node.index = self.num_nodes
        self.nodes.append(ast_node)

    def new_node(self, node_type, value):
        ast_node = AstNode(node_type=node_type, value=value)
        self.add_node(ast_node)
        return ast_node

    def remove_node(self, ast_node):
        p = ast_node.parent
        ast_node.parent = None
        assert p is not None
        p.remove_child(ast_node)

    def _relabeling(self, node):
        self.add_node(node)
        for ch in node.children:
            ch.parent = node
            self._relabeling(ch)

    def reset_index(self):
        self.nodes = []
        self._relabeling(self.root_node)

def get_bug_prefix(buggy_file):
    fname = buggy_file.split('/')[-1] # e.g. SHIFT_01-01-2019:00_6_0selectors_buggy.json
    return '_'.join(fname.split('_')[:-1]) # SHIFT_01-01-2019:00_6_0selectors

def build_shift_node_ast_from_json(json_node, parent_node, ast):
    if isinstance(json_node, dict):
        assert 'type' in json_node
        value = str(json_node['value']) if 'value' in json_node else None
        ast_node = ast.new_node(node_type=json_node['type'], value=value)
        for key in json_node:
            if key == 'type' or key == 'value':
                continue
            if isinstance(json_node[key], dict):                
                ch_node = build_shift_node_ast_from_json(json_node[key], ast_node, ast)
                ch_node.node_type = key + SEPARATOR + ch_node.node_type
            elif isinstance(json_node[key], list):
                ch_node = ast.new_node(key, value=None)
                build_shift_node_ast_from_json(json_node[key], ch_node, ast)
            else:
                value = None if json_node[key] is None else str(json_node[key])
                ch_node = ast.new_node(key, value=value)
            ast_node.add_child(ch_node)
        return ast_node
    elif isinstance(json_node, list):
        assert parent_node is not None
        for d in json_node:
            if isinstance(d, dict):
                ch_node = build_shift_node_ast_from_json(d, None, ast)
            else:
                assert d is None
                ch_node = ast.new_node('None', value=None)
            parent_node.add_child(ch_node)
    else:
        raise NotImplementedError



def build_shift_node_ast(fname):
    with open(fname, 'r') as f:
        try:
            root_node = json.load(f)
        except (json.decoder.JSONDecodeError, RecursionError) as e:
            return None

        ast = AST()
        root = build_shift_node_ast_from_json(root_node, None, ast)
        ast.root_node = root
    return ast

def make_graph_edits(root_path, file_tuple, writer):
    f_bug, f_bug_src, f_fixed, f_diff = file_tuple

    sample_name = get_bug_prefix(f_bug) # e.g. 'SHIFT_01-01-2019:00_6_0selectors'

    try:
        ast_bug = build_shift_node_ast(f_bug)
        ast_fixed = build_shift_node_ast(f_fixed)
    except FileNotFoundError:
        return

    try:
        with open(os.path.join(root_path, f_diff), 'r') as f:
            text = f.read()
            try:
                jsonified = json.loads(text)
            except:
                return
    except FileNotFoundError:
        return
        
    writer.writerow([f_bug_src.split('/')[-1], ast_bug.num_nodes, ast_fixed.num_nodes, len(jsonified), ','.join(map(lambda x: x['op'], jsonified))])

    return file_tuple, (ast_bug, ast_fixed)

def code_group_generator(data_root, prefix_list=None, file_suffix=['_buggy.json', '_buggy.js', '_fixed.json', '_ast_diff.txt']):
    files = os.listdir(data_root)
    tuples = []
    for fname in files:
        abs_path = os.path.join(data_root, fname)

        if os.path.isdir(abs_path):
            for t in code_group_generator(abs_path, prefix_list, file_suffix):
                tuples.append(t)
        elif fname.endswith(file_suffix[0]):
            prefix = fname.split(file_suffix[0])[0] # e.g. 'SHIFT_01-01-2019:00_6_0selectors'
            if prefix_list is not None and prefix not in prefix_list:
                continue
            local_names = []
            for suff in file_suffix:
                if (suff == "_buggy.js" or suff == '_ast_diff.txt'):
                    my_prefix = prefix.replace("SHIFT_", "") # e.g. '01-01-2019:00_6_0selectors'
                else:
                    my_prefix = prefix
                local_names.append(os.path.join(data_root, my_prefix + suff))
                # e.g. ['SHIFT_01-01-2019:00_6_0selectors_buggy.json', '01-01-2019:00_6_0selectors_buggy.js', 'SHIFT_01-01-2019:00_6_0selectors_fixed.json', 'SHIFT_01-01-2019:00_6_0selectors_ast_diff.txt']
            tuples.append(tuple(local_names))
    return tuples

if __name__ == '__main__':
    dir = sys.argv[1]
    csv_file_name = sys.argv[2]
    pkl_dir = sys.argv[3]

    train_file = open(pkl_dir + '/train.txt', 'r')
    train_set = set(train_file.read().split('\n'))
    test_file = open(pkl_dir + '/test.txt', 'r')
    test_set = set(test_file.read().split('\n'))
    val_file = open(pkl_dir + '/val.txt', 'r')
    val_set = set(val_file.read().split('\n'))

    prefix_list = list(train_set) + list(test_set) + list(val_set)
    
    with open(csv_file_name, 'w', newline='') as myfile:
        writer = csv.writer(myfile, quoting=csv.QUOTE_ALL)
        writer.writerow(['Buggy file', 'Buggy file nodes', 'Fixed file nodes', 'Difference in nodes', 'Fix types'])
        for file_gen in code_group_generator(dir, prefix_list=prefix_list):
            make_graph_edits(dir, file_gen, writer)
    
        df = pd.read_csv(csv_file_name)
        print(df.describe(include='all'))
