#!/bin/bash
set -eu

find projects/10/ | grep ".jack$" | while read input_file; do
    echo "----- $input_file -----"
    python CompilationEngine.py $input_file

    expected=${input_file/.jack/.xml}
    actual=${input_file/.jack/.mine.xml}

    echo ""
    tools/TextComparer.sh "$expected" "$actual"
    echo ""
done