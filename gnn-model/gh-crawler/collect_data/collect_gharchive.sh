#!/bin/bash
# gharchive script

# get gharchive data
# this script iterates through all months/days/hours
# of gharchive data to find known bugs

# j corresponds to days
# k corresponds to hours
# year: change year in ext

# name of output file to store the result

month=$1
year=$2

if [[ -z "$month" || -z "$year" ]]; then
	echo "USAGE: ./collect_gharchive.sh MONTH YEAR"
	exit 1
fi

echo "month $month year $year"


now=$(date +"%T")

if [ ! -d $DATA_HOME/data/ ]; then
  mkdir -p $DATA_HOME/data/;
fi

echo $now start collect_bug.sh >> $DATA_HOME/data/"$idnum"/record.txt
total=0

if [[ "$month" == "1" || 
      "$month" == "3" || 
      "$month" == "5" || 
      "$month" == "7" || 
      "$month" == "8" || 
      "$month" == "10" || 
      "$month" == "12" ]]; then 
	num_days=31
elif [[ "$month" == "2" ]]; then
	num_days=28
else
	num_days=30
fi

first="$(echo $month | head -c 1)"

if [[ "$month" -lt "10" ]] && [[ "$first" != "0" ]]; then
	month="0"$month
fi

for day in $(seq 1 $num_days)
do

	if (($day < 10)); then
		day="0"$day
	fi

	for hour in $(seq 0 23)
	do

		#gets json file of year/month/day/hour data
		ext="$year-$month-$day-$hour"
		if (($hour < 10)); then
			hour="0"$hour
		fi
		#create id for each hour, make a directory 
		idnum=$month"-"$day"-"$year":"$hour

		if [ ! -d $DATA_HOME/data/$idnum ]; then
			mkdir $DATA_HOME/data/$idnum
		fi



		output=$DATA_HOME/data/$idnum/$idnum-push-events.json


		if [ -f $output ]; then
			echo "Already downloaded - continuing"
			continue
		fi

		touch $output

		base_url="http://data.gharchive.org/"
		data_url="$base_url$ext.json.gz"
		err=$(wget $data_url 2>&1)

		if [[ $err ==  *"ERROR 404: Not Found"* ]]; then 
			echo "wget failed"
			continue
		fi


		gunzip "$ext.json.gz"

		# query data with python script
		#inputs: filename, output file
		lst=$(python $CRAWLER_HOME/collect_data/query_gh_api.py "$ext.json" "$output")
		echo $lst
		total=$(($total+$lst))
		echo collected $lst push events >> $DATA_HOME/record.txt
		#remove data once parsed for space purposes
		rm -r "$ext.json"
	done
done 

now=$(date +"%T")
echo $now finish collect_bug.sh with total $total push events >> $DATA_HOME/data/"$idnum"/record.txt
