#!/bin/bash

find os/*.jack | while read src; do
    name=$(basename ${src/.jack//})
    tools/JackCompiler.sh $src
    cp -v os/${name}.vm projects/12/${name}Test/
done