import argparse
from collections import defaultdict
import json
import glob
import logging
import multiprocessing as mp
from ntpath import basename
import os
import time
import sys
import utils

'''
usage: get_ast_diff.py [-h] [--mode MODE] [--np NUM_PROCESSES]
                       input_folder output_folder

Generate asts and ast diffs from a corpus of buggy and fixed javascript pairs

positional arguments:
  input_folder        folder containing buggy and fixed javascript pairs
  output_folder       folder to put generated ASTs and AST diffs

optional arguments:
  -h, --help          show this help message and exit
  --mode MODE         Mode not accepted. Script can run in 'crawler' mode or
                      'standalone'. Crawler mode is used in conjunction with
                      the download_files script in this repo. Standalone
                      should be used for a single folder of buggy and fixed js
                      pairs.
  --np NUM_PROCESSES  number of processing for multiprocessing
'''

#GENOME_HOME = os.environ['GENOME_HOME']

logger = mp.log_to_stderr(logging.DEBUG)

DESC = 'Generate asts and ast diffs from a corpus of buggy and fixed javascript pairs'
parser = argparse.ArgumentParser(DESC)
parser.add_argument('--input_folder', default="", help='folder containing buggy and fixed javascript pairs')
parser.add_argument('--output_folder', default="", help='folder to put generated ASTs and AST diffs')

MODE_TEXT = """ Mode not accepted. Script can run in 'crawler' mode or 'standalone'.
                Crawler mode is used in conjunction with the download_files script in this repo.  
                Standalone should be used for a single folder of buggy and fixed js pairs."""

parser.add_argument('--mode', dest='mode', default="standalone", help=MODE_TEXT)

parser.add_argument("--np", dest="num_processes", type=int, help="# of processes", default=15)

def standalone(b_name, f_name, bug_meta, failed_file):
    failed = 0

    f = {}
    f["buggy_file"] = b_name
    f["fixed_file"] = f_name

    err_b, err_f = utils.get_asts(basename(b_name), basename(f_name), args.input_folder, args.output_folder, bug_meta)

    if err_b or err_f:
        failed = 1
        utils.log_failure(failed_file, b_name, f_name) 
        return None, failed

    ast_diff_fname = os.path.join(args.output_folder, utils.get_prefix(b_name) + "_ast_diff.txt")

    num_ast_diff = utils.get_ast_diff(basename(b_name), basename(f_name), ast_diff_fname, args.output_folder)

    bug_meta["files_changed"][0]["ast_diff_file"] = ast_diff_fname

    metadata = {}
    metadata["file"] = utils.get_prefix(b_name) + ".js"
    metadata["num_ast_diffs"] = num_ast_diff

    bug_meta["files_changed"][0]["metadata"] = metadata


    if num_ast_diff < 0:
        utils.log_failure(failed_file, b_name, f_name) 
        failed = 1
        print("json diff failed")

    return bug_meta, failed

def crawler(bug, folder_path, failed_file):
    files = bug["files_changed"]
    bug_id = bug["id"]

    num_failed = 0
    ast_files = []
    for f in files:
        fixed_name = f["fixed_file"]
        buggy_name = f["buggy_file"]
        ast_name = f["ast_diff_file"]

        bug_path = os.path.join(folder_path, str(bug_id))

        err_b, err_f = utils.get_asts(buggy_name, fixed_name, bug_path, bug_path, bug)

        if err_b or err_f:
            #print("generating the shift ast failed")
            num_failed = 1

            with open(failed_file, "a") as f:
                f.write(os.path.join(bug_path, buggy_name) + "\n")

            continue

        ast_diff_name = os.path.join(bug_path, "SHIFT_" + ast_name)
        num_ast_diff = utils.get_ast_diff(buggy_name, fixed_name, ast_diff_name, bug_path)

        if num_ast_diff >= 0:
            f['metadata']['num_ast_diffs'] = num_ast_diff

            ast_files.append(f)
        else:
            print("json diff failed")

            with open(failed_file, "a") as my_f:
                my_f.write(os.path.join(bug_path, buggy_name) + "\n")

            num_failed = 1
            continue

    bug["files_changed"] = ast_files

    if not ast_files:
        return None, num_failed

    #ast_results.append(bug)
    #jreturn num_failed
    return bug, num_failed

results = []

args = parser.parse_args()

if args.mode == "standalone":
    if not args.output_folder or not args.input_folder: 
        parser.print_help()
        sys.exit(1)

    if not os.path.isdir(args.output_folder): 
        os.mkdir(args.output_folder)

    master_json = os.path.join(args.output_folder, "master_bug_metadata.json")

    processed_file = os.path.join(args.output_folder, "processed.txt")
    failed_samples_file = os.path.join(args.output_folder, "failed.txt")

    if not os.path.exists(failed_samples_file):
        open(failed_samples_file, "x").close()

    processed_pairs = utils.get_already_processed(processed_file)

    f_all = glob.glob(args.input_folder + "/*.js")

    is_processed_func = lambda p, e: utils.get_prefix(e["files_changed"][0]["metadata"]["file"]) + ".js" in p if isinstance(e, dict) else utils.get_prefix(e) + ".js" in p
    pairs_to_process = utils.get_not_processed(f_all, processed_pairs, is_processed_func)

    if not pairs_to_process:
        print("Already processed entire folder")
        sys.exit(1)

    pairs = defaultdict(list)
    pool = mp.Pool(args.num_processes)

    #get pairs
    for f in pairs_to_process:
        prefix = utils.get_prefix(basename(f))
        pairs[prefix].append(f)

    count = 0
    for prefix, v in pairs.items():
        if(len(v) != 2):
            print(f'length of pair is: {v}')
            print('prefix is:' + prefix)
        assert len(v) == 2
        _b_name = v[0] if "_buggy" in v[0] else v[1]
        _f_name = v[1] if "_fixed" in v[1] else v[0]

        bug = {}
        bug["id"] = count

        pool.apply_async(standalone, args=(_b_name, _f_name, bug, failed_samples_file), callback=results.append)

        count += 1

    pool.close()
    pool.join()

    func_to_write = lambda elem: elem["files_changed"][0]["metadata"]["file"]
    utils.cleanup(results, func_to_write, processed_pairs, is_processed_func, master_json, processed_file)

elif args.mode == "crawler":

    DATA_HOME = os.environ['DATA_HOME']

    path = os.path.join(DATA_HOME, "*")
    for _dir in sorted(glob.glob(path)):
        if not 'month' in locals(): month = _dir[len(path)-1:_dir.find("-", len(path))]
        if not 'year' in locals(): year = _dir[_dir.rfind("-")+1:_dir.find(":")]

        idx = _dir.find("-", len(path))+1
        day = _dir[idx:_dir.find("-", idx)]
        hour = _dir[_dir.find(":")+1:]

        folder_id = month+"-"+day+"-"+year+":"+hour

        folder_path = os.path.join(DATA_HOME, folder_id)
        changed_file_json = os.path.join(folder_path, folder_id + "_bug.json")

        while not os.path.exists(changed_file_json):
            print("waiting for", changed_file_json)
            time.sleep(1800) #wait for the download to catch up

        master_json = os.path.join(folder_path, folder_id + "_master_bug_metadata.json")

        processed_file = os.path.join(folder_path, folder_id + "_processed.txt")
        failed_samples_file = os.path.join(folder_path, folder_id + "_failed.txt")

        if not os.path.exists(failed_samples_file):
            open(failed_samples_file, "x").close()

        processed_pairs = utils.get_already_processed(processed_file)

        with open(changed_file_json) as f:
            bug_array = json.load(f)

        while True:
            prev_bug_array = bug_array

            is_processed_func = lambda p, e: e["metadata"]["fixed_sha"] in processed_pairs

            pool = mp.Pool(args.num_processes)

            bug_array_not_processed = utils.get_not_processed(bug_array, processed_pairs, is_processed_func)
            if not bug_array_not_processed:
                print("already processed whole hour")
                break

            print(len(bug_array_not_processed))

            for sample in bug_array_not_processed:
                pool.apply_async(crawler, args=(sample, folder_path, failed_samples_file), callback=results.append)

            pool.close()
            pool.join()

            func_to_write = lambda elem: elem["metadata"]["fixed_sha"]
            utils.cleanup(results, func_to_write, processed_pairs, is_processed_func, master_json, processed_file)

            with open(changed_file_json) as f:
                try:
                    bug_array = json.load(f)
                except json.decoder.JSONDecodeError:
                    time.sleep(1)
                    bug_array = json.load(f)

            if len(bug_array) == len(prev_bug_array):
                break

else:
    print(MODE_TEXT)
    sys.exit(1)
