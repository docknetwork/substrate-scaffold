#!/bin/bash

# use: ./download_run_dir.bash <git-sha-or-branch> [run]

set -ueo pipefail

if [ $# -lt 1 ]; then
	echo -e "Usage:\n\t./download_run_dir.bash <git-sha> [run]"
	echo -e "Example:\n\t./download_run_dir.bash 0b164bbff0698d24279 run"
	echo -e "Example:\n\t./download_run_dir.bash 0b164bbff0698d24279"
	exit 1
fi	

git_commit_ish=$1

dorun=0
if [ $# -gt 1 ]; then
	if [ "x$2" = xrun ]; then
		dorun=1
	else
		echo "If present, second argument must be \"run\"."
		exit 1
	fi
fi

cd ~
[ -d substrate-scaffold ] || git clone https://github.com/docknetwork/substrate-scaffold.git
cd substrate-scaffold
git fetch
git checkout $git_commit_ish

if [ -d ~/vasaplatsen ]; then rm -r ~/vasaplatsen; fi
cp -r run ~/vasaplatsen

if [ $dorun -eq 1 ]; then
	~/vasaplatsen/run.py
fi
