import argparse
import json
import re
import sys
import glob
import time
import math
import os
import subprocess
import traceback
import logging
import multiprocessing as mp
import github
import requests

'''
usage: Script to download files based on commit data [-h]
                                                     [--input_file INPUT_FILE]
                                                     [--output_folder OUTPUT_FOLDER]

optional arguments:
  -h, --help            show this help message and exit
  --input_file INPUT_FILE
                        file containing commit data
  --output_folder OUTPUT_FOLDER
                        folder to put downloaded files
'''

parser = argparse.ArgumentParser("Script to download files based on commit data")
parser.add_argument('--input_file', dest='input_file', default="", help='file containing commit data')
parser.add_argument('--output_folder', dest='output_folder', default="", help='folder to put downloaded files')

# system variables
DATA_PATH = os.path.join(os.environ['DATA_HOME'], "data")

NUM_ACCESS_TOKENS = int(os.environ['NUM_ACCESS_TOKENS'])

#mp variables
logger = mp.log_to_stderr(logging.DEBUG)
NUM_TOKENS_PER_THREAD = 1
NUM_THREADS = 3
token_idxs = mp.Array('i', NUM_ACCESS_TOKENS, lock=True)

# parse json file to get info for each bug
def parse(line):
    return tuple([str(line[x]) for x in ["repo_url", "repo_name", "fixed_hash", "buggy_hash", "commit_msg", "pushed_at"]])

def get_list_of_commit_pairs(filename):
    assert os.path.exists(filename)

    with open(filename) as f:
        array = json.load(f)
        return [parse(item) for item in array]

def update_files(err_shas, json_array, downloaded_file, output_json, err_results):
    str_to_write = ""
    for fixed_sha in err_shas:
        str_to_write += fixed_sha + "\n"

    with open(downloaded_file, "a+") as f:
        f.write(str_to_write)

    with open(os.path.join(output_json), 'w') as outfile:  
        json.dump(json_array, outfile, indent=4, sort_keys=True)

    logger.info("wrote " +  str(len(err_shas)) +  " err shas and " +  str(len(json_array)) +  " results to files " +  output_json + " " + downloaded_file)

def update_tokens(token_list, repo_path, err_shas, json_array, downloaded_file, output_json, err_results):
    for i, token in enumerate(token_list):

        if not token["live"] and token["time_ready"] > time.time():
            continue
        elif not token["live"] and token["time_ready"] < time.time():
            token["live"] = True
            token["time_ready"] = time.time()

        g = github.Github(token["token"])

        try: 
            repo = g.get_repo(repo_path) 
            return g, repo

        except github.GithubException as exc:
            if "API rate limit exceeded" in str(exc):
                print(exc)
                logger.info("token " + token["token"] +  " is now dead")
                update_files(err_shas, json_array, downloaded_file, output_json, err_results)
                token["live"] = False
                token["time_ready"] = g.rate_limiting_resettime
                continue

            else:
                #repo_issue
                return g, None

        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as exc:
            print("connection error")
            #try again
            i -= 1

    lowest_wait = min([token["time_ready"] for token in token_list])

    sleep_time = math.ceil(lowest_wait - time.time())
    logger.info("sleeping for" + str(sleep_time) + "seconds")
    if not sleep_time < 0:
        time.sleep(sleep_time)

    return update_tokens(token_list, repo_path, err_shas, json_array, downloaded_file, output_json, err_results)


def get_json_obj(push_event, global_id, tokens_dict, folder_path, json_array, err_shas, downloaded_file, output_json, err_results):
    fixed_sha = push_event[2]

    try:
        path_reg = re.compile(r"https:\/\/github.com\/([^\/]*\/[^\/]*).git")
        repo_path = path_reg.match(push_event[0]).group(1)
    except (IndexError, AttributeError):
        err_results.append(-2)
        err_shas.append(fixed_sha)
        return -2

    g, repo = update_tokens(tokens_dict, repo_path, err_shas, json_array, downloaded_file, output_json, err_results)
    assert g

    if not repo:
        err_results.append(-5)
        err_shas.append(fixed_sha)
        return -5

    file_json_objs = []
    try:
        lan = repo.get_languages()

        if 'JavaScript' not in lan: 
            err_shas.append(fixed_sha)
            err_results.append(-1)
            return -1

        repo = repo.get_commit(push_event[2])
        if len(repo.parents) == 0:
            err_shas.append(fixed_sha)
            err_results.append(-6)
            return -6

        files = repo.files
        if files is None:
            err_shas.append(fixed_sha)
            err_results.append(-7)
            return -7

        file_id = 0
        bug_path = os.path.join(folder_path, str(global_id))

        if not os.path.isdir(bug_path):
            os.mkdir(bug_path)

        fnames = [f.filename for f in files]
        files_to_download = [filename for filename in fnames if filename.split('.')[-1] == 'js' and "umd.js" not in filename and "min.js" not in filename]

        url = push_event[0].split(".git")[0]

        for filename in files_to_download:
            str_file_id = str(file_id)
            raw_file_name = filename.split(".js")[0].split("/")[-1]
            fixed_name = str_file_id + raw_file_name + '_fixed.js'
            buggy_name = str_file_id + raw_file_name+ '_buggy.js'
            ast_name = str_file_id + raw_file_name + '_ast_diff.txt'

            download = download_files(url.replace("github.com", "raw.githubusercontent.com"), push_event[2], push_event[3], filename, fixed_name, buggy_name, bug_path)

            if download == 0:
                json_obj = get_file_json(filename, fixed_name, buggy_name, ast_name)
                file_json_objs.append(json_obj) 
                file_id += 1
            else:
                break

        if len(file_json_objs) > 0:
            ret = get_push_json(push_event, len(files), global_id, file_json_objs, push_event[5])
            json_array.append(ret)
            logger.info(str(len(file_json_objs)) + " downloaded")
            return ret

        id_folder = os.path.join(folder_path, str(global_id)) #remove the folder if we didn't download anything into them
        if os.path.isdir(id_folder) and len(os.listdir(id_folder)) == 0:
            os.rmdir(id_folder)

    except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError, github.GithubException):
        err_shas.append(fixed_sha)
        err_results.append(-3)
        return -3
    
    err_shas.append(fixed_sha)
    err_results.append(-4)
    return -4


def get_file_json(filename, fixed_name, buggy_name, ast_name):
    data = {}
    data['buggy_ast'] = buggy_name + '_ast.txt'
    data['buggy_file'] = buggy_name 
    data['fixed_ast'] = fixed_name + '_ast.txt'
    data['fixed_file'] = fixed_name 
    data['ast_diff_file'] = ast_name
    data['metadata'] = {}
    data['metadata']['file'] = filename
    data['metadata']['num_ast_diffs'] = None
    return data

# "repo_url", "repo_name", "fixed_hash", "buggy_hash", "commit_msg"
# get diff url for each commit 
def get_push_json(push_event, num_files_changed, bug_id, file_json_list, timestamp):
    repo_url = push_event[0]
    fixed_sha = push_event[2]
    url = repo_url.split(".git")[0] + "/commit/" + fixed_sha

    data = {}
    data["files_changed"] = file_json_list
    data['id'] = bug_id
    data['metadata'] = {}
    data['metadata']['buggy_sha'] = push_event[3]
    data['metadata']['commit_message'] = push_event[4]
    data['metadata']['commit_url'] = url
    data['metadata']['fixed_sha'] = fixed_sha
    data['metadata']['num_files_changed'] = num_files_changed
    data['metadata']['repo_name'] = push_event[1]
    data['metadata']['repo_url'] = repo_url
    data['metadata']['pushed_at'] = timestamp
    return data


def download_files(repo_url, fixed_hash, buggy_hash, filename, fixed_name, buggy_name, bug_path):
    #download corresponding files
    fixed_file_url = repo_url + "/" + fixed_hash + "/" + filename
    buggy_file_url = repo_url + "/" + buggy_hash + "/" + filename
    
    fixed_file_out = bug_path + "/" + fixed_name
    buggy_file_out = bug_path + "/" + buggy_name

    FNULL = open(os.devnull, 'w')

    try:
        subprocess.check_output(["wget", "-O", fixed_file_out, fixed_file_url], stderr=FNULL)
    except subprocess.CalledProcessError:
        if os.path.isfile(fixed_file_out):
            os.remove(fixed_file_out)

        return -1

    try:
        subprocess.check_output(["wget", "-O", buggy_file_out, buggy_file_url], stderr=FNULL)
    except subprocess.CalledProcessError:
        if os.path.isfile(fixed_file_out):
            os.remove(fixed_file_out)

        if os.path.isfile(buggy_file_out):
            os.remove(buggy_file_out)

        return -1

    return 0

def process_folder(folder_id, helper_func, input_file=None, output_folder=None):
    global_id = 0

    if output_folder:
        folder_path = output_folder
        data = input_file
        output_json = os.path.join(output_folder, "bug.json")
        downloaded_file = os.path.join(folder_path, "downloaded.txt")
    else:
        folder_path = os.path.join(DATA_PATH, folder_id)
        data = os.path.join(folder_path, folder_id + "-push-events.json")
        output_json = os.path.join(folder_path, folder_id + "_bug.json")
        downloaded_file = os.path.join(folder_path, folder_id + "_downloaded.txt")

    if os.path.exists(os.path.join(folder_path, ".done")): 
        logger.info("already downloaded entire hour")
        return

    if not os.path.exists(downloaded_file):
        print(downloaded_file, "does not exist")
        downloaded_shas = []
    else:
        with open(downloaded_file, "r") as f:
            downloaded_shas = f.read()
            downloaded_shas = downloaded_shas.splitlines()

    #get pairs of buggy, fixed commits
    push_event_pairs = get_list_of_commit_pairs(data)
    included_shas = []

    if os.path.exists(output_json):
        with open(output_json) as f:
            json_array = json.load(f)

        if len(json_array) > 0:
            global_id = json_array[-1]["id"] + 1
            included_shas = [bug['metadata']['fixed_sha'] for bug in json_array]
    else:
        json_array = []
    
    not_downloaded_pairs = [pair for pair in push_event_pairs if not pair[2] in downloaded_shas and pair[2] not in included_shas]
    if len(not_downloaded_pairs) == 0:
        logger.info("already downloaded entire hour")
        
        with open(os.path.join(folder_path, ".done"), "w") as f:
            f.write("")

        logger.info("wrote to" +  os.path.join(folder_path, ".done"))
        return


    err_shas = []
    err_results = []

    tokens_dict = []
    #with lock:
    i = 0
    try:
        while len(tokens_dict) < NUM_TOKENS_PER_THREAD:
            if token_idxs[i]:
                token_idxs[i] = 0
                d = {}
                d["token"] = tokens[i]
                d["idx"] = i
                d["live"] = True
                d["time_ready"] = time.time()
                tokens_dict.append(d)

            i += 1

    except Exception as e:
        print("tokens dict", tokens_dict)
        print("token idxs", token_idxs)
        print("tokens", tokens)
        print("i:", i)
        print(e)
        sys.exit(1)

    logger.info("got our tokens" + str([d["idx"] for d in tokens_dict]))
    try:
        results = []
        for pair in not_downloaded_pairs:
            res = helper_func(pair, global_id, tokens_dict, folder_path, json_array, err_shas, downloaded_file, output_json, err_results)
            if isinstance(res, dict):
                results.append(res)
                global_id += 1

    except Exception as e:
        print("exception in get_json_obj")
        traceback.print_exc(limit=3, file=sys.stdout)
        sys.exit(1)
    
    results = [result for result in results if isinstance(result, dict)]

    not_js = 0
    broken_repo = 0 
    no_repo = 0
    connect_problem = 0
    other = 0
    no_files = 0
    no_par = 0
    for res in err_results:
        if res == -1:
            not_js += 1
        elif res == -2:
            broken_repo += 1
        elif res == -3:
            connect_problem += 1
        elif res == -4:
            other += 1
        elif res == -5:
            no_repo += 1
        elif res == -6:
            no_par += 1 
        elif res == -7:
            no_files += 1


    logger.info("finished entire folder! " + str(folder_path) + " started with " +  str(len(not_downloaded_pairs)) +  " pairs: " +  str(len(results)) + " downloaded " +  str(not_js) +  " not js " +  str(broken_repo) + " broken repo path "+ str(connect_problem) + " connection problem " + str(other) +  " wget failed " + str(no_repo) +  " no repo " + str(no_par) + " no parent " + str(no_files) +  "no files")

    fixed_shas = [result['metadata']['fixed_sha'] for result in results]
    included_shas += fixed_shas

    update_files(err_shas, json_array, downloaded_file, output_json, err_results)

    for token in tokens_dict:
        idx = token["idx"]
        token_idxs[idx] = 1

args = parser.parse_args()

#access token
tokens = []
for i in range(0, NUM_ACCESS_TOKENS):
    tokens.append(os.environ['TOKEN_'+str(i)])

path = os.path.join(DATA_PATH, "*")


if args.input_file:
    folder_ids = [0]
    if not os.path.exists(args.output_folder):
        os.mkdir(args.output_folder)
else:
    _dirs = [_dir for _dir in sorted(glob.glob(path)) if os.path.isdir(_dir)]

    folder_ids = [_dir[len(path)-1:_dir.find("-", len(path))] + "-" + _dir[_dir.find("-", len(path))+1:_dir.find("-", _dir.find("-", len(path))+1)] + "-" + _dir[_dir.rfind("-")+1:_dir.find(":")] + ":" + _dir[_dir.find(":")+1:] for _dir in _dirs]

pool = mp.Pool(NUM_THREADS)

for i in range(0, NUM_ACCESS_TOKENS):
    token_idxs[i] = 1

for folder_id in folder_ids:
    results = pool.apply_async(process_folder, args=(folder_id, get_json_obj, args.input_file, args.output_folder, ))

results.get()
pool.close()
pool.join()

