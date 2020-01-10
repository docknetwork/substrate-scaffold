#!/bin/bash

set -ueo pipefail

if [ $# -ne 2 -a $# -ne 3 ]; then
	echo -e "Usage:\n\t./upload_run_dir.bash <target_host> <ssh_private_key_file> [run]"
	echo -e "Example:\n\t./upload_run_dir.bash root@example.com ~/.ssh/id_rsa run"
	exit 1
fi	

target_host=$1
ssh_private_key_file=$2

dorun=0
if [ $# -gt 2 ]; then
	if [ "x$3" = xrun ]; then
		dorun=1
	else
		echo "If present, second argument must be \"run\"."
		exit 1
	fi
fi


cd $(dirname $0)/..

rsync -az --progress --delete -e "ssh -i $ssh_private_key_file" ./run/ $target_host:vasaplatsen/

if [ $dorun -eq 1 ]; then
	ssh -i $ssh_private_key_file $target_host ./vasaplatsen/run.py
fi
