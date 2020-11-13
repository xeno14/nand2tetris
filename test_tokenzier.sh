#!/bin/bash
set -eu

find projects/10 | grep ".jack$" | while read input_file; do
    echo "----- $input_file -----"
    # output_file="${input_file}.T.xml"
    python JackTokenizer.py $input_file
    expected=${input_file/.jack/T.xml}
    actual=${input_file/.jack/T.mine.xml}

    echo ""
    tools/TextComparer.sh "$expected" "$actual"
    echo ""
done