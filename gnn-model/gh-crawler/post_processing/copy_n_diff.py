#!/usr/bin/env python3
import json
import os
import sys
import glob
import subprocess
import utils
from tqdm import tqdm

if len(sys.argv) < 2:
    print("USAGE: python copy_n_diff.py [n]")
    sys.exit(1)

n = int(sys.argv[1])

DATA_HOMES = utils.get_data_homes()

rsync_fname = "/home/edinella/rsync_list_temp.txt"

def get_files(fname, path, folder_name):
    files = []

    for entry in utils.entry_itr(fname):
        _id = str(entry["id"])

        for f in entry["files_changed"]:
            if not f["metadata"]["num_ast_diffs"] == n: continue

            b_ast = utils.get_ast_fname(f["buggy_file"])
            f_ast = utils.get_ast_fname(f["fixed_file"])

            diff = "SHIFT_" + f["ast_diff_file"]
            
            prefix = folder_name + "_" + _id + "_"

            files.append((os.path.join(path, _id, b_ast), prefix+ b_ast))
            files.append((os.path.join(path, _id, f_ast), prefix + f_ast))
            files.append((os.path.join(path, _id, diff), prefix + diff))

            js_file = utils.get_source(path, _id, f["buggy_file"])

            files.append((js_file, folder_name + "_" + _id + "_" + js_file.replace(path + "/" +  _id + "/", "")))

    return files

if not os.path.exists(rsync_fname):
        open(rsync_fname, "w").close()

with open(rsync_fname, "r") as f:
    content = f.read()

for _dir_tup in tqdm(utils.data_itr()):

    folder_name = utils.get_folder_name(_dir_tup)

    _dir = _dir_tup[4]
    ast_diffs = os.path.join(_dir, folder_name + "_master_bug_shift.json")

    files = get_files(ast_diffs, _dir, folder_name)

    for f in files:
        if f[0] in content: continue

        with open(rsync_fname, "a") as f_io:
            f_io.write(f[0] + "\n" + f[1] + "\n")

