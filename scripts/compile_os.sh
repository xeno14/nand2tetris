#!/bin/bash

set -e

# unit test
# find os/*.jack | while read src; do
#     name=$(basename ${src/.jack//})
#     dst_dir="projects/12/${name}Test/"
#     tools/JackCompiler.sh $src
#     mv -v os/${name}.vm $dst_dir
# done

# integration test
tools/JackCompiler.sh os
find os/*.jack | while read src; do
    name=$(basename ${src/.jack//})
    dst_dir="projects/12/${name}Test/"
    # tools/JackCompiler.sh $src
    cp -v os/*.vm ${dst_dir}/
done
rm os/*.vm