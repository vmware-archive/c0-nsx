#!/bin/bash 
lpass ls > /dev/null
fly -t main sp -p nsx-proto-pynsxv -c pipeline.yml -l <(lpass show --notes "Shared-Customer [0]/c0-nsx params")
