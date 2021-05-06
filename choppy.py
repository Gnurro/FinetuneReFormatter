"""
Utilities to prepare files for reformatting (and quickly fix up (lazily) reformatted texts)

TODO: turn this into a widget to use in the GUI
"""
import re
import json

inPath = ""

inFileName = "chapter 1"

inPathFile = inPath + inFileName + ".txt"
outPathFile = inPath + inFileName + "_chop.txt"
outJSONfile = inPath + inFileName + "_sentences.json"

doubleNewlinePlaceholder = "/-----/"
sentenceEndPlaceholder = "%%%%%"


inText = open(inPathFile, "r", encoding="utf-8").read()
inTextLines = inText.split("\n")

# newText = ""

""" lazy reformatting fix bit:
for line in inTextLines:
    #line = '\t"' + line + '",\n'
    if ">" in line:
        line = "\n" + line.replace(">","> You") + ".\n"
        newText += line
    elif line != "":
        newText += line + " "
"""

# mark intentional double newline breaks; remove excessive newlines:
newText = inText.replace("\n\n", f"{doubleNewlinePlaceholder} ").replace("\n"," ")

# insert placeholder markers for better splitting:
sentenceText = newText.replace(". ", f".{sentenceEndPlaceholder}").replace("! ", f"!{sentenceEndPlaceholder}")
sentenceText = sentenceText.replace("? ", f"?{sentenceEndPlaceholder}")

# reintroduce double newlines:
sentenceText = sentenceText.replace(f"{doubleNewlinePlaceholder} ", "\n\n")

# split text into sentences; -> list
choppedSentences = sentenceText.split(f"{sentenceEndPlaceholder}")
print(choppedSentences)

# turn sentence list into json for saving:
jsonSentences = json.dumps(choppedSentences)

# save the chopped sentences in a file:
outJSON = open(outJSONfile, "w", encoding="utf-8")
outJSON.write(jsonSentences)
"""
outText = open(outPathFile, "w", encoding="utf-8")
outText.write(newText)
"""
