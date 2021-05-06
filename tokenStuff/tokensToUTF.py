"""
Sets up a reverse dictionary to nicely output tokens as their actual unicode counterparts
"""

import json
import os

def getFixEncodes():
    if os.path.exists("fixEncodes.json"):
        fixEncodes = json.loads(open("fixEncodes.json", encoding='utf-8').read())
    else:
        # GPT BS
        bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) + list(
            range(ord("®"), ord("ÿ") + 1))
        cs = bs[:]
        n = 0
        for b in range(2 ** 8):
            if b not in bs:
                bs.append(b)
                cs.append(2 ** 8 + n)
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

        fixEncodesJSON = json.dumps(fixEncodes)

        JSONfile = open("fixEncodes.json", "w", encoding="utf-8")
        JSONfile.write(fixEncodesJSON)
    return fixEncodes
