#!/usr/bin/env python3
import json
import os
import sys
import glob
import utils
import multiprocessing as mp

'''
set range_starts = None for fine grained statistics 
(prints number of samples per each # of AST diffs)
'''

range_starts = [0,1,2,10,20,50,100]
#range_starts = None 

def get_idx(range_starts, num_diffs):
    for i in range(0, len(range_starts)):
        idx = range_starts[i]
        if num_diffs <= idx:
            return idx

    return "101+" 

def collect_result(res):
    global num_downloaded 
    num_downloaded = res

def get_num_downloaded(_dir_tup):
    month, day, year, hour, _dir = _dir_tup

    if os.path.exists(os.path.join(_dir, "num_downloaded")):
        with open(os.path.join(_dir, "num_downloaded"), "r") as f:
            num_down = f.read()
    else:
        num_down = len(glob.glob(os.path.join(_dir, "*/*.js")))

        if os.path.exists(os.path.join(_dir, ".done")):
            with open(os.path.join(_dir, "num_downloaded"), "w") as f:
                f.write(str(num_down))
    
    return int(num_down)

def print_dicts(month, year):
    print(month+"/"+year)
    print("=" * 43)
    #pushes
    total_files = 0
    total_push = 0
    total_downloaded = 0
    
    ast_diffs = {}

    if range_starts:
        #coarse grained statistics
        for num in range_starts:
            ast_diffs[str(num)] = 0

        ast_diffs["101+"] = 0

    for k, v in master_dict.items():
        if master_dict[k]["num_downloaded"] == 0: continue

        print("-" * 43)
        print(k[k.rfind("/")+1:])
        print("-" * 43)
        total_files += master_dict[k]["num_files"]
        total_push += master_dict[k]["num_push"]
        total_downloaded += master_dict[k]["num_downloaded"]

        for k2, v2 in v.items():
            if k2 == "dir" or k2 == "fname": continue

            if not isinstance(v2, dict):
                print("{0:35}: {1:>6}".format(k2, v2))
            else:
                total_count = 0
                for num_diffs, count in sorted(v2.items()):
                    idx = str(get_idx(range_starts, num_diffs)) if range_starts else num_diffs

                    if not idx in ast_diffs:
                        assert not range_starts
                        ast_diffs[idx] = 0

                    ast_diffs[idx] += count

    print("=" * 43)
    print("Total")
    print("-" * 43)
    print("{0:35}: {1:>6}".format("total_files", total_files))
    print("{0:35}: {1:>6}".format("total_push", total_push))
    print("{0:35}: {1:>6}".format("total_downloaded", total_downloaded))
    
    print("-" * 43)
    print("{0:35}: {1:>6}".format("Num AST diffs", "count"))
    print("-" * 43)

    prev = -1 
    for k, v in ast_diffs.items():
        key = str(prev+1)+"-"+k if range_starts else k

        print("{0:35}: {1:>6}".format(key, v))

        if range_starts and k.isdigit():
            prev = int(k)

    
def get_stats(stat):
    num_ast = {}

    db = list(utils.entry_itr(stat["fname"]))
    
    files_changed = [entry['files_changed'] for entry in db]
    num_push = len(files_changed)
    num_files = sum([len(fs) for fs in files_changed])

    num_ast_diffs = [f["metadata"]["num_ast_diffs"] for fs in files_changed for f in fs]
    for num_diffs in num_ast_diffs:
        if num_diffs not in num_ast.keys(): 
            num_ast[num_diffs] = 1
        else:
            num_ast[num_diffs] += 1
    
    stat["num_files"] = num_files
    stat["num_push"] = num_push
    stat["num_ast"] = num_ast

    return stat

master_dict = {}
master_results = []

pool = mp.Pool(30)

_dirs = list(utils.data_itr())

ast_diffs = [os.path.join(_dir[4], utils.get_folder_name(_dir) + "_master_bug_metadata.json") for _dir in _dirs]

pool.map_async(get_num_downloaded, _dirs, callback=collect_result)

pool.close()
pool.join()

stats = [{"num_downloaded": num_downloaded[i], "dir": _dirs[i][4], "fname": ast_diffs[i]} for i in range(0, len(num_downloaded))]

pool = mp.Pool(30)
results = pool.map(get_stats, stats)
master_results += results

pool.close()
pool.join()

for result in master_results:
    if result:
        master_dict[result["dir"]] = result

if _dirs:
    month = _dirs[0][0]
    year = _dirs[0][2]
    print_dicts(month, year)

