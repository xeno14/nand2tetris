#!/bin/bash

find os/*.jack | grep 'String' | while read src; do
    name=$(basename ${src/.jack//})
    dst_dir="projects/12/${name}Test/"
    tools/JackCompiler.sh $src
    mv -v os/${name}.vm $dst_dir
done