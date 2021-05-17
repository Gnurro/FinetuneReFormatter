"""
Base module for the GUI

TODO:
    - figure out license!!!
    - chunkFile templates?
    - move findMainWindow() outside of spec classes, iE make it static?
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

    TODO:
        - settings
            - file
            - centralWidget
        - overwrite warnings
        - unsaved file QoL
            - window title indicator
            - close warning
            - status bar?
            - autosaving?
        - save as
        - over-all hotkeys/shortcuts
            - saving
            - switching modes
        - mode state persistence
            - save with project file?
        - clear nomenclature
            - call 'chunk json project thingamajig files'...
                - ChunkFile(s)?
                - Project(s)-/File(s)?
        - CLI/direct file loading?
            - sys.args
            - flags to instantly apply common fixes?
        - add toolbar?
            - save
            - shortcuts by mode?
            - buttons to switch modes?
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # window title:
        self.setWindowTitle('Gnurros FinetuneReFormatter')
        # TODO: settings - make these configurable:
        self.setGeometry(1000, 1000, 800, 800)
        self.move(800, 50)
        # overall values used for file handling:
        self.curFileInfo = ''
        self.curFilePath = ''
        self.curFileType = ''
        self.curFileName = ''
        # currently allowed GUI modes, determined by file type:
        self.allowedModes = []
        # actual, temporary data edited:
        self.curData = ''
        # intro screen showing on start:
        InitialIntroScreen = IntroScreen()
        self.setCentralWidget(InitialIntroScreen)

        # self.fileSelect()

        # self._createToolbar()

        # self._createStatusBar()

    def setMode(self, modeID):
        """
        set/switch to different GUI modes

        TODO:
            - make more robust?
        """
        # print(f'setMode called with {modeID}')
        if modeID == 'ChunkStack':
            print('Set mode to ChunkStack.')
            curChunkStack = ChunkStack()
            self.setCentralWidget(curChunkStack)
        if modeID == 'ChunkCombiner':
            print('Set mode to ChunkCombiner.')
            curChunkCombiner = ChunkCombiner()
            self.setCentralWidget(curChunkCombiner)
        if modeID == 'SourceInspector':
            print('Set mode to SourceInspector.')
            curSourceInspector = SourceInspector()
            self.setCentralWidget(curSourceInspector)
        if modeID == 'InitialPrep':
            print('Set mode to InitialPrep.')
            curInitialPrep = InitialPrep()
            self.setCentralWidget(curInitialPrep)

    def fileSelect(self):
        """
        file selection, setting allowed modes and loading

        TODO:
            - warnings for wrong type in GUI
            - allowed file types in QtFileDialog?
            - UTF-8 conversion?
        """
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
            self.allowedModes = ['ChunkStack', 'ChunkCombiner']
            self.curData = json.loads(open(self.curFilePath, "r", encoding="UTF-8").read())
            self.setMode('ChunkCombiner')
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
        # TODO: save as
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

                if allowedMode == 'ChunkStack':
                    self.menuMode.addAction(allowedMode, lambda: self.setMode('ChunkStack'))

                if allowedMode == 'ChunkCombiner':
                    self.menuMode.addAction(allowedMode, lambda: self.setMode('ChunkCombiner'))

    def _createToolbar(self):
        tools = QToolBar()
        self.addToolBar(tools)
        tools.addAction('Save', self.saveData)

    def _createStatusBar(self):
        status = QStatusBar()
        status.showMessage('Nothing to tell yet...')
        self.setStatusBar(status)


class IntroScreen(QWidget):
    """
    Intro splash screen with file selection and access to non-file based modes

    TODO:
        - settings access
        - create new 'project'?
            - ...from chunkFile template?
    """
    def __init__(self):
        super(IntroScreen, self).__init__()

        self.layout = QGridLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.setLayout(self.layout)

        self.headLineLabel = QLabel('<h1><b>Gnurros Finetune-ReFormatter</h1></b>')

        self.openFileButton = QPushButton('Open File')
        self.openFileButton.clicked.connect(self.openFile)

        self.exploreTokensButton = QPushButton('Explore tokens')
        self.exploreTokensButton.clicked.connect(self.toTokenExplorer)

        self.layout.addWidget(self.headLineLabel, 0, 0)
        self.layout.addWidget(self.openFileButton, 1, 0)
        self.layout.addWidget(self.exploreTokensButton, 2, 0)

    def openFile(self):
        self.findMainWindow().fileSelect()

    def toTokenExplorer(self):
        curTokenExplorer = TokenExplorer()
        self.findMainWindow().setCentralWidget(curTokenExplorer)

    def findMainWindow(self):
        for widget in app.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                return widget
        return None


class SourceInspector(QWidget):
    """
    Checking for common source text issues, like excessive newlines, with an interactive text editor

    TODO:
        - turn 'newline modes' into generic 'issue trackers'
        - go through all found issues, instead of getting stuck on the first?
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
        # TODO: get rid of one of these:
        self.newlineCount = self.textField.toPlainText().count('\n')
        self.textLines = self.textField.toPlainText().split('\n')

        self.newlineModeComboBox = QComboBox()
        # TODO: make this generic:
        self.newlineModeComboBox.addItems(['LineEnd', 'InLine', 'NoDoubles'])
        self.newlineModeComboBox.currentIndexChanged.connect(self.newLineModeChange)

        self.nextBadLineButton = QPushButton()
        # TODO: make this generic:
        self.nextBadLineButton.setText('Move cursor to bad line')
        self.nextBadLineButton.clicked.connect(self.findBadLines)

        self.countBadLines()
        self.newlinesLabel.setText(f'Newlines: {str(self.newlineCount)} Bad newlines: {str(self.badLineCount)}')

        # misc warnings:
        # TODO: on-demand warning check?
        self.warningsLabel = QLabel('Warnings:')
        # self.warningsLabel.setText('Warnings:')
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
        """
        count 'bad lines'/newlines that might be detrimental for finetuning

        TODO:
            - make lineEnders configurable
                - in settings?
                - ...elsewhere?
        """
        # make sure that counter/list are empty to prevent duplicates:
        self.badLineList = []
        self.badLineCount = 0
        # list of strings that are proper ends of lines/end sentences:
        # lineEnders = ['.', '!', '?', '<|endoftext|>', '”', ':']
        # lineEnders after trying on Moby Dick:
        lineEnders = ['.', '!', '?', '<|endoftext|>', '”', ':', '—', '*', ')', '_', '’', ']', ',']
        # process line by line:
        for line in self.textLines:
            # TODO: untangle this mess?
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
            print(f'found badLineList with content: {self.badLineList}')
            # get the string position of the first bad newline:
            curBadLineTextIndex = self.getLineStringIndexList()[self.badLineList[0]]
            print(f'got text index of first badLine: {curBadLineTextIndex}')
            # put the text cursor there:
            self.setTextCursorPosition(curBadLineTextIndex)
            # focus on the text field so the cursor isn't placed somewhere else by manual mouseclick focus:
            self.textField.setFocus()

    def getLineStringIndexList(self):
        """returns list of text string indexes of the start of lines"""
        print('trying to get line text indexes')
        return [match.start() for match in re.finditer("\n", self.textField.toPlainText())]

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
    # TODO: credit source!
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
        - more quick utilities:
            - double newline removal
            - leading/trailing spaces removal
            - PDF export issue fixes
                - block layout
                - page numbers
                - headers
            - wiki fixes from other prep scripts?
        - more chunkfile creation options
            - more placeholder options
            - low/high token thresholds
            - additional metadata?
            - separate mode/(central)widget?
                - if: better name for this mode
        - file saving dialogs?
    """
    def __init__(self):
        super(InitialPrep, self).__init__()

        self.layout = QGridLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.setLayout(self.layout)
        # stat values:
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
        # TODO: make this configurable:
        # placeholder string for sentence endings:
        self.sentenceEndPlaceholder = '%%%%%'
        self.sentences = []

        self.tokenizeButton = QPushButton('Tokenize data')
        self.tokenizeButton.clicked.connect(self.tokenizeData)

        self.tokenDistLabel = QLabel('Token distribution:')
        self.tokenDistributionButton = QPushButton('Calculate token distribution')
        self.tokenDistributionButton.clicked.connect(self.calculateTokenDistribution)
        # TODO: figure out if this is even useful:
        self.chopSentencesButton = QPushButton('Split into sentences and save')
        self.chopSentencesButton.clicked.connect(self.exportSentenceList)
        self.chopSentencesFileSuffixLabel = QLabel('Sentence file suffix:')
        self.chopSentencesFileSuffix = QLineEdit('_sentences')
        # chunking:
        self.makeChunksHeaderLabel = QLabel('<b>Chunking:</b>')
        self.makeChunksFileTknsPerChunkLabel = QLabel('Maximum tokens per chunk:')
        self.makeChunksFileTknsPerChunk = QSpinBox()
        self.makeChunksFileTknsPerChunk.editingFinished.connect(self.updateTokensPerChunk)
        self.makeChunksFileTknsPerChunk.setValue(65)  # subject to change
        self.makeChunksFileTknsPerChunk.setMaximum(200)  # subject to change
        # placeholder chunks insertion:
        self.makeChunksFileInsertsCheckbox = QCheckBox('Insert placeholder chunks')
        # placeholder chunk interval:
        # TODO: add this:
        # self.makeChunksFileInsertsIntervalLabel = QLabel('Chunk insertion interval:')
        # self.makeChunksFileInsertsInterval = QSpinBox()
        # self.makeChunksFileInsertsInterval.setMinimum(2)
        # placeholder chunk metadata type:
        self.makeChunksFileInsertsTypeLabel = QLabel('Placeholder type tag:')
        # TODO: make this preconfigurable:
        self.makeChunksFileInsertsType = QLineEdit('generic')
        self.makeChunksFileInsertsType.setMaxLength(12)
        # placeholder chunk placeholder text:
        self.makeChunksFileInsertsTextLabel = QLabel('Placeholder text:')
        # TODO: make this preconfigurable:
        self.makeChunksFileInsertsText = QLineEdit('PLACEHOLDER')
        # chunk file export:
        self.makeChunksFileSuffixLabel = QLabel(f'Chunk file suffix: _{self.makeChunksFileTknsPerChunk.value()}')
        # TODO: make this preconfigurable:
        self.makeChunksFileSuffix = QLineEdit('tknChunks')
        self.makeChunksButton = QPushButton('Create chunks and save')
        self.makeChunksButton.clicked.connect(self.exportChunks)
        # one-button fixes:
        self.miscPrepLabel = QLabel('<b>Miscellaneous fixes:</b>')
        # remove spaces at line ends:
        self.lineEndSpaceRemoveButton = QPushButton('Remove spaces at line ends')
        self.lineEndSpaceRemoveButton.clicked.connect(self.lineEndSpaceRemove)
        # get basic statistics:
        self.getDataStats()

        self.layout.addWidget(self.tokenizeButton, 0, 0)
        self.layout.addWidget(self.tokenDistributionButton, 0, 1)

        self.layout.addWidget(self.dataStatsLabel, 1, 0)
        self.layout.addWidget(self.tokenDistLabel, 1, 1)

        self.layout.addWidget(self.chopSentencesFileSuffixLabel, 2, 0)
        self.layout.addWidget(self.chopSentencesFileSuffix, 2, 1)
        self.layout.addWidget(self.chopSentencesButton, 2, 2)

        self.layout.addWidget(self.makeChunksHeaderLabel, 3, 0)

        self.layout.addWidget(self.makeChunksFileTknsPerChunkLabel, 4, 0)
        self.layout.addWidget(self.makeChunksFileTknsPerChunk, 4, 1)

        self.layout.addWidget(self.makeChunksFileInsertsCheckbox, 5, 0)
        self.layout.addWidget(self.makeChunksFileInsertsTypeLabel, 5, 1)
        self.layout.addWidget(self.makeChunksFileInsertsType, 5, 2)
        self.layout.addWidget(self.makeChunksFileInsertsTextLabel, 5, 3)
        self.layout.addWidget(self.makeChunksFileInsertsText, 5, 4)

        self.layout.addWidget(self.makeChunksFileSuffixLabel, 6, 0)
        self.layout.addWidget(self.makeChunksFileSuffix, 6, 1)
        self.layout.addWidget(self.makeChunksButton, 6, 2)

        self.layout.addWidget(self.miscPrepLabel, 7, 0)

        self.layout.addWidget(self.lineEndSpaceRemoveButton, 8, 0)

    def getDataStats(self):
        # characters:
        self.curCharCount = len(self.findMainWindow().curData)
        # words:
        self.curWordCount = len(self.findMainWindow().curData.split())
        # lines:
        self.curLines = self.findMainWindow().curData.split('\n')
        self.curLineCount = len(self.curLines)
        # sentences:
        # TODO: make this configurable:
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
        """recursively iterate through data and count token occurrences"""
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
        # TODO: make number of tokens shown configurable
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
        """
        build chunks of a defined number of tokens from complete sentences and save as chunkFile

        TODO:
            - fix wonky parts
                - stop adding redundant empty chunks at the end
            - make placeholder insertion generic
                - allow more placeholders
                - allow other spacing
        """
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
                if curChunk[0] == " ":
                    curChunk = curChunk[1:]
                curChunk = curChunk.replace(" \n\n", "\n\n")
                curChunk = curChunk.replace("  ", " ")
                chunkList.append(curChunk)
                # curChunk = f"{self.sentences[index]} "
                curChunk = f"{self.sentences[index]} "
                curTokenCount = len(currentTokens)
            else:
                # print("-> Still below chunk token cap.")
                # curChunk += f"{self.sentences[index]} "
                curChunk += f"{self.sentences[index]} "

        if curChunk[-1] == " ":
            curChunk = curChunk[:-1]

        chunkList.append(curChunk)


        # for chunk in chunkList:
            # print(f'{chunk}///\n')
            # if chunk[0] == " ":
                # print('woop!')
                # chunk = chunk[0:]


        # print(chunkList)

        fullList = []

        if self.makeChunksFileInsertsCheckbox.isChecked():
            for chunk in chunkList:
                fullList.append({'text': chunk, 'type': 'sourceText'})
                fullList.append({'text': self.makeChunksFileInsertsText.text(), 'type': self.makeChunksFileInsertsType.text()})
        else:
            for chunk in chunkList:
                fullList.append({'text': chunk, 'type': 'sourceText'})

        # chunkListJSON = json.dumps(fullList)
        # print(chunkListJSON)

        # add project data:
        fullData = {'projectData': {'targetTknsPerChunk': self.makeChunksFileTknsPerChunk.value(), 'tagTypeData': {}}, 'chunks': fullList}
        fullDataJSON = json.dumps(fullData)

        with open(f'{self.findMainWindow().curFilePath.replace(".txt", "")}_{self.makeChunksFileTknsPerChunk.value()}{self.makeChunksFileSuffix.text()}.json', 'w', encoding='utf-8') as chunksOutFile:
            # chunksOutFile.write(chunkListJSON)
            chunksOutFile.write(fullDataJSON)

    def updateTokensPerChunk(self):
        """inserts desired token number into suffix automatically"""
        # TODO: make this configurable:
        self.makeChunksFileSuffixLabel.setText(f'Chunk file suffix: _{self.makeChunksFileTknsPerChunk.value()}')

    def lineEndSpaceRemove(self):
        """removes spaces at line ends"""
        self.findMainWindow().curData = self.findMainWindow().curData.replace(' \n', '\n')

    def findMainWindow(self):
        """helper method to conveniently get the MainWindow widget object"""
        for widget in app.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                return widget
        return None


class ChunkStack(QWidget):
    """
    A list of consecutive chunks in the form of ActionTextEdits

    TODO:
        - make navigation more convenient
            - make nice header (widget?)
            - Buttons: 'scrolling'?
        - make this cover the approximate context window
            - make chunk widgets more compact
            - calculate total tokens in displayed chunks
            - apply fitting actionAmount
        - settings:
            - actionAmount/chunkAmount hard setting
            - toggle for context-window auto-sizing
        - rename class/mode to ChunkStack
    """
    def __init__(self, startIndex=0, actionAmount=6):
        super(ChunkStack, self).__init__()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        # initial view position:
        # TODO: give this project persistence?
        self.startIndex = startIndex
        self.actionAmount = actionAmount
        # change view position:
        self.startIndexSpinBox = QSpinBox()
        self.startIndexSpinBox.setMaximum(len(self.findMainWindow().curData['chunks'])-actionAmount)
        self.startIndexSpinBox.valueChanged.connect(self.startIndexChange)

        self.layout.addWidget(self.startIndexSpinBox)
        # initial stack filling:
        self.fillStack()

    def fillStack(self):
        """update the displayed chunk stack"""
        print('Trying to clear ChunkStack..')
        self.clearStack()
        print('Filling ChunkStack...')
        for actionTextIndex in range(self.startIndex, self.startIndex + self.actionAmount):
            self.layout.addWidget(ActionTextEdit(actionID=actionTextIndex, actionContent=self.findMainWindow().curData['chunks'][actionTextIndex]))

    def findMainWindow(self):
        for widget in app.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                return widget
        return None

    def clearStack(self):
        """clears the chunk stack"""
        print('Clearing ChunkStack...')
        for actionIndex in reversed(range(1, self.layout.count())):
            self.layout.itemAt(actionIndex).widget().setParent(None)

    def startIndexChange(self):
        """track changes in view position"""
        self.startIndex = self.startIndexSpinBox.value()
        self.fillStack()


class ActionTextEdit(QWidget):
    """
    Interactive widget holding a single chunk/action

    TODO:
        - token threshold warnings
            - ...define token thresholds and store them
        - change chunkType edit to dropdown?
            -> chunkTypes defined elsewhere
            - might only work nicely with chunkFile/project handler widget
        - rename widgetClass to SingleChunkEdit/ChunkTextEdit/somesuch
    """
    def __init__(self, actionID=0, actionContent={'text': 'Chunk content text...', 'type': 'generic'}):
        # TODO: change actionID to chunkIndex?
        super(ActionTextEdit, self).__init__()

        self.layout = QGridLayout()
        # TODO: set alignment
        self.setLayout(self.layout)

        # chunk index:
        self.actionID = actionID
        # TODO: compact IDlabel+tokens?
        self.IDlabel = QLabel('Chunk ID: ' + str(actionID))
        # chunk type tag:
        self.typeField = QLineEdit(actionContent['type'])
        self.typeField.setMaxLength(12)
        self.typeField.setMaximumWidth(80)
        self.typeField.setEnabled(False)
        self.typeField.editingFinished.connect(self.updateType)
        # chunk content text editor:
        self.textField = QTextEdit()
        self.textField.setAcceptRichText(False)
        self.textField.setText(actionContent['text'])
        self.textField.textChanged.connect(self.textChange)
        # token counter:
        self.tokens = encoder.encode(self.textField.toPlainText())
        self.tokenCount = len(self.tokens)
        self.tokensLabel = QLabel('Tokens: ' + str(self.tokenCount))
        # 'More' button:
        self.advancedMenu = QToolButton()
        self.advancedMenu.setText('More')
        self.advancedMenu.setPopupMode(QToolButton.InstantPopup)
        self.advancedMenu.setMenu(QMenu(self.advancedMenu))
        # add chunk above:
        topSpliceAction = QWidgetAction(self.advancedMenu)
        topSpliceAction.setText('Add chunk above.')
        topSpliceAction.triggered.connect(self.spliceAbove)
        self.advancedMenu.menu().addAction(topSpliceAction)
        # add chunk below:
        bottomSpliceAction = QWidgetAction(self.advancedMenu)
        bottomSpliceAction.setText('Add chunk below.')
        bottomSpliceAction.triggered.connect(self.spliceBelow)
        self.advancedMenu.menu().addAction(bottomSpliceAction)
        # edit action type tag:
        # TODO: change this to dropdown?
        self.editTypeAction = QWidgetAction(self.advancedMenu)
        self.editTypeAction.setText('Edit chunk type.')
        self.editTypeAction.triggered.connect(self.editActionType)
        self.advancedMenu.menu().addAction(self.editTypeAction)

        self.layout.addWidget(self.textField, 0, 0, 4, 1)

        self.layout.addWidget(self.IDlabel, 0, 1, alignment=Qt.AlignRight)

        self.layout.addWidget(self.tokensLabel, 1, 1, alignment=Qt.AlignRight)

        self.layout.addWidget(self.typeField, 2, 1, alignment=Qt.AlignRight)

        self.layout.addWidget(self.advancedMenu, 3, 1, alignment=Qt.AlignRight)

    def findMainWindow(self):
        for widget in app.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                return widget
        return None

    def textChange(self):
        """
        track text changes, instantly calculate token count and update working data

        TODO:
            - settings: instant tokens toggle
            - token threshold warnings
                - fancy colors?
                - warning icon?
        """
        self.tokens = encoder.encode(self.textField.toPlainText())
        self.tokenCount = len(self.tokens)
        self.tokensLabel.setText('Tokens: ' + str(self.tokenCount))
        self.findMainWindow().curData['chunks'][self.actionID]['text'] = self.textField.toPlainText()

    def spliceAbove(self):
        """
        add a chunk above this chunk

        TODO:
            - make type/content configurable
        """
        self.findMainWindow().curData['chunks'].insert(self.actionID-1, {'text': 'Action content text...', 'type': 'generic'})
        self.parentWidget().fillStack()

    def spliceBelow(self):
        """
        add a chunk above this chunk

        TODO:
            - make type/content configurable
        """
        self.findMainWindow().curData['chunks'].insert(self.actionID+1, {'text': 'Action content text...', 'type': 'generic'})
        self.parentWidget().fillStack()

    def editActionType(self):
        """toggle type tag editing"""
        if not self.typeField.isEnabled():
            self.typeField.setEnabled(True)
            self.editTypeAction.setText('Stop type edit.')
        elif self.typeField.isEnabled():
            self.typeField.setEnabled(False)
            self.editTypeAction.setText('Edit action type.')

    def updateType(self):
        """update chunk type tag in working data"""
        self.findMainWindow().curData['chunks'][self.actionID]['type'] = self.typeField.text()


class TokenExplorer(QWidget):
    def __init__(self):
        super(TokenExplorer, self).__init__()

        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.testStringLabel = QLabel('String to check:')
        self.testString = QLineEdit()

        self.checkButton = QPushButton('Find tokens containing string')
        self.checkButton.clicked.connect(self.tokenCheck)

        self.outputText = QTextEdit()
        self.outputText.setReadOnly(True)

        self.layout.addWidget(self.testStringLabel, 0, 0)
        self.layout.addWidget(self.testString, 0, 1)
        self.layout.addWidget(self.checkButton, 0, 2)

        self.layout.addWidget(self.outputText, 1, 0, 1, 3)

    def tokenCheck(self):
        catchList = []
        checkExpression = re.compile(f'.*{self.testString.text()}.*')

        for key, value in fixEncodes.items():
            matchedExpression = checkExpression.match(key)
            if matchedExpression:
                catchList.append(key)

        self.outputText.setText('|'.join(catchList))

    def findMainWindow(self):
        for widget in app.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                return widget
        return None


class ChunkCombiner(QWidget):
    """
    Combine chunkfile content and insert newlines, pre- and suffixes depending on chunk type

    TODO:
        - fix 'unsaved' notice
            - fix layout insanity
        - export file dialog?
        - turn this into chunkFile handler widget?
    """
    def __init__(self):
        super(ChunkCombiner, self).__init__()

        self.layout = QGridLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.setLayout(self.layout)

        self.chunkAmount = len(self.findMainWindow().curData['chunks'])
        self.chunkAmountLabel = QLabel(f'Number of Chunks: {self.chunkAmount}')
        # check working data for chunk type (tags):
        chunkTagsList = [chunk['type'] for chunk in self.findMainWindow().curData['chunks']]
        self.tagTypes = list(set(chunkTagsList))
        self.tagCounts = [chunkTagsList.count(tagType) for tagType in self.tagTypes]
        tagTypeCounts = [f'{self.tagTypes[index]} ({self.tagCounts[index]})' for index in range(len(self.tagTypes))]
        self.tagTypesLabel = QLabel(f'Chunk types (amount): {", ".join(tagTypeCounts)}')
        # saving chunk type handling to project file:
        self.saveTagTypeDataButton = QPushButton('Save type handling data')
        self.saveTagTypeDataButton.clicked.connect(self.saveTagTypeData)
        # combined file settings:
        self.fileSuffixLabel = QLabel('Combined file suffix:')
        # TODO: make this preconfigurable:
        self.fileSuffix = QLineEdit('_combined')
        # add type-based strings, combine chunks and export as plaintext:
        self.combineExportButton = QPushButton('Export combined chunks')
        self.combineExportButton.clicked.connect(self.combineExport)
        # persistent chunk type handling settings:
        self.tagTypeData = {}
        if 'tagTypeData' in self.findMainWindow().curData['projectData'].keys():
            self.tagTypeData = self.findMainWindow().curData['projectData']['tagTypeData']
        print(f'tagTypeData: {self.tagTypeData}')

        self.tagTypeStackHeaderLabel = QLabel('<b>Chunk type handling:</b>')
        self.chunkTypeStack = TagTypeStack(self.tagTypes)

        self.layout.addWidget(self.chunkAmountLabel, 0, 0)
        self.layout.addWidget(self.tagTypesLabel, 0, 1)
        self.layout.addWidget(self.saveTagTypeDataButton, 0, 2)

        self.layout.addWidget(self.fileSuffixLabel, 1, 0)
        self.layout.addWidget(self.fileSuffix, 1, 1)
        self.layout.addWidget(self.combineExportButton, 1, 2)

        self.layout.addWidget(self.tagTypeStackHeaderLabel, 2, 0)
        self.layout.addWidget(self.chunkTypeStack, 3, 0, 1, 3)

    def getTagTypeStackItems(self):
        for index in range(1, len(self.chunkTypeStack.children())):
            tagID = self.chunkTypeStack.children()[index].getContent()[0]
            print(tagID)
            content = self.chunkTypeStack.children()[index].getContent()[1]
            tagPreNewlineBool = content[0]
            tagPostNewlineBool = content[1]
            tagPrefix = content[2]
            tagSuffix = content[3]
            self.tagTypeData[tagID] = [tagPreNewlineBool, tagPostNewlineBool, tagPrefix, tagSuffix]
        print('got chunk type data:')
        print(self.tagTypeData)

    def updateChunkTypeStack(self):
        print('updating chunk types')
        print(self.layout.itemAt(self.layout.count()-1))
        self.layout.itemAt(self.layout.count()-1).widget().setParent(None)
        self.chunkTypeStack = TagTypeStack(self.tagTypes)
        self.layout.addWidget(self.chunkTypeStack, 3, 0, 1, 3)

    def saveTagTypeData(self):
        print('saving tag type data')
        self.getTagTypeStackItems()
        self.findMainWindow().curData['projectData']['tagTypeData'] = self.tagTypeData
        self.updateChunkTypeStack()
        with open(f'{self.findMainWindow().curFilePath}', 'w', encoding='utf-8') as chunksOutFile:
            fullDataJSON = json.dumps(self.findMainWindow().curData)
            chunksOutFile.write(fullDataJSON)

    def combineExport(self):
        self.getTagTypeStackItems()
        chunkTextsList = []
        for chunkIndex in range(len(self.findMainWindow().curData['chunks'])):
            chunkText = self.findMainWindow().curData['chunks'][chunkIndex]['text']
            # add prefix:
            chunkText = self.tagTypeData[self.findMainWindow().curData['chunks'][chunkIndex]['type']][2] + chunkText
            # add suffix:
            chunkText += self.tagTypeData[self.findMainWindow().curData['chunks'][chunkIndex]['type']][3]
            # check for newline adding to start of chunk text:
            if self.tagTypeData[self.findMainWindow().curData['chunks'][chunkIndex]['type']][0]:
                chunkText = '\n' + chunkText
            # check for newline adding to end of chunk text:
            if self.tagTypeData[self.findMainWindow().curData['chunks'][chunkIndex]['type']][1]:
                chunkText += '\n'
            # add updated chunk text to list:
            chunkTextsList.append(chunkText)
        # join the chunk text list:
        combinedString = ''.join(chunkTextsList)
        # print(combinedString)
        # save the whole thing:
        with open(f'{self.findMainWindow().curFilePath.replace(".json", "")}{self.fileSuffix.text()}.txt', 'w', encoding='utf-8') as combinedChunksFile:
            combinedChunksFile.write(combinedString)

    def findMainWindow(self):
        for widget in app.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                return widget
        return None


class TagTypeStack(QWidget):
    """widget to hold list of chunk types and keep everything interactive"""
    def __init__(self, tagTypes):
        super(TagTypeStack, self).__init__()

        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.setLayout(self.layout)

        self.tagTypes = tagTypes

        for tagType in self.tagTypes:
            curTagTypeHolder = TagTypeHolder(tagType)
            self.layout.addWidget(curTagTypeHolder)

    def findMainWindow(self):
        for widget in app.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                return widget
        return None


class TagTypeHolder(QWidget):
    """holds single chunk type handling"""
    def __init__(self, tagType):
        super(TagTypeHolder, self).__init__()

        self.layout = QGridLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.setLayout(self.layout)

        self.tagType = tagType
        self.tagTypeIdLabel = QLabel(tagType)
        self.tagTypeSaveWarnLabel = QLabel('')

        self.tagTypeFrontNewlineCheckbox = QCheckBox('Add newline before')
        self.tagTypeBackNewlineCheckbox = QCheckBox('Add newline after')

        self.tagTypePrefixLabel = QLabel('Prefix:')
        self.tagTypePrefix = QLineEdit()

        self.tagTypeSuffixLabel = QLabel('Suffix:')
        self.tagTypeSuffix = QLineEdit()

        if tagType in self.findMainWindow().curData['projectData']['tagTypeData'].keys():
            self.tagTypeSaveWarnLabel.setText('')
            if self.findMainWindow().curData['projectData']['tagTypeData'][tagType][0]:
                self.tagTypeFrontNewlineCheckbox.setChecked(True)
            if self.findMainWindow().curData['projectData']['tagTypeData'][tagType][1]:
                self.tagTypeBackNewlineCheckbox.setChecked(True)
            if self.findMainWindow().curData['projectData']['tagTypeData'][tagType][2]:
                self.tagTypePrefix.setText(self.findMainWindow().curData['projectData']['tagTypeData'][tagType][2])
            if self.findMainWindow().curData['projectData']['tagTypeData'][tagType][3]:
                self.tagTypeSuffix.setText(self.findMainWindow().curData['projectData']['tagTypeData'][tagType][3])
        else:
            self.tagTypeSaveWarnLabel.setText('<b>(not saved)</b>')

        self.layout.addWidget(self.tagTypeIdLabel, 0, 0)
        self.layout.addWidget(self.tagTypeSaveWarnLabel, 0, 1)
        self.layout.addWidget(self.tagTypeFrontNewlineCheckbox, 1, 0)
        self.layout.addWidget(self.tagTypeBackNewlineCheckbox, 1, 1)
        self.layout.addWidget(self.tagTypePrefixLabel, 2, 0)
        self.layout.addWidget(self.tagTypePrefix, 2, 1)
        self.layout.addWidget(self.tagTypeSuffixLabel, 3, 0)
        self.layout.addWidget(self.tagTypeSuffix, 3, 1)

    def getContent(self):
        outTagType = self.tagType
        preNewlineBool = self.tagTypeFrontNewlineCheckbox.isChecked()
        postNewlineBool = self.tagTypeBackNewlineCheckbox.isChecked()
        prefix = self.tagTypePrefix.text()
        suffix = self.tagTypeSuffix.text()
        return outTagType, [preNewlineBool, postNewlineBool, prefix, suffix]

    def findMainWindow(self):
        for widget in app.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                return widget
        return None


if __name__ == '__main__':
    app = QApplication([])
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())
