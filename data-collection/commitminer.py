import os
import errno
from pydriller import RepositoryMining
import csv
import re

COMPOSED_SYMBOLS = ['<<', '>>', '==', '!=', '>=', '<=', '&&', '||', '++', '--', '-=', '+=', '*=', '/=', '%=', '&=',
                    '|=', '^=', '<<=', '>>=', '->', '<-', '::']

def extract_strings(string):
    # FIXME Does not work for s.append(',').append(',') return [',', ').append(', ',']
    matches = re.sub(r'"([^"]*)"', " SSSTRINGSS ", string)
    matches = re.sub(r"'([^']*)'", " SSSTRINGSS ", matches)
    matches = re.sub(r"`([^`]*)`", " SSSTRINGSS ", matches)

    return matches

def number_split(identifier):
    match = re.findall('\d+|\D+', identifier)
    return match


def remove_integer(tokens):
    for idx, tok in enumerate(tokens):
        if tok.isdigit():
            try:
                if int(tok) > 1:
                    tokens[idx] = '$NUMBER$'
            except:
                tokens[idx] = tok
    return tokens

def get_strings_numbers(string):
    # FIXME Does not work for s.append(',').append(',') return [',', ').append(', ',']
    matches1 = re.findall(r'(?<=\")(.*?)(?=\")', string)
    matches2 = re.findall(r"(?<=\')(.*?)(?=\')", string)
    strings = matches1 + matches2
    numbers = re.findall(r'\d+', string)
    return strings, numbers

def tokenize(string):
    final_token_list = []
    string_replaced = extract_strings(string)
    split_tokens = re.split(r'([\W_])', string_replaced)
    split_tokens = list(filter(lambda a: a not in [' ', '', '"', "'", '\t', '\n'], split_tokens))
    flag = False

    # Special symbols
    for idx, token in enumerate(split_tokens):
        if idx < len(split_tokens) - 1:
            reconstructed_token = token + split_tokens[idx + 1]
            if reconstructed_token in COMPOSED_SYMBOLS:
                final_token_list.append(reconstructed_token)
                flag = True
            elif not flag:
                final_token_list.append(token)
            elif flag:
                flag = False
        else:
            final_token_list.append(token)

    final_token_list = ' '.join(final_token_list).replace('== ==', '===').split(' ')
    # number split
    tokens = []
    for token in final_token_list:
        number_sep = number_split(token)
        for num in number_sep:
            tokens.append(num)
    tokens = remove_integer(tokens)
    for idx, token in enumerate(tokens):
        if token == 'SSSTRINGSS':
            if idx > 0 and tokens[idx - 1] == '$STRING$':
                return []
            else:
                tokens[idx] = '$STRING$'
    return tokens

class repo:
    def __init__(self, owner, address):
        self.owner = owner
        self.address = address

def createRepositoriesList():
    repos = []
    with open('repos.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for row in csv_reader:
            if row[0] == 'Username':
                continue
            repo_owner = row[0]
            repo_address = row[1] + "/"
            repos.append(repo(repo_owner, repo_address))
    
    traverseCommits(repos) 


def add_headers(writer):
    header = [
        'Project name',
        'Repo url',
        'Commit url',
        'Commit hash',
        'Commit message',
        'Commit date',
        'Filename',
        'Buggy file url',
        'Fixed file url',
        'Diff',
        'Buggy line number',
        'Buggy line',
        'Fixed line'
    ]
    writer.writerow(header)
    

def traverseCommits(repos):
    with open('commits.csv', 'w', encoding='UTF8', newline='') as f:
        writer = csv.writer(f)
        add_headers(writer)
        for repo in repos:
            repo_address = "https://github.com/" + repo.owner + "/" + repo.address
            for commit in RepositoryMining('repositories/' + repo.address, only_no_merge=True,
                                        only_modifications_with_file_types=['.js']).traverse_commits():

                repoUrl = "https://github.com/" + repo.owner + "/" + commit.project_name

                commit_msg = str(commit.msg).lower()
                if 'bug' in commit_msg or 'fix' in commit_msg or 'resolve' in commit_msg:
                    print('Found {} buggy commit changes.....'.format(len(commit.modifications)))
                    for m in commit.modifications:
                        if m.change_type.name == "MODIFY" and m.added == 1 and m.removed == 1 and str(m.filename).endswith(".js") and not str(m.filename).endswith(".min.js"):
                            print('Writing commit data to CSV for file {} repo {}....'.format(m.filename, commit.project_name))
                            # Collect data for each single-line change
                            data = [
                                commit.project_name,
                                repoUrl,
                                repoUrl + "/commit/" + commit.hash,
                                commit.hash,
                                commit.msg,
                                commit.committer_date,
                                m.filename,
                                repoUrl + "/raw/" + commit.parents[0] + "/" + m.old_path,
                                repoUrl + "/raw/" + commit.hash + "/" + m.new_path
                            ]
                            
                            try:
                                data.append(m.diff or '')
                                data.append(m.diff_parsed.get('added')[0][0] or m.diff_parsed.get('deleted')[0][0])
                            except:
                                print("An exception occurred")
                                continue
                            diffLines = m.diff.split("\n")
                            buggy_line = None
                            fixed_line = None
                            flag = False
                            for line in diffLines:
                                #Get rid of very long lines
                                if len(line) > 350:
                                    flag = True
                                    break

                                if line.startswith('-'):
                                    excludedWords = ["import", "export", "href", "version", "require", "path", "url", "Url", "//", "/*", "html", "div", "$(", "css", "regex", "RegEx"]
                                    flag = False
                                    for word in excludedWords:
                                        if word in line:
                                            flag = True
                                            break
                                    if flag:
                                        break
                                    buggy_line = line.lstrip('-').strip()
                                    data.append(buggy_line)
                                

                                if line.startswith('+'):
                                    excludedWords = ["import", "export", "href", "version", "require", "path", "url", "Url", "//", "/*", "html", "div", "$(", "css", "regex", "RegEx"]
                                    flag = False
                                    for word in excludedWords:
                                        if word in line:
                                            flag = True
                                            break
                                    if flag:
                                        break
                                    fixed_line = line.lstrip('+').strip()
                                    data.append(fixed_line)

                            #Download buggy and fixed versions of files
                            if flag or (m.source_code is None or m.source_code_before is None):
                                continue
                            
                            tokenized_bug = tokenize(buggy_line)
                            tokenized_fix = tokenize(fixed_line)

                            if tokenized_bug == tokenized_fix:
                                continue
                            modifiedFiles = "unsliced/"
                            oldFile = modifiedFiles + "/{}_{}_{}".format(commit.project_name, commit.hash, m.filename.split('.js')[0] + '_buggy.js')
                            newFile = modifiedFiles + "/{}_{}_{}".format(commit.project_name, commit.hash, m.filename.split('.js')[0] + '_fixed.js')
                            if not os.path.exists(os.path.dirname(oldFile)):
                                try:
                                    os.makedirs(os.path.dirname(oldFile))
                                except OSError as exc:
                                    if exc.errno != errno.EEXIST:
                                        raise
                            if m.source_code.strip() != '' and m.source_code_before.strip() != '':
                                f = open(newFile, "w+")
                                f.write(m.source_code)
                                f.close()
                                f = open(oldFile, "w+")
                                f.write(m.source_code_before)
                                f.close()
                                writer.writerow(data)


if __name__ == "__main__":
    createRepositoriesList()
