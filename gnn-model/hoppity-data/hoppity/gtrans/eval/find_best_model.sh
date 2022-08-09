data_base=/mnt/volume1/model-sliced/hoppity-data

data_name=contextmltttttzzz

cooked_root=$data_base/ml_astPKL
save_dir=$data_base/ml_trainingResult

loss_file=$data_base/ml_trainingResult/OUTPUT_FILE
max_num_diffs=20

export CUDA_VISIBLE_DEVICES=1

python find_best_model.py \
               -data_root $cooked_root \
               -data_name $data_name \
               -save_dir $save_dir \
               -gnn_type 's2v_multi' \
               -loss_file $loss_file \
               -max_lv 4 \
	       -dropout 0.1 \
               -max_modify_steps $max_num_diffs \
               -resampling True \
               -comp_method mlp \
               $@
