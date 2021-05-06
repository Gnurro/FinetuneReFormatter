"""
Quickly check counts of a manually singled chunk
reads in a file and outputs counts and re-decoded text with tokens marked
"""

import tokensToUTF
from GPT2.encoder import get_encoder

###

inTextFile = "testText.txt"

logTokenIDs = False # toggle console output of token numbers list
logDiscord = True # toggle addition of discord code block delimiters for console output
logCounts = True # toggle console output of counts

doDecode = True # toggles output of re-decoded text with tokens marked

griffinMarker = True # adds a marker for Griffin's 15-token association range (currently 🐦💀)
dragonMarker = True # adds a marker for Dragon's 60-token association range (currently 🐲💀)
overrideKey = '' # a key after which to reset the threshold markers

sanitizeInput = False # toggles cleanup of common patterns, NOTE: this will most likely change tokenization!
sanitizeOutput = False # toggles insertion of newline markers in outputs

outputToFile = False # toggle file output of re-decoded text
outTextFile = "outText.txt"

###

fixEncodes = tokensToUTF.getFixEncodes()

text = open(inTextFile, "r", encoding="utf-8").read()

if sanitizeInput:
    text = text.replace("\n\n"," ")

enc = get_encoder()
context_tokens = enc.encode(text)

if logTokenIDs:
    tokenIDstring = f"\n{str(context_tokens)}"
else:
    tokenIDstring = ""

if logDiscord:
    wraps = "```"
else:
    wraps = ""

if logCounts:
    wordCount = len(text.split())
    charCount = len(text)
    tokenCount = len(context_tokens)
    countsBit = f"\n{str(wordCount)} words, {str(charCount)} characters -> {str(tokenCount)} BPE tokens"
else:
    countsBit = ''

# check what comes back out
if doDecode:
    decoded = ""
    tokenNumber = 0
    tokenWarning = " - Griffin should be fine with this."
    caughtKey = False
    for token in context_tokens:
        for key, value in fixEncodes.items():
            if value == token:
                decoded += key + "|"
                curToken = key
                if caughtKey == False:
                    keyMarker = key
                    caughtKey = True
        if overrideKey:
            keyMarker = overrideKey
        if curToken == keyMarker:
            tokenNumber = 0
        else:
            tokenNumber += 1
        if tokenNumber == 15 and griffinMarker:
            tokenWarning = ' - This might be too much for Griffin!'
            decoded += '🐦💀'
        if tokenNumber == 60 and dragonMarker:
            tokenWarning = ' - This might be too much, even for Dragon!'
            decoded += '🐲💀'

    if sanitizeOutput:
        finalTxt = decoded.replace('\n', '(newline)\n')
    else:
        finalTxt = decoded

    decodedTextBit = f"\nTokenizes to:\n{finalTxt}"

    if outputToFile:
        outText = open(outTextFile, "w", encoding="utf-8")
        outText.write(finalTxt)

else:
    decodedTextBit = ""

print(f"{wraps}\n{text}{decodedTextBit}{tokenIDstring}{countsBit}{tokenWarning}\n{wraps}")