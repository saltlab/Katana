data_base=/mnt/volume1/model-sliced/hoppity-data

data_name=contextmltttttzzz
cooked_root=$data_base/ml_astPKL
save_dir=$data_base/ml_trainingResult
target_model=$data_base/ml_trainingResult/epoch-49.ckpt
eval_dump_folder=$data_base/eval_dump_folder

export CUDA_VISIBLE_DEVICES=0

python eval.py \
	-target_model $target_model \
	-data_root $cooked_root \
	-data_name $data_name \
	-save_dir $save_dir \
	-eval_dump_folder $eval_dump_folder \
	-iters_per_val 100 \
	-beam_size 3 \
	-batch_size 10 \
	-topk 3 \
	-gnn_type 's2v_multi' \
	-max_lv 4 \
	-dropout 0.1 \
	-max_modify_steps 20 \
	-gpu 0 \
	-resampling True \
	-comp_method "mlp" \
	-bug_type True \
	-loc_acc True \
	-val_acc True \
	-output_all False \
	$@
