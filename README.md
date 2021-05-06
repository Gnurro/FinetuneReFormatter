# Gnurros FinetuneReFormatter
#### Tools with GUI for GPT finetune data preparation  

### Usage:

Run baseGUI.py to open the GUI.  
Select a file to inspect/edit. Currently works on .txt UTF-8 plaintext files.  

Selecting a .txt plaintext file opens it in SourceInspector mode, which is intended to help with spotting some common formatting issues in finetune data texts:  
- badly positioned newline characters
  - two different modes with different restrictiveness:
    - LineEnd mode checks for lines ending in anything but a small set of 'sentence-ending' characters
    - InLine mode checks for lines that contain no 'sentence-ending' characters
  - trailing newline at document end
- missing EOT

More in-depth editing of rolling-context-targeted data in the form of .json files is highly WIP, but can be previewed by selecting/opening an appropriately formatted .json file.   

### Planned Features:
#### textadventure (re)formatting (WIP)
Intended to allow organized creation of textadventure-formatted data. Current WIP allows inspection/editing of pre-chunked 'textadventure rolling context' based on a .json file format with text chunks + meta data.
#### GPT BPE token inspection and exploration (Idea)
Check how a text is split into tokens, and explore the 'token dictionary' to find useful/detrimental token splits or check for token/sequence ambuiguity. Most likely will come with prompt/input format checking (e.g. certain WI/context insert formats).

### Info:
Written in Python 3.9  
GUI uses PyQt5  
Requirements supplied as venv. (Subject to change.)  

### Credits:
GPT2 encoder from https://github.com/graykode/gpt-2-Pytorch  
  by Tae Hwan Jung(Jeff Jung) @graykode
