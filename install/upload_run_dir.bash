#!/bin/bash

set -ueo pipefail

if [ $# -ne 2 ]; then
	echo -e "Usage:\n\t./upload_run_dir.bash <target_host> <ssh_private_key_file>"
	echo -e "Example:\n\t./upload_run_dir.bash root@example.com ~/.ssh/id_rsa"
	exit 1
fi	

target_host=$1
ssh_private_key_file=$2

cd $(dirname $0)/..

rsync -az --progress --delete -e "ssh -i $ssh_private_key_file" ./run/ $target_host:vasaplatsen/
