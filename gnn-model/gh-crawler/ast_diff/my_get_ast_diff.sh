export BABEL_DIR=$(pwd)/babel-dir/
export NODE_PATH=$(pwd)/node_modules/

export CRAWLER_HOME="$(pwd)"
data_dir=/mnt/volume1/model-sliced/hoppity-data/
source=/mnt/volume1/model-sliced/hoppity-data/sliced_hoppity
target=/mnt/volume1/model-sliced/hoppity-data/ml_astJSON
echo $source
echo $target

python ast_diff/get_ast_diff.py --mode standalone --input_folder $source --output_folder $target --np 4

cd $data_dir
rm -rf ml_raw
cp -pR $source/ ml_raw/
find ml_raw -type f -name "*_buggy.js" -exec cp -p {} ml_astJSON/ \; -print
