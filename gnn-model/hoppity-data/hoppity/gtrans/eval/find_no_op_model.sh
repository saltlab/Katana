data_name=contextmltttttzzz

cooked_root=/Users/zhutao/lab/data/small_astPKL
save_dir=/Users/zhutao/lab/data/small_trainingResult

loss_file=/Users/zhutao/lab/data/small_trainingResult/OUTPUT_FILE
max_num_diffs=1

export CUDA_VISIBLE_DEVICES=1

python find_best_model.py \
               -data_root $cooked_root \
               -data_name $data_name \
               -save_dir $save_dir \
               -iters_per_val 100 \
               -beam_size 3 \
               -batch_size 10 \
               -topk 3 \
               -gnn_type 's2v_multi' \
               -loss_file $loss_file \
               -max_lv 4 \
               -max_modify_steps $max_num_diffs \
               -gpu 0 \
               -resampling True \
               -comp_method bilinear \
               $@
