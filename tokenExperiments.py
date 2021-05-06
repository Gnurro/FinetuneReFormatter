import json

# GPT BS
bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) + list(range(ord("®"), ord("ÿ") + 1))
cs = bs[:]
n = 0
for b in range(2**8):
    if b not in bs:
        bs.append(b)
        cs.append(2**8+n)
        n += 1
cs = [chr(n) for n in cs]
revDict = dict(zip(cs, bs))

# fixing GPT BS
encodeFile = open(".\GPT2\encoder.json", encoding='utf-8').read()
encodes = json.loads(encodeFile)
fixEncodes = list()
for key, value in encodes.items():
    newKey = str()
    for char in key:
        if char in revDict.keys():
            newKey += chr(revDict[char])
        else:
            newKey += char
    fixEncodes.append((newKey, value))
fixEncodes = dict(fixEncodes)

"""
for key, value in fixEncodes.items():
    if len(key) == 3:
        catchList.append(key)
"""

"""
import matplotlib.pyplot as plt

maxLen = 0
for key, value in fixEncodes.items():
    if len(key) > maxLen:
        maxLen = len(key)
freqList = [0]*maxLen
for key, value in fixEncodes.items():
    freqList[len(key)-1] += 1
print(freqList)
plt.bar(list(range(maxLen))[:20], freqList[:20])
plt.show()
"""