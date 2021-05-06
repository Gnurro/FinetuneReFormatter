"""
Find specific tokens in the token set
"""

import tokensToUTF
import re

# (raw) string to be regExed for search:
checkStr = '\s*Ky'

printList = False # list output in console
printDiscord = True # console output with Discord codeblock delimiters
writeToFile = False # write results to file

###

fixEncodes = tokensToUTF.getFixEncodes()

catchList = list()
checkEx = re.compile(checkStr)
for key, value in fixEncodes.items():
    woop = checkEx.match(key)
    if woop:
        catchList.append(key)
print("Number of matched tokens:", len(catchList))

if printList: print(catchList)

if printDiscord:
    disordText = str()
    for item in catchList:
        disordText += item + "|"
    print(f"```{len(catchList)} Tokens matching '{checkStr}':\n{disordText}```")

if writeToFile:
    outCatchList = catchList
    finalTxt = str()
    for item in outCatchList:
        finalTxt += item + "\n"
    outText = open("tokenOutText.txt", "w", encoding="utf-8")
    outText.write(finalTxt)
