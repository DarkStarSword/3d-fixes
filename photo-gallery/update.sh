#!/bin/sh -xe

for dir in "$@" do
(
	cd "$dir"
	rm -frv crosseyed distance jps mirrorl mirrorr anaglyph
	../orig2all.sh originals/*
)
done
