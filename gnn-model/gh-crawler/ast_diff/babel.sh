#!/bin/bash

in_path=$1
in_name=$2
out_name=$3

cp $in_path/$in_name $BABEL_DIR/$in_name
cd $BABEL_DIR
./node_modules/.bin/babel $in_name > $in_path/$out_name
rm $BABEL_DIR/$in_name
