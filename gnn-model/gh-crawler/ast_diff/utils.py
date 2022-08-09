from ntpath import basename
import os
import json
import subprocess

CRAWLER_HOME = os.environ['CRAWLER_HOME']
babel_script = os.path.join(CRAWLER_HOME, "ast_diff", "babel.sh")

def log_failure(failed_file, b_fname, f_fname):
    with open(failed_file, "a") as f:
        f.write(b_fname + " " + f_fname + "\n")

def cleanup(results, func_to_write, processed, is_processed_func, master_file, processed_file):
    num_failed = sum([entry[1] for entry in results])
    ast_results = [entry[0] for entry in results if entry[0]]

    print(len(ast_results), "processed,", num_failed, "failed")

    write_to_processed(ast_results, func_to_write, processed_file)

    for bug in ast_results:
        assert bug["files_changed"] and not is_processed_func(processed, bug)

    if os.path.exists(master_file):
        with open(master_file) as f:
            json_array = json.load(f)
    else:
        json_array = []

    json_array = json_array + ast_results
    json_array = sorted(json_array, key=lambda bug: int(bug["id"]))

    with open(master_file, 'w') as outfile:
        print("wrote to master_bug", master_file)
        #print("adding: ", json_array)
        json.dump(json_array, outfile, indent=4, sort_keys=True)


def write_to_processed(processed, func_to_write, processed_file):
    to_write = ""

    for elem in processed:
        to_write += func_to_write(elem) + "\n"

    if os.path.exists(processed_file):
        with open(processed_file, "a") as f:
            f.write(to_write)

    else:
        with open(processed_file, "w") as f:
            f.write(to_write)

def get_prefix(filename):
    tmp = basename(filename)

    suffixes = ["_buggy.js", "_buggy_babel.js", "_fixed.js", "_fixed_babel.js"]

    itr = 0
    end = -1
    while end < 0 and itr < len(suffixes):
        end = tmp.rfind(suffixes[itr])
        itr += 1

    return tmp[0:end]

def get_ast_diff(b_fname, f_fname, ast_name, out_path):

    b_SHIFT_name = "SHIFT_" + b_fname[0:b_fname.rfind(".")] + ".json"
    f_SHIFT_name = "SHIFT_" + f_fname[0:f_fname.rfind(".")] + ".json"

    full_b_SHIFT = os.path.join(out_path, b_SHIFT_name)
    full_f_SHIFT = os.path.join(out_path, f_SHIFT_name)
    js_script = os.path.join(CRAWLER_HOME, "ast_diff", "run_json_diff.js")

    try:
        args = ["node", js_script, full_b_SHIFT, full_f_SHIFT, ast_name]
        subprocess.call(args)

    except Exception as e:
        #print(e)
        #print("json diff failed")
        return -1

    with open(ast_name, "r") as f:
        try:
            obj = json.load(f)
        except RecursionError as e:
            print("JSON too big")
            return -1

    return len(obj)

def get_asts(b_fname, f_fname, in_path, out_path, bug_metadata):
    b_SHIFT_name = "SHIFT_" + b_fname[0:b_fname.rfind(".")] + ".json"
    f_SHIFT_name = "SHIFT_" + f_fname[0:f_fname.rfind(".")] + ".json"
    full_b_SHIFT = os.path.join(out_path, b_SHIFT_name)
    full_f_SHIFT = os.path.join(out_path, f_SHIFT_name)

    ret1 = gen_shift_AST(os.path.join(in_path, b_fname), full_b_SHIFT)
    ret2 = gen_shift_AST(os.path.join(in_path, f_fname), full_f_SHIFT)

    if ret1 or ret2: return ret1, ret2

    f = {}
    f["buggy_ast"] = b_fname
    f["fixed_ast"] = f_fname

    bug_metadata["files_changed"] = [f]

    return ret1, ret2

def get_not_processed(whole, processed, is_processed_func):
    return [elem for elem in whole if not is_processed_func(processed, elem)]

def get_already_processed(processed_file):
    if os.path.exists(processed_file):
        with(open(processed_file, "r")) as f:
            processed_pairs = f.read()
            processed_pairs = processed_pairs.splitlines()
    else:
        print(processed_file, "does not exist")
        processed_pairs = []

    return processed_pairs

def gen_babel(in_path, in_name, out_name):
    args = [babel_script, in_path, in_name, out_name]

    subprocess.call(args, stderr=subprocess.DEVNULL)

    with open(os.path.join(in_path, out_name)) as f:
        content = f.read()

    return content

def gen_shift_AST(fname, shift_ast_name):
    script = os.path.join(CRAWLER_HOME, "ast_diff", "gen_shift_AST.js")

    try:
        args = ["node", script, fname, shift_ast_name]
        s = subprocess.check_output(args, stderr=subprocess.DEVNULL)

    except subprocess.CalledProcessError:
        try:
            in_name = fname[fname.rfind("/")+1:]
            in_path = fname[0:fname.rfind("/")+1]
            out_name = in_name[0:in_name.rfind(".js")] + "_babel.js"

            content = gen_babel(in_path, in_name, out_name)

            if not content:
                os.remove(os.path.join(in_path, out_name))
                #print("babel conversion failed")
                return 1

            args = ["node", script, os.path.join(in_path, out_name), shift_ast_name]
            s = subprocess.check_output(args, stderr=subprocess.DEVNULL)

            os.remove(os.path.join(in_path, out_name))

        except subprocess.CalledProcessError:
            os.remove(os.path.join(in_path, out_name))
            #print("error generating shift ast for:", fname)
            return 1

    if len(s) > 0:
        print("error generating shift ast for:", fname)
        return 1

    return 0
