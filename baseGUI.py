"""
Base module for the GUI

TODO:
    - intro screen
        - with progress display on opening/tokenizing
    - make tokenization optional to prevent large files from locking it up
"""

import sys
import os

import json

import re

from GPT2.encoder import get_encoder

import tokensToUTF

from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QStatusBar, QToolBar, QTextEdit, QVBoxLayout, QAction
from PyQt5.QtWidgets import QHBoxLayout, QWidget, QGridLayout, QPushButton, QToolButton, QMenu, QWidgetAction, QSpinBox
from PyQt5.QtWidgets import QFileDialog, QPlainTextEdit, QCheckBox, QComboBox, QLineEdit, QSizePolicy
from PyQt5.QtCore import Qt, QSize, QRect
from PyQt5.QtGui import QColor, QPainter, QTextFormat, QTextCursor

# more handy encoder reference:
encoder = get_encoder()
# get proper reverse token dictionary:
fixEncodes = tokensToUTF.getFixEncodes()


class MainWindow(QMainWindow):
    """
    Main window, holding all the top-level things

    TODO: modes!
        -> prep mode for raw data
        -> token explorer
    TODO: settings
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle('Gnurros FinetuneReFormatter')
        self.setGeometry(1000, 1000, 800, 800)
        self.move(800, 50)

        self.curFileInfo = ''
        self.curFilePath = ''
        self.curFileType = ''
        self.curFileName = ''
        self.allowedModes = []
        self.curData = ''

        self.fileSelect()

        # self._createToolbar()

        # self._createStatusBar()

    def setMode(self, modeID):
        # print(f'setMode called with {modeID}')
        if modeID == 'ActionStack':
            print('Set mode to ActionStack.')
            curActionStack = ActionStack()
            self.setCentralWidget(curActionStack)
        if modeID == 'SourceInspector':
            print('Set mode to SourceInspector.')
            curSourceInspector = SourceInspector()
            self.setCentralWidget(curSourceInspector)
        if modeID == 'InitialPrep':
            print('Set mode to InitialPrep.')
            curInitialPrep = InitialPrep()
            self.setCentralWidget(curInitialPrep)

    def fileSelect(self):
        self.curFileInfo = QFileDialog.getOpenFileName(caption='Open source file...')
        self.curFilePath = self.curFileInfo[0]
        self.curFileName = self.curFilePath.split('/')[-1]
        self.setWindowTitle(f'Gnurros FinetuneReFormatter - {self.curFileName}')
        self.curFileType = self.curFilePath.split('.')[1]
        if self.curFileType == 'txt':
            print('Current file type is plaintext, allowing appropriate modes...')
            self.allowedModes = ['InitialPrep', 'SourceInspector']
            self.curData = open(self.curFilePath, "r", encoding="UTF-8").read()
            self.setMode('SourceInspector')
            # self.setMode('InitialPrep')
            self._createMenu()
        elif self.curFileType == 'json':
            print('Current file type is JSON, allowing appropriate modes...')
            # print(self.curData)
            self.allowedModes = ['ActionStack']
            self.curData = json.loads(open(self.curFilePath, "r", encoding="UTF-8").read())
            self.setMode('ActionStack')
            self._createMenu()
        else:
            print('File type of selected file is not compatible!')

    def saveCurFile(self):
        with open(self.curFilePath, 'w', encoding='UTF-8') as outData:
            if self.curFileType == 'json':
                outData.write(json.dumps(self.curData))
            else:
                outData.write(self.curData)

    def _createMenu(self):
        self.topMenu = self.menuBar()
        # clean up old menu and start fresh:
        self.topMenu.clear()
        # file menu:
        self.menuFile = self.topMenu.addMenu("&File")
        self.menuFile.addAction('&Open', self.fileSelect)
        self.menuFile.addAction('&Save', self.saveCurFile)
        self.menuFile.addAction('&Exit', self.close)
        # if there are multiple allowed modes:
        if len(self.allowedModes) > 1:
            # add the mode menu
            self.menuMode = self.topMenu.addMenu('&Mode')
            # go through the allowed modes and add a menu option for each
            for allowedMode in self.allowedModes:
                """tried many more dynamic approaches, but none worked, so this is done explicitly for each mode..."""

                if allowedMode == 'InitialPrep':
                    self.menuMode.addAction(allowedMode, lambda: self.setMode('InitialPrep'))

                if allowedMode == 'SourceInspector':
                    self.menuMode.addAction(allowedMode, lambda: self.setMode('SourceInspector'))

                if allowedMode == 'ActionStack':
                    self.menuMode.addAction(allowedMode, lambda: self.setMode('ActionStack'))

    def _createToolbar(self):
        tools = QToolBar()
        self.addToolBar(tools)
        tools.addAction('Save', self.saveData)

    def _createStatusBar(self):
        status = QStatusBar()
        status.showMessage('Nothing to tell yet...')
        self.setStatusBar(status)


class SourceInspector(QWidget):
    """
    Checking for common source text issues, like excessive newlines, with an interactive text editor
    """
    def __init__(self):
        super(SourceInspector, self).__init__()

        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.textField = QCodeEditor()
        self.textField.setPlainText(self.findMainWindow().curData)
        self.textField.textChanged.connect(self.textChange)

        # instant token count:
        self.tokensLabel = QLabel()
        # self.tokens = encoder.encode(self.textField.toPlainText())
        self.tokens = []
        # self.tokenCount = len(self.tokens)
        self.tokenCount = 0
        self.tokensLabel.setText('Tokens: ' + str(self.tokenCount))
        # checkbox to turn off instant token count:
        self.doCountTokens = False
        self.tokensCheckBox = QCheckBox('Instant token count')
        self.tokensCheckBox.setChecked(False)
        self.tokensCheckBox.stateChanged.connect(self.tokenCountToggle)
        # on-demand token count button:
        self.tokenCountButton = QPushButton()
        self.tokenCountButton.setText('Count tokens')
        self.tokenCountButton.setEnabled(True)
        self.tokenCountButton.clicked.connect(self.tokenButtonClick)

        # newlines checking:
        self.newlineMode = 'LineEnd'
        self.badLineCount = 0
        self.badLineList = []

        self.newlinesLabel = QLabel()
        self.newlineCount = self.textField.toPlainText().count('\n')
        self.textLines = self.textField.toPlainText().split('\n')

        self.newlineModeComboBox = QComboBox()
        self.newlineModeComboBox.addItems(['LineEnd', 'InLine', 'NoDoubles'])
        self.newlineModeComboBox.currentIndexChanged.connect(self.newLineModeChange)

        self.nextBadLineButton = QPushButton()
        self.nextBadLineButton.setText('Move cursor to bad line')
        self.nextBadLineButton.clicked.connect(self.findBadLines)

        self.countBadLines()
        self.newlinesLabel.setText(f'Newlines: {str(self.newlineCount)} Bad newlines: {str(self.badLineCount)}')

        # misc warnings:
        self.warningsLabel = QLabel()
        self.warningsLabel.setText('Warnings:')
        self.checkWarnables()

        # putting all the widgets into layout:
        self.layout.addWidget(self.tokensLabel, 0, 0)
        self.layout.addWidget(self.tokenCountButton, 0, 1)
        self.layout.addWidget(self.tokensCheckBox, 0, 2)

        self.layout.addWidget(self.newlinesLabel, 0, 3)
        self.layout.addWidget(self.newlineModeComboBox, 0, 4)
        self.layout.addWidget(self.nextBadLineButton, 0, 5)

        self.layout.addWidget(self.textField, 1, 0, 1, 6)

        self.layout.addWidget(self.warningsLabel, 2, 0)

    def tokenCountToggle(self):
        """switch realtime encoding/token count on and off"""
        self.doCountTokens = self.tokensCheckBox.isChecked()
        if self.tokensCheckBox.isChecked():
            self.tokenCountButton.setEnabled(False)
        else:
            self.tokenCountButton.setEnabled(True)

    def tokenButtonClick(self):
        """on-demand token encoding and count"""
        self.tokens = encoder.encode(self.textField.toPlainText())
        self.tokenCount = len(self.tokens)
        self.tokensLabel.setText('Tokens: ' + str(self.tokenCount))

    def newLineModeChange(self):
        """newline checking mode selection and updating"""
        self.newlineMode = self.newlineModeComboBox.currentText()
        print(f'Newline checking mode set to {self.newlineMode}')
        self.countBadLines()

    def countBadLines(self):
        """count 'bad lines'/newlines that might be detrimental for finetuning"""
        # make sure that counter/list are empty to prevent duplicates:
        self.badLineList = []
        self.badLineCount = 0
        # list of strings that are proper ends of lines/end sentences:
        # lineEnders = ['.', '!', '?', '<|endoftext|>', '”', ':']
        # lineEnders after trying on Moby Dick:
        lineEnders = ['.', '!', '?', '<|endoftext|>', '”', ':', '—', '*', ')', '_', '’', ']', ',']
        # process line by line:
        for line in self.textLines:
            lineIsFine = False
            # handle empty lines; in NoDoubles mode these are assumed to be double newlines:
            if len(line) == 0:
                if self.newlineMode == 'NoDoubles':
                    pass
                else:
                    continue
            else:
                if self.newlineMode == 'NoDoubles':
                    lineIsFine = True

            # handle lines depending on the substring they end with:
            if self.newlineMode == 'LineEnd':
                for lineEnder in lineEnders:
                    if line.endswith(lineEnder):
                        lineIsFine = True
                        break
            # handle lines depending on the presence of 'sentence enders':
            if self.newlineMode == 'InLine':
                for lineEnder in lineEnders:
                    if lineEnder in line:
                        lineIsFine = True
                        break
            # go on with the next line if it's fine:
            if lineIsFine:
                continue
            # add line to the list of bad lines and increment counter:
            self.badLineCount += 1
            self.badLineList.append(self.textLines.index(line))
        # update GUI newline info display and button interactivity:
        self.newlinesLabel.setText(f'Newlines: {str(self.newlineCount)} Bad newlines: {str(self.badLineCount)}')
        if self.badLineCount == 0:
            self.nextBadLineButton.setEnabled(False)
        else:
            self.nextBadLineButton.setEnabled(True)

    def findBadLines(self):
        """move the text cursor to the first bad newline and focus the text field"""
        # ...but only if there are any:
        if len(self.badLineList) > 0:
            # get the string position of the first bad newline:
            curBadLineTextIndex = self.getLineStringIndexList()[self.badLineList[0]]
            # put the text cursor there:
            self.setTextCursorPosition(curBadLineTextIndex)
            # focus on the text field so the cursor isn't placed somewhere else by manual mouseclick focus:
            self.textField.setFocus()

    def getLineStringIndexList(self):
        """returns list of text string indexes of the start of lines"""
        return [match.start() for match in re.finditer('\n', self.textField.toPlainText())]

    def getTextCursor(self):
        """returns the current text cursor object"""
        return self.textField.textCursor()

    def getTextCursorPosition(self):
        """returns the current text cursor position string index"""
        return self.getTextCursor().position()

    def setTextCursorPosition(self, value):
        """set the text cursor position to parameter string index"""
        textCursor = self.getTextCursor()
        textCursor.setPosition(value)
        self.textField.setTextCursor(textCursor)

    def findMainWindow(self):
        """helper method to conveniently get the MainWindow widget object"""
        for widget in app.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                return widget
        return None

    def textChange(self):
        """event method for realtime text checking"""
        # update token count if instant token encoding+counting is on:
        if self.doCountTokens:
            self.tokens = encoder.encode(self.textField.toPlainText())
            self.tokenCount = len(self.tokens)
            self.tokensLabel.setText('Tokens: ' + str(self.tokenCount))
        # update newline checks:
        self.newlineCount = self.textField.toPlainText().count('\n')
        self.textLines = self.textField.toPlainText().split('\n')
        self.countBadLines()
        # update warnings:
        self.checkWarnables()
        # update the cached text at toplevel:
        self.findMainWindow().curData = self.textField.toPlainText()

    def checkWarnables(self):
        """
        checks for miscellaneous issues

        current warnings:
            - missing EOT
            - trailing newline at end
        """
        warningStrings = []
        # check if text ends in EOT token:
        if not self.textField.toPlainText().endswith('<|endoftext|>'):
            warningStrings.append('Missing <|endoftext|> at document end!')
        # check for trailing newline at end:
        if self.textField.toPlainText().endswith('\n'):
            warningStrings.append('Redundant empty newline at document end!')
        # cat warnings or display that there ain't none of those:
        if len(warningStrings) > 0:
            self.warningsLabel.setText('Warnings: ' + ' '.join(warningStrings))
        else:
            self.warningsLabel.setText('No warnings.')


class QLineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)


class QCodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lineNumberArea = QLineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        self.updateLineNumberAreaWidth(0)

    def lineNumberAreaWidth(self):
        digits = 1
        max_value = max(1, self.blockCount())
        while max_value >= 10:
            max_value /= 10
            digits += 1
        space = 3 + self.fontMetrics().width('9') * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def highlightCurrentLine(self):
        extraSelections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor(Qt.yellow).lighter(160)
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)

        painter.fillRect(event.rect(), Qt.lightGray)

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        # Just to make sure I use the right font
        height = self.fontMetrics().height()
        while block.isValid() and (top <= event.rect().bottom()):
            if block.isVisible() and (bottom >= event.rect().top()):
                number = str(blockNumber + 1)
                painter.setPen(Qt.black)
                painter.drawText(0, top, self.lineNumberArea.width(), height, Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

    def getTextCursor(self):
        pass


class InitialPrep(QWidget):
    """
    Utility mode to check raw data statistics and perform simple data preparation

    TODO:
        - make tokenization on-demand
        - add dummy player input option
    """
    def __init__(self):
        super(InitialPrep, self).__init__()

        self.layout = QGridLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.setLayout(self.layout)

        self.curCharCount = 0
        self.curWordCount = 0
        self.curLines = []
        self.curLineCount = 0
        self.tokens = []
        self.tokenCount = 0
        self.uniqueTokens = []
        self.uniqueTokenCount = 0
        self.tokenDistribution = {}

        self.dataStatsLabel = QLabel('Stats:')
        self.dataStatsLabel.setAlignment(Qt.AlignTop)
        self.tokenDistLabel = QLabel('Token distribution:')

        self.sentenceEndPlaceholder = '%%%%%'  # hope this thing doesn't show up in any data...
        self.sentences = []

        self.chopSentencesButton = QPushButton('Split into sentences and save')
        self.chopSentencesButton.clicked.connect(self.exportSentenceList)
        self.chopSentencesFileSuffixLabel = QLabel('Sentence file suffix:')
        self.chopSentencesFileSuffix = QLineEdit('_sentences')

        self.makeChunksButton = QPushButton('Create chunks and save')
        self.makeChunksButton.clicked.connect(self.exportChunks)
        self.makeChunksFileSuffixLabel = QLabel('Chunk file suffix: _(tokens/chunk)')
        self.makeChunksFileSuffix = QLineEdit('tknChunks')
        self.makeChunksFileTknsPerChunkLabel = QLabel('Maximum tokens per chunk:')
        self.makeChunksFileTknsPerChunk = QSpinBox()
        self.makeChunksFileTknsPerChunk.setValue(65)  # subject to change
        self.makeChunksFileTknsPerChunk.setMaximum(200)  # subject to change

        self.tokenizeButton = QPushButton('Tokenize data')
        self.tokenizeButton.clicked.connect(self.tokenizeData)

        self.tokenDistributionButton = QPushButton('Calculate token distribution')
        self.tokenDistributionButton.clicked.connect(self.calculateTokenDistribution)

        self.miscPrepLabel = QLabel('Miscellaneous small fixes:')

        self.lineEndSpaceRemoveButton = QPushButton('Remove spaces at line ends')
        self.lineEndSpaceRemoveButton.clicked.connect(self.lineEndSpaceRemove)

        self.getDataStats()

        self.layout.addWidget(self.tokenizeButton, 0, 0)
        self.layout.addWidget(self.tokenDistributionButton, 0, 1)

        self.layout.addWidget(self.dataStatsLabel, 1, 0)
        self.layout.addWidget(self.tokenDistLabel, 1, 1)

        self.layout.addWidget(self.chopSentencesFileSuffixLabel, 2, 0)
        self.layout.addWidget(self.chopSentencesFileSuffix, 2, 1)
        self.layout.addWidget(self.chopSentencesButton, 2, 2)

        self.layout.addWidget(self.makeChunksFileTknsPerChunkLabel, 3, 0)
        self.layout.addWidget(self.makeChunksFileTknsPerChunk, 3, 1)
        self.layout.addWidget(self.makeChunksFileSuffixLabel, 3, 2)
        self.layout.addWidget(self.makeChunksFileSuffix, 3, 3)
        self.layout.addWidget(self.makeChunksButton, 3, 4)

        self.layout.addWidget(self.miscPrepLabel, 4, 0)

        self.layout.addWidget(self.lineEndSpaceRemoveButton, 5, 0)

    def getDataStats(self):
        # characters:
        self.curCharCount = len(self.findMainWindow().curData)
        # words:
        self.curWordCount = len(self.findMainWindow().curData.split())
        # lines:
        self.curLines = self.findMainWindow().curData.split('\n')
        self.curLineCount = len(self.curLines)
        # sentences:
        sentenceEnders = ['.', '!', '?', ':']
        rawSentencesMarked = self.findMainWindow().curData
        for sentenceEnder in sentenceEnders:
            rawSentencesMarked = rawSentencesMarked.replace(f"{sentenceEnder}", f"{sentenceEnder}{self.sentenceEndPlaceholder}")
        self.sentences = rawSentencesMarked.split(f"{self.sentenceEndPlaceholder}")
        # put it all together and display:
        self.dataStatsLabel.setText(f'Stats:\n'
                                    f'Number of characters: {self.curCharCount}\n'
                                    f'Number of words (approximately): {self.curWordCount}\n'
                                    f'Number of lines: {self.curLineCount}\n'
                                    f'Number of sentences (approximately): {len(self.sentences)}\n'
                                    f'Number of tokens: {self.tokenCount}\n'
                                    f'Number of unique tokens: {self.uniqueTokenCount}')

    def tokenizeData(self):
        self.tokens = encoder.encode(self.findMainWindow().curData)
        self.tokenCount = len(self.tokens)
        # put it all together and display:
        self.dataStatsLabel.setText(f'Stats:\n'
                                    f'Number of characters: {self.curCharCount}\n'
                                    f'Number of words (approximately): {self.curWordCount}\n'
                                    f'Number of lines: {self.curLineCount}\n'
                                    f'Number of sentences (approximately): {len(self.sentences)}\n'
                                    f'Number of tokens: {self.tokenCount}\n'
                                    f'Number of unique tokens: {self.uniqueTokenCount}')

    def calculateTokenDistribution(self):
        for token in self.tokens:
            if token not in self.uniqueTokens:
                self.uniqueTokens.append(token)
            if token not in self.tokenDistribution.keys():
                self.tokenDistribution[token] = 1
            elif token in self.tokenDistribution.keys():
                self.tokenDistribution[token] += 1

        self.uniqueTokenCount = len(self.uniqueTokens)

        self.tokenDistribution = sorted(self.tokenDistribution.items(), key=lambda x: x[1], reverse=True)
        showTokenDistString = ''
        for tokenFrequency in self.tokenDistribution[:10]:
            for key, value in fixEncodes.items():
                if value == tokenFrequency[0]:
                    curToken = key
            showTokenDistString += f'"{curToken}" {tokenFrequency[1]}\n'

        self.tokenDistLabel.setText(f'Most frequent tokens:\n{showTokenDistString}')

        # put it all together and display:
        self.dataStatsLabel.setText(f'Stats:\n'
                                    f'Number of characters: {self.curCharCount}\n'
                                    f'Number of words (approximately): {self.curWordCount}\n'
                                    f'Number of lines: {self.curLineCount}\n'
                                    f'Number of sentences (approximately): {len(self.sentences)}\n'
                                    f'Number of tokens: {self.tokenCount}\n'
                                    f'Number of unique tokens: {self.uniqueTokenCount}')

    def exportSentenceList(self):
        """exports data split into sentences as JSON (array)"""
        with open(f'{self.findMainWindow().curFilePath.replace(".txt", "")}{self.chopSentencesFileSuffix.text()}.json', 'w', encoding='utf-8') as sentenceOutFile:
            sentenceOutFile.write(json.dumps(self.sentences))

    def exportChunks(self):
        curTokenCount = 0  # current number of tokens in current chunk
        curChunk = ""  # chunk text
        chunkList = []  # list of properly sized chunks

        for index in range(0, len(self.sentences)):
            currentTokens = encoder.encode(self.sentences[index])

            # print(f"\nChecking: {sentenceList[index]}")
            # print(f"Number of tokens: {len(currentTokens)}")
            # print(currentTokens)

            curTokenCount += len(currentTokens)
            # print(f"Number of tokens if current sentence would be added to current chunk: {curTokenCount}")

            if curTokenCount > self.makeChunksFileTknsPerChunk.value():
                # print("-> Hit chunk token cap! Starting new chunk...")
                if curChunk[-1] == " ":
                    curChunk = curChunk[:-1]
                curChunk = curChunk.replace(" \n\n", "\n\n")
                chunkList.append(curChunk)
                curChunk = f"{self.sentences[index]} "
                curTokenCount = len(currentTokens)
            else:
                # print("-> Still below chunk token cap.")
                curChunk += f"{self.sentences[index]} "

        if curChunk[-1] == " ":
            curChunk = curChunk[:-1]
        chunkList.append(curChunk)

        # print(chunkList)
        fullList = []
        for chunk in chunkList:
            fullList.append({'text': chunk, 'type': 'sourceText'})

        """
        if addEmptyPlayerInputs:
            fullList = []

            for chunk in chunkList:
                fullList.append({'text': chunk, 'type': 'sourceText'})
                fullList.append({'text': '> Do!', 'type': 'playerInput'})

        else:
            fullList = chunkList
        """

        chunkListJSON = json.dumps(fullList)
        # print(chunkListJSON)

        with open(f'{self.findMainWindow().curFilePath.replace(".txt", "")}_{self.makeChunksFileTknsPerChunk.value()}{self.makeChunksFileSuffix.text()}.json', 'w', encoding='utf-8') as chunksOutFile:
            chunksOutFile.write(chunkListJSON)

    def lineEndSpaceRemove(self):
        self.findMainWindow().curData = self.findMainWindow().curData.replace(' \n', '\n')

    def findMainWindow(self):
        """helper method to conveniently get the MainWindow widget object"""
        for widget in app.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                return widget
        return None


class ActionStack(QWidget):
    """
    A list of consecutive chunks in the form of ActionTextEdits

    TODO: Buttons: 'scrolling'?
    """
    def __init__(self, startIndex=0, actionAmount=6):
        super(ActionStack, self).__init__()

        self.startIndex = startIndex
        self.actionAmount = actionAmount

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.startIndexSpinBox = QSpinBox()
        self.startIndexSpinBox.setMaximum(len(self.findMainWindow().curData)-actionAmount)
        self.startIndexSpinBox.valueChanged.connect(self.startIndexChange)

        self.layout.addWidget(self.startIndexSpinBox)

        self.fillStack()

    def fillStack(self):
        # print('Trying to clear ActionStack..')
        self.clearStack()
        # print('Filling ActionStack...')
        for actionTextIndex in range(self.startIndex, self.startIndex + self.actionAmount):
            self.layout.addWidget(ActionTextEdit(actionID=actionTextIndex, actionContent=self.findMainWindow().curData[actionTextIndex]))

    def findMainWindow(self):
        for widget in app.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                return widget
        return None

    def clearStack(self):
        # print('Clearing ActionStack...')
        for actionIndex in reversed(range(1, self.layout.count())):
            self.layout.itemAt(actionIndex).widget().setParent(None)

    def startIndexChange(self):
        self.startIndex = self.startIndexSpinBox.value()
        self.fillStack()


class ActionTextEdit(QWidget):
    """
    Interactive widget holding a single chunk/action

    TODO:
        - token threshold warnings...?
    """
    def __init__(self, actionID=0, actionContent={'text': 'Chunk content text...', 'type': 'generic'}):
        super(ActionTextEdit, self).__init__()

        self.actionID = actionID

        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.IDlabel = QLabel('Chunk ID: ' + str(actionID))

        self.typeField = QLineEdit(actionContent['type'])
        self.typeField.setMaxLength(12)
        self.typeField.setMaximumWidth(80)
        self.typeField.setEnabled(False)
        self.typeField.editingFinished.connect(self.updateType)

        self.textField = QTextEdit()
        self.textField.setAcceptRichText(False)
        self.textField.setText(actionContent['text'])
        self.textField.textChanged.connect(self.textChange)

        self.tokens = encoder.encode(self.textField.toPlainText())
        self.tokenCount = len(self.tokens)
        self.tokensLabel = QLabel('Tokens: ' + str(self.tokenCount))

        self.advancedMenu = QToolButton()
        self.advancedMenu.setText('More')
        self.advancedMenu.setPopupMode(QToolButton.InstantPopup)
        self.advancedMenu.setMenu(QMenu(self.advancedMenu))

        topSpliceAction = QWidgetAction(self.advancedMenu)
        topSpliceAction.setText('Add chunk above.')
        topSpliceAction.triggered.connect(self.spliceAbove)
        self.advancedMenu.menu().addAction(topSpliceAction)

        bottomSpliceAction = QWidgetAction(self.advancedMenu)
        bottomSpliceAction.setText('Add chunk below.')
        bottomSpliceAction.triggered.connect(self.spliceBelow)
        self.advancedMenu.menu().addAction(bottomSpliceAction)

        self.editTypeAction = QWidgetAction(self.advancedMenu)
        self.editTypeAction.setText('Edit chunk type.')
        self.editTypeAction.triggered.connect(self.editActionType)
        self.advancedMenu.menu().addAction(self.editTypeAction)

        # self.testButton = QPushButton()
        # self.testButton.setText('Eh?')
        # self.testButton.clicked.connect(self.spliceAbove)

        self.layout.addWidget(self.textField, 0, 0, 4, 1)

        self.layout.addWidget(self.IDlabel, 0, 1, alignment=Qt.AlignRight)

        self.layout.addWidget(self.tokensLabel, 1, 1, alignment=Qt.AlignRight)

        self.layout.addWidget(self.typeField, 2, 1, alignment=Qt.AlignRight)

        self.layout.addWidget(self.advancedMenu, 3, 1, alignment=Qt.AlignRight)

        # self.layout.addWidget(self.testButton, 3, 1, alignment=Qt.AlignRight)


    def findMainWindow(self):
        for widget in app.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                return widget
        return None

    def textChange(self):
        self.tokens = encoder.encode(self.textField.toPlainText())
        self.tokenCount = len(self.tokens)
        self.tokensLabel.setText('Tokens: ' + str(self.tokenCount))
        self.findMainWindow().curData[self.actionID]['text'] = self.textField.toPlainText()

    def spliceAbove(self):
        self.findMainWindow().curData.insert(self.actionID-1, {'text': 'Action content text...', 'type': 'generic'})
        self.parentWidget().fillStack()

    def spliceBelow(self):
        self.findMainWindow().curData.insert(self.actionID+1, {'text': 'Action content text...', 'type': 'generic'})
        self.parentWidget().fillStack()

    def editActionType(self):
        if not self.typeField.isEnabled():
            self.typeField.setEnabled(True)
            self.editTypeAction.setText('Stop type edit.')
        elif self.typeField.isEnabled():
            self.typeField.setEnabled(False)
            self.editTypeAction.setText('Edit action type.')

    def updateType(self):
        self.findMainWindow().curData[self.actionID]['type'] = self.typeField.text()


if __name__ == '__main__':
    app = QApplication([])
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())
