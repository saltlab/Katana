#!/bin/bash
data_base=/mnt/volume1/model-sliced/hoppity-data

data_root=/mnt/volume1/model-sliced/hoppity-data/ml_astJSON
data_name=contextmltttttzzz

save_dir=/mnt/volume1/model-sliced/hoppity-data/ml_astPKL

python main_build_dataset.py \
    -data_root $data_root \
    -data_name $data_name \
    -save_dir $save_dir \
    -max_ast_nodes 500 \
    -num_cores 16 \
    -gpu 1 \
    $@

