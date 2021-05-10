# Gnurros FinetuneReFormatter
#### Tools with GUI for GPT finetune data preparation  

### Usage:

Run baseGUI.py to open the GUI.  
Select a file to inspect/edit. Currently works on .txt UTF-8 plaintext files.  

Selecting a .txt plaintext file opens it in SourceInspector mode, which is intended to help with spotting some common formatting issues in finetune data texts:  
- badly positioned newline characters
  - three different modes with different restrictiveness:
    - LineEnd mode checks for lines ending in anything but a small set of 'sentence-ending' characters
    - InLine mode checks for lines that contain no 'sentence-ending' characters
    - NoDoubles mode checks for empty lines to find double newlines (or any number of stacked newlines)
  - trailing newline at document end
- missing EOT

The InitialPrep mode for plaintext .txt files contains a compact view of various data statistics, as well as splitting of the data into .json files containing either separated sentences as a list/array or a chunklist including metadata for rolling context preparation.  

More in-depth editing of rolling-context-targeted data in the form of .json files is highly WIP, but can be previewed by selecting/opening an appropriately formatted .json file.   

### Planned Features:
#### textadventure (re)formatting (WIP)
Intended to allow organized creation of textadventure-formatted data. Current WIP allows inspection/editing of pre-chunked 'textadventure rolling context' based on a .json file format with text chunks + meta data. Open 'chapter 1_65tkChunks.json' to see the WIP interface (file contains 65-token-chunked chapter 1 of Moby Dick with player action inserts in the currently used data format).
#### GPT BPE token inspection and exploration (Idea)
Check how a text is split into tokens, and explore the 'token dictionary' to find useful/detrimental token splits or check for token/sequence ambuiguity. Most likely will come with prompt/input format checking (e.g. certain WI/context insert formats).

### Info:
Written in Python 3.9  
GUI uses PyQt5  
Requirements supplied as venv. (Subject to change.)  

### Credits:
GPT2 encoder from https://github.com/graykode/gpt-2-Pytorch  
  by Tae Hwan Jung(Jeff Jung) @graykode
