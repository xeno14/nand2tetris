#!/bin/bash

find os/*.jack | while read src; do
    name=$(basename ${src/.jack//})
    dst_dir="projects/12/${name}Test/"
    tools/JackCompiler.sh $src
    cp -v os/${name}.vm $dst_dir
done