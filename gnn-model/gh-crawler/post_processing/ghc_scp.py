from paramiko import SSHClient
from tqdm import tqdm
import os
import sys

if len(sys.argv) < 4:
    print("USAGE: python client.py HOST IN_FILE DEST_DIR")
    print("")
    print("copies all files from remote server HOST listed in IN_FILE to the DEST_DIR")
    print("Format of IN_FILE is a list of filenames entered as src_file1 \\n dst_file1 \\n src_file2 \\n dst_file2 .... \\n src_fileN \\n dsy_fileN")
    print("Where n is the number of files to be copied from the HOST")
    print("")
    print("IN_FILE can be generated using gh-crawler/post_processing/copy_n_diffs")
    print("")
    sys.exit(1)

host = sys.argv[1]
in_file = sys.argv[2]
dst_dir = sys.argv[3]

if not os.path.exists(in_file):
    print("file", in_file, "does not exist")
    sys.exit(1)

if not os.path.exists(dst_dir):
    print("directory", dst_dir, "does not exist")
    sys.exit(1)

ssh = SSHClient()

ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
print("copying from", host + ".seas.upenn.edu")

ssh.connect(host + ".seas.upenn.edu")

sftp = ssh.open_sftp()

with open(in_file, "r") as f:
    rsync_list = f.read().split("\n")

count = 0
for i in tqdm(range(0, len(rsync_list)-1, 2)):
    src = rsync_list[i]
    dst = os.path.join(dst_dir, rsync_list[i+1])

    if os.path.exists(dst):
        continue

    try:
        sftp.get(src, dst)
    except FileNotFoundError:
        print(src, "does not exist")
        sys.exit(1)

    count += 1

sftp.close()
ssh.close()

print("copied", count, "files from", host + ".seas.upenn.edu to", dst_dir)
