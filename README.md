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
- missing EOT

More in-depth editing of rolling-context-targeted data in the form of .json files is highly WIP, but can be previewed by selecting/opening an appropriately formatted .json file.   

### Info:
GUI uses PyQt5  
Requirements supplied as venv. (Subject to change.)  

### Credits:
GPT2 encoder from https://github.com/graykode/gpt-2-Pytorch  
  by Tae Hwan Jung(Jeff Jung) @graykode
