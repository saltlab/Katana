import json
import sys

# GHARCHIVE QUERIES
# Program to query gharchive data (json format)
# Current implementation searches for term stored in msg_search
# and returns list of resulting github url, commit hash, and repo name

def sanitize(url):
    lst = url.split("/commits/")
    l = len(lst[0])
    temp = lst[0].split("/")
    try:
        repo = temp[5]
    except:
        return ''
    return (repo, "https://github.com" + lst[0][28:l] + ".git")

def process_msg(msg):
        str1 = ''
        for i in msg:
                if i == '\"':
                        str1 += '\"'
                elif ord(i) in [40, 41, 93, 91] or ord(i) > 128:
                        str1 += ' '
                else:
                        str1 += i
        return str1

def get_urls(filename):
        jsonf = []
        count = 0
        with open(filename) as f:
                data = [json.loads(line) for line in f]
                for x in data:
                        if x['type'] == 'PushEvent':
                                time = x["created_at"]
                                y = x['payload']
                                if 'commits' in y:
                                        parent = y['before']
                                        for i in range(len(y['commits'])):
                                                commit = y['commits'][i]
                                                # order of repo_name, repo_url, buggy_hash, fixed_hash, message
                                                url_repo = sanitize(commit['url'])
                                                if url_repo == '' or commit['message'].startswith("Merge pull request"):
                                                        continue
                                                elem = {'repo_name' : url_repo[0], 
                                                'repo_url' : url_repo[1], 
                                                'buggy_hash' : parent, 
                                                'fixed_hash' : commit['sha'], 
                                                'commit_msg' : process_msg(commit['message']),
                                                'pushed_at' : time
                                                }
                                                jsonf.append(elem)
                                                parent = y['commits'][i]['sha']
                                                count += 1

        with open(output_file, "r+") as outfile:
            try:
                json_array = json.load(outfile)
            except:
                json_array = []
                # print("first entry")
                # print(count)

        with open(output_file, 'w+') as outfile:
                json.dump(json_array + jsonf, outfile)
        print(count)


fn = sys.argv[1]
output_file = sys.argv[2]
get_urls(fn)

