import argparse
import os
import shutil


def _get_prefix(filename):
    if filename.endswith('_buggy.js') or filename.endswith('_fixed.js'):
            return filename.split('_buggy.js')[0] if '_buggy.js' in filename else filename.split('_fixed.js')[0]


def move_files(abs_dirname, N):
    """Move files into subdirectories."""

    files = [os.path.join(abs_dirname, f) for f in os.listdir(abs_dirname) if f.endswith('.js')]

    file_map = {}
    for file in files:
        prefix = _get_prefix(file)

        if '_buggy' in file:
                if prefix not in file_map:
                    file_map[prefix] = {
                        'buggy_file': file
                    }
                else:
                    file_map[prefix]['buggy_file'] = file
        elif '_fixed' in file:
                if prefix in file_map:
                    file_map[prefix]['fixed_file'] = file
                else:
                    file_map[prefix] = {
                        'fixed_file': file
                    }  

    i = 0

    for file in file_map.items():
        [prefix, obj] = file
        # create new subdir if necessary
        if i % N == 0:
            subdir_name = os.path.join(abs_dirname, '{0:03d}'.format(i // N + 1))
            try:
                os.mkdir(subdir_name)
            except FileExistsError:
                print('Folders exists -- skipping creation')


        if 'fixed_file' in obj and 'buggy_file' in obj:
            print('Working on prefix {}...'.format(prefix))
            for f in ['buggy_file', 'fixed_file']:
                # move file to current dir
                filename = obj[f]
                print('Moving file {} to subdir'.format(filename))
                f_base = os.path.basename(filename)

                shutil.copy(filename, os.path.join(subdir_name, f_base))
        i += 1

parser = argparse.ArgumentParser()
parser.add_argument(
    '--dir', help='Source directory', required=True)
parser.add_argument(
    '--num_files', help='Number of file pairs per subdirectory', required=False)

def main():
    """Module's main entry point (zopectl.command)."""
    args = parser.parse_args()
    src_dir = args.dir
    num_files = int(args.num_files) if args.num_files else 10000

    if not os.path.exists(src_dir):
        raise Exception('Directory does not exist ({0}).'.format(src_dir))

    move_files(os.path.abspath(src_dir), num_files)


if __name__ == '__main__':
    main()
