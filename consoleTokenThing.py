import os
import sys
import argparse
import numpy as np

from GPT2.encoder import get_encoder

parser = argparse.ArgumentParser()
parser.add_argument("--text", type=str, required=False)
args = parser.parse_args()

text = args.text
if text is None:
    text = sys.stdin.read()
enc = get_encoder()
context_tokens = enc.encode(text)
print(context_tokens)
print(str(len(text)) + "->" + str(len(context_tokens)))