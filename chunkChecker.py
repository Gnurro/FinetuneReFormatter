"""
Utility to check a chunk list for token counts and potential issues

TODO:
    - turn this into a widget to use in the GUI
    - in the GUI, show prior and following chunk to allow assessment
"""

import json
import tokensToUTF
from GPT2.encoder import get_encoder

inPath = ""
inFileName = "chapter 1"

tokensPerChunk = 65  # number of tokens a chunk should have at most

lowTokenBoundary = 20

inJSONfilePath = f"{inPath}{inFileName}_{tokensPerChunk}tkChunks.json"

inJSON = open(inJSONfilePath, "r", encoding="utf-8").read()
chunkList = json.loads(inJSON)

fixEncodes = tokensToUTF.getFixEncodes()
encoder = get_encoder()

for chunk in chunkList:
    chunkTokens = encoder.encode(chunk)

    if len(chunkTokens) > tokensPerChunk:
        print(f"'{chunk}'\nhas {len(chunkTokens)} tokens, which are {len(chunkTokens) - tokensPerChunk} too many!\n")

    if len(chunkTokens) <= lowTokenBoundary:
        print(f"'{chunk}'\nhas {len(chunkTokens)} tokens, which is very little!\n")