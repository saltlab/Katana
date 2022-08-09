import os
import json
import glob

GENOME_HOME = os.environ['GENOME_HOME']

path = os.path.join(GENOME_HOME, "data/*")
for _dir in sorted(glob.glob(path)): 
    month = _dir[len(path)-1:_dir.find("-", len(path))]
    year = _dir[_dir.rfind("-")+1:_dir.find(":")]

    idx = _dir.find("-", len(path))+1
    day = _dir[idx:_dir.find("-", idx)]
    hour = _dir[_dir.find(":")+1:]

    folder_id = month+"-"+day+"-"+year+":"+hour

    folder_path = os.path.join(GENOME_HOME, "data", folder_id)
    output_json = os.path.join(folder_path, folder_id + "_bug.json")
    with open(output_json) as f:
        bug_array = json.load(f)
    for bug in bug_array:
        bug_path = os.path.join(folder_path, str(bug["id"]))
        files_changed = bug["files_changed"]
        if "state" in files_changed[0]["metadata"]:
            with open(os.path.join(bug_path, 'processing_info.json'), 'w') as outfile:  
                print("wrote to processing_info.json", bug_path)
                json.dump(files_changed, outfile, indent=4, sort_keys=True)
            for fi in files_changed:
                fi["metadata"].pop("state")
        elif "es6" in files_changed[0]["metadata"]:
            with open(os.path.join(bug_path, 'processing_info.json'), 'w') as outfile:  
                print("wrote to processing_info.json", bug_path)
                json.dump(files_changed, outfile, indent=4, sort_keys=True)
            for fi in files_changed:
                fi["metadata"].pop("es6")
    with open(output_json, 'w') as outfile:  
            print("removing state field", output_json)
            json.dump(bug_array, outfile, indent=4, sort_keys=True)