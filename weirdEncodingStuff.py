import json

#text = open("testText.txt", "r", encoding="utf-8").read()

'''
text = " "
print(ord(text[0]))
print(hex(ord(text[0])))
print(len(hex(ord(text[0]))))
print(chr(ord(text[0])))

text = "Ġ"
print(ord(text[0]))
print(hex(ord(text[0])))
print(len(hex(ord(text[0]))))
print(chr(ord(text[0])))
'''

text = open("testText.txt", "r", encoding="utf-8").read()
print(text)

pointList = list(text.encode())
print(pointList)

hexList = list()
for point in pointList:
    hexList.append(hex(point))
print(hexList)

#print('aaa\u000aaaa')

encodes = json.loads(open(".\GPT2\encoder.json", encoding='utf-8').read())
for key, value in encodes.items():
        if value == 198:
            print(key, value)
            print(key.encode())

'''
for item in pointList:
    for key, value in encodes.items():
        if value == item:
            print(item, key, value)

for item in hexList:
    for key, value in encodes.items():
        if value == item:
            print(item, key, value)
        #if value == token:
            #decoded += "|" + key
'''

print(encodes.items())
'''
blep = open(".\GPT2\encoder.json", encoding='utf-8').read()
blep1 = str(blep)
blep2 = blep1.replace('\\u0120', '\\u0020')
'''
#blep2 = blep1.split('\\u0120')
#print(blep2)