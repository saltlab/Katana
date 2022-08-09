import os
import re
import github
import glob
import json

AST_TYPE = "SHIFT"

def create_folder_list(out_file):
    DATA_HOMES = get_data_homes()

    open(out_file, "w").close()

    for DATA_HOME in DATA_HOMES:
        with open(out_file, "a") as f:
            f.write(DATA_HOME + "\n" + "-"*100 + "\n")

        path = DATA_HOME + "/*"
        _dirs = ""
        for _dir in sorted(glob.glob(path)):
           _dirs += _dir.replace(DATA_HOME,"")  + "\n" 

        with open(out_file, "a") as f:
            f.write(_dirs + "\n")
    
def check_api_tokens():
    NUM_ACCESS_TOKENS = int(os.environ['NUM_ACCESS_TOKENS'])
    broken = False

    for i in range(0, NUM_ACCESS_TOKENS):
        g = github.Github(os.environ['TOKEN_'+str(i)])
        rate = g.rate_limiting
        if rate[1] == 60:
            print("token", i, "broken")
            broken = True
        else:
            print(rate[1])

    return broken

def get_data_homes():
    try:
        DATA_HOME = os.environ['DATA_HOME']
        DATA_HOMES = [DATA_HOME]
    except KeyError as e:
        DATA_HOME1 = os.environ['DATA_HOME1']
        DATA_HOME2 = os.environ['DATA_HOME2']
        DATA_HOMES = [DATA_HOME1, DATA_HOME2]

    return DATA_HOMES

def data_itr():
    DATA_HOMES = get_data_homes()

    for DATA_HOME in DATA_HOMES:
        path = DATA_HOME + "/*"
        for _dir in sorted(glob.glob(path)):
            reg = re.escape(DATA_HOME) + r"([0-1][0-9])-([0-3][0-9])-(201[8-9]):([0-2][0-9])"
            m = re.match(reg, _dir)

            if not m:
                continue 

            month = m.group(1)
            day = m.group(2)
            year = m.group(3)
            hour = m.group(4)

            yield (month, day, year, hour, _dir)

def get_folder_name(_dir_tup):
    month, day, year, hour, _dir = _dir_tup
    return month+"-"+day+"-"+year+":"+hour

def entry_itr(fname):
    if os.path.exists(fname):
        with open(fname, 'r') as f:
            db = json.load(f)

        for entry in db:
            yield entry

def get_prefix(fname):
    return fname[:fname.rfind(".js")]

def get_ast_fname(fname):
    return AST_TYPE + "_" +  get_prefix(fname) + ".json"

def get_source(path, _id, fname):
    babel_file = os.path.join(path, _id, get_prefix(fname) + "_babel.js")
    js_file = os.path.join(path, _id, fname)

    if os.path.isfile(babel_file):
        js_file = babel_file

    return js_file

def check_dups(fname):
    ids = list(entry_itr(fname))
    return len(ids) == len(set(ids))

def _counter(_dict):
    yield 1

    for _, v in _dict.items():
        if isinstance(v, dict):
            for x in _counter(v):
                yield x

        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    for x in _counter(item):
                        yield x

def ast_size(_dict):
    return sum(_counter(_dict))
