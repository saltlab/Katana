Steps how to run the GNN architecture on [Hoppity](https://openreview.net/pdf?id=SJeqs6EFvB)'s 

- Extract the `sliced_hoppity.tar.gz` located in `./hoppity-data/`

# HOW TO CREATE A NEW CONDA ENVIRONMENT?
Assuming the name of the conda environment we want to create is `model`. 

```
cd gh-crawler
npm install shift-parser fast-json-path

cd ../hoppity-data/hoppity
conda create -n gnnEnv python=3.6
conda activate gnnEnv

pip install torch==1.3.1
pip install -r requirements.txt

cd deps/torchext
pip install -e .

cd ../..
pip install -e .


```

# BEFORE STARTING TRAINING
```
cd hoppity-data
```
Before start training run:
```
reset_data_dirs.sh
```

# COMMANDS TO PREPARE DATASET
```
cd gh-crawler
ast_diff/my_get_ast_diff.sh

cd hoppity/gtrans
cd data_process
rm processed.txt
./run_build_dataset.sh
./run_split.sh
```

# COMMANDS TO RUN TRAINING
Run `run_main.sh` which would trigger the training. At a later stage we need to do tuning hyperparameters in this file `common/config.py.`
Run training for at least 30 epochs. After that kill the script to end training.

```
cd hoppity-data/hoppity/gtrans/training
./run_main.sh
```

# COMMANDS TO DO VALIDATION
Now we need to find the best model. Trigger `find_best_model.sh` and based on the result set variables accordingly in `eval.sh`.

```
cd hoppity-data/hoppity/gtrans/eval
./find_best_model.sh
```

Set target_model (epoch-*.ckpt) in eval.sh accordingly
```
./eval.sh
```
