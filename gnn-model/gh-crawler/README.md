# gh-crawler

This project consists of two major modules: the **crawler**, and the **ast diff generator**.

The **crawler** scans Github for commits that occured in a particular month and year. Two versions of the JS files changed in each commit are downloaded. That is, the file before the commit, and the file containing the changes made in the commit. 

The **ast diff generator** performs an AST level diff on each pair of (buggy, fixed) JS files. 

## CRAWLER 
First, set the following environment variables:

```
$ export CRAWLER_HOME=[path_to_this_repo]
$ export DATA_HOME=[path_to_output_dir]
```

Next, perform setup by running:

```
$ ./collect_gharchive.sh MONTH YEAR 
```

The `collect_gharchive.sh` script collects commit data from [GH Archive](https://www.gharchive.org/) and sets up the output directory by creating a folder `$DATA_HOME/data/month-day-year:hour` for each hour in the input month and year. The commit data includes a JSON array with entires for each commit in the specified time period. Each entry is a JSON object including fields for `repo_name`, `repo_url`, `buggy_hash`, `fixed_hash`, `commit_msg`and time `pushed_at`. You can also provide your own list of commits from any time period in the specified format. 

Now, we are ready to begin collecting files. For this step, we use the [PyGithub api](https://github.com/PyGithub/PyGithub).
The number of API calls per hour is limited per github account. To authorize the API, provide your github access token in the form of an environment variable. You can generate a unique access token following the instructions here: https://help.github.com/en/github/authenticating-to-github/creating-a-personal-access-token-for-the-command-line
No scopes or permissions are required. 

In order to speed up the download, you can provide multiple access tokens. Set the following environment variables to specify your access tokens: 

```
$ export NUM_ACCESS_TOKENS=[number_of_github_acess_tokens]
For each access token (indexed from 0):
$ export TOKEN_N=[nth_access_token]
```

You can configure the number of threads and number of tokens per thread by editing the `NUM_TOKENS_PER_THREAD` and `NUM_THREADS` variables in `download_files.py.` Each thread needs at least one access token. 

By default

```
python download_files.py
```

continuously downloads JS files by collecting the commit data generated in the previous step through the created folder directory. 

If you would like to use your own file for custom commit data, pass options for the input file and output folder:
```
python download_files.py DATA_FILE OUTPUT_FOLDER
```

Regardless of which mode you run the script in, each commit will be assigned a unique ID and sub-folder named as such.


## AST DIFF GENERATOR
The AST Diff Generator can run in two modes: 'Standalone' and 'Crawler.'

The Crawler mode is designed to be used in conjuction with the CRAWLER component. It generates ASTs and AST diff files for each commit sub-folder in each `$DATA_HOME/data/month-day-year:hour` folder. 

Alternatively, the Standalone folder generates ASTs and AST diff files for a single folder of JS files. If you are providing your own folder that was not generated from the CRAWLER component, ensure that for each file, there exists a (buggy, fixed) pair. We also provide a dataset 363,425 pairs of (buggy, fixed) javascript files: https://drive.google.com/file/d/1tUjAN5VODgFHxZOzLz1N14S9QQqssFL6/view?usp=sharing

This dataset consists of the files used to train and evaluate our `OneDiff` model (290,715 used for training, 36,349 for validation, and 36,361 for testing). Each pair of (buggy, fixed) files contains a single AST difference. 

As an initial setup step, install the following NPM packages used to parse JS files:

```
$ npm install shift-parser
$ npm install fast-json-patch 
```

Additionally, setup babel for a more robust parsing experience:

1. Create a folder for babel operations: `babel-dir` or a name of your choosing
2. `cd babel-dir && npm init`
3. `npm install --save-dev @babel/core @babel/cli`
4. `npm install --save-dev @babel/preset-react`
5. `npm install --save-dev @babel/plugin-proposal-class-properties`
6. Create a `.babelrc` file in the root of your `babel_dir` with the following contents:
```
{
        "presets": [
                "@babel/preset-react"
        ], 
        "plugins": [ 
                "@babel/plugin-proposal-class-properties" 
        ]
}
```

Lastly, setup the following environment variables:
```
$ export BABEL_DIR=[path_to_babel_folder]
$ export NODE_PATH=[path_to_node_modules/node_modules/]

```

Now we are ready to generate ASTs and AST diffs:

```
get_ast_diff.py 
usage: Generate asts and ast diffs from a corpus of buggy and fixed javascript pairs
       [-h] [--input_folder INPUT_FOLDER] [--output_folder OUTPUT_FOLDER]
       [--mode MODE] [--np NUM_PROCESSES]
```


### POST PROCESSING

Lastly, we provide a post-processing Statistics.py script to keep track of the number of files downloaded and AST diffs generated. Be sure to set the `DATA_HOME` environment variable before running.

