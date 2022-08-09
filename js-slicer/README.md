### Setup

- Install [Understand by Scitools](https://www.scitools.com). Requires API license key for usage of the functionalities in this script.

- The slicing function in `backward-slice.py` requires on three things:
    - Pairs of buggy and fixed files in a directory.
    - A `.und` database in that directory. This is basically the [Understand](https://www.scitools.com) database of all the files of that directory. Note that `understand` cannot process folders containing more than 10,000 pairs of files so its best if the total dataset is split into directories of 10,000 pairs. Use the `partition.py` script to chunk the root directories into multiple subdirs of 10,000 pairs of files.
    - A CSV file containing buggy line, fixed line, buggy line number.

- For each of these directories, create the `.und` database by running the `und undCommands.txt`. Feel free to add more directory chunks in the same script.

- If you're in linux, understand command line should be available in your terminal via `upython`. In Mac, you need to add the path of the `upython` executable in your Applications folder.

- Generate the csv file using the script `python generate-file-info.py --path=<data-dir>`. Make sure to pass all the folder chunks you created in step 2 in the `--path`. This will create the .csv file in each subdirs.

### Running the slicer

- `upython backward-slice.py multiple True dir1 dir2 dir3` 
    - `multiple` means multiple directories containing files buggy and fixed files (along with .und) will be sliced. If you only want to do in one folder, then use `single`. If you want to just test the slicer (sanity check), then run `upython backward-slice.py test True`
    - Here `True` means dual slicing enabled. `False` will do single slicing.

- After running the slicer, you need to use the script `node prune-unparsable-files.js <path-to-unsliced-folder> <path-to-sliced-folder> dual` to prune out files that we incompletely sliced.
