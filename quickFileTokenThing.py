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

griffinMarker = False # adds a marker for Griffin's 15-token association range (currently 🐦💀)
dragonMarker = False # adds a marker for Dragon's 60-token association range (currently 🐲💀)
overrideKey = '' # a decoded token after which to reset the threshold markers, for formats that assume re-mentions
futureMan = False # thresholds adapted to futureman: ignores first << for marker grabbing; resets threshold at newline

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
tokenWarning = ""
keyMarker = None
if doDecode:
    decoded = ""
    tokenNumber = 0
    if griffinMarker or dragonMarker:
        tokenWarning = " - Any model should be fine with this."
        if futureMan:
            tokenWarning = " - Looks like functioning futureman!"
    caughtKey = False
    for token in context_tokens:
        for key, value in fixEncodes.items():
            if value == token:
                decoded += key + "|"
                curToken = key
                if caughtKey == False:
                    if futureMan and key == '<<':
                        print("futureman mode, ignoring <<!")
                    else:
                        keyMarker = key
                        caughtKey = True
                        print(f'Extracted cutoff marker: "{keyMarker}"')

        if overrideKey:
            keyMarker = overrideKey
        if keyMarker:
            if curToken == '\n' and futureMan:
                tokenNumber = 0
            elif curToken == keyMarker:
                tokenNumber = 0
            else:
                tokenNumber += 1

        if tokenNumber == 15 and griffinMarker:
            if futureMan:
                tokenWarning = ' - This is too much for futureman!'
            else:
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
else:
    decodedTextBit = ""

print(f"{wraps}\n{text}{decodedTextBit}{tokenIDstring}{countsBit}{tokenWarning}\n{wraps}")

if outputToFile:
    outText = open(outTextFile, "w", encoding="utf-8")
    outText.write(f"{wraps}\n{text}{decodedTextBit}{tokenIDstring}{countsBit}{tokenWarning}\n{wraps}")