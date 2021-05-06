"""
Utility to concatenate chopped sentences into appropriately sized chunks

TODO: turn this into a widget to use in the GUI
"""

import json
import tokensToUTF
from GPT2.encoder import get_encoder

inPath = ""
inFileName = "chapter 1"

tokensPerChunk = 65  # number of tokens a chunk should have at most
addEmptyPlayerInputs = True

inJSONfilePath = inPath + inFileName + "_sentences.json"

outJSONfilePath = f"{inPath}{inFileName}_{tokensPerChunk}tkChunks.json"


inJSON = open(inJSONfilePath, "r", encoding="utf-8").read()
sentenceList = json.loads(inJSON)
# print(sentenceList)

fixEncodes = tokensToUTF.getFixEncodes()
encoder = get_encoder()

# for sentence in sentenceList:

curTokenCount = 0  # current number of tokens in current chunk
curChunk = ""  # chunk text
chunkList = []  # list of of properly sized chunks

for index in range(0, len(sentenceList)):
    currentTokens = encoder.encode(sentenceList[index])

    # print(f"\nChecking: {sentenceList[index]}")
    print(f"Number of tokens: {len(currentTokens)}")
    # print(currentTokens)

    curTokenCount += len(currentTokens)
    # print(f"Number of tokens if current sentence would be added to current chunk: {curTokenCount}")

    if curTokenCount > tokensPerChunk:
        print("-> Hit chunk token cap! Starting new chunk...")
        if curChunk[-1] == " ":
            curChunk = curChunk[:-1]
        curChunk = curChunk.replace(" \n\n", "\n\n")
        chunkList.append(curChunk)
        curChunk = f"{sentenceList[index]} "
        curTokenCount = len(currentTokens)
    else:
        print("-> Still below chunk token cap.")
        curChunk += f"{sentenceList[index]} "

    # print(curChunk)


    """
    decoded = ""
    for token in currentTokens:
        for key, value in fixEncodes.items():
            if value == token:
                decoded += key + "|"
    """

    # print(decoded)

# make sure nothing is omitted at the end:
if curChunk[-1] == " ":
    curChunk = curChunk[:-1]
chunkList.append(curChunk)

# print(chunkList)

if addEmptyPlayerInputs:
    fullList = []

    for chunk in chunkList:
        fullList.append({'text': chunk, 'type': 'sourceText'})
        fullList.append({'text': '> Do!', 'type': 'playerInput'})

else:
    fullList = chunkList




outJSON = open(outJSONfilePath, "w", encoding="utf-8")
outJSON.write(json.dumps(fullList))
