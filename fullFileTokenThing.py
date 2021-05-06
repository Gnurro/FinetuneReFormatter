"""
Check counts for full file
output as .csv
for mass-checking of reformatted texts
"""
import os
import sys
import argparse
import numpy as np
import json

from GPT2.encoder import get_encoder

enc = get_encoder()

# File Paths; I've left the specifics in as examples
inPath = "..\\misc\\"

inFileName = "carly"

inPathFile = inPath + inFileName + ".txt"
outPathFile = inPath + inFileName + "_counts.csv"

# Read in
inText = open(inPathFile, "r", encoding="utf-8").read()
inTextLines = inText.split("\n")

# split into text adventure chunks
inTextChunks = inText.split(">")
inTextChunks = [">" + chunk for chunk in inTextChunks]

outText = "characters,words,tokens"

# checkMode enables a filter, so only chunks smaller or bigger then the limits show
# currently word-based, as the instructions are word-based as well
checkMode = False
lowLimit = 20
highLimit = 150

# check chunks
# starts checking at first chunk, iE ignores anything before the first >
# currently checks only the 'output' part of each chunk, not the > line
for chunk in inTextChunks[1:len(inTextChunks)]:
    cleanChunk = "".join(chunk.splitlines()[1:len(chunk.splitlines())])
    if checkMode == True:
        if len(cleanChunk.split()) <= lowLimit or len(cleanChunk.split()) >= highLimit:
            print(
                "Characters: {} Words: {} Tokens: {}".format(
                    len(cleanChunk),
                    len(cleanChunk.split()),
                    len(enc.encode(cleanChunk))
                )
            )
            outText += "\n{},{},{}".format(
                    len(cleanChunk),
                    len(cleanChunk.split()),
                    len(enc.encode(cleanChunk))
            )
    else:
        print(
            "Characters: {} Words: {} Tokens: {}".format(
                len(cleanChunk),
                len(cleanChunk.split()),
                len(enc.encode(cleanChunk))
            )
        )
        outText += "\n{},{},{}".format(
            len(cleanChunk),
            len(cleanChunk.split()),
            len(enc.encode(cleanChunk))
        )

outFile = open(outPathFile, "w", encoding="utf-8")
outFile.write(outText)