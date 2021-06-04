"""
Base module for the GUI

TODO:
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
from PyQt5.QtWidgets import QFileDialog, QPlainTextEdit, QCheckBox, QComboBox, QLineEdit, QSizePolicy, QMessageBox, QShortcut
from PyQt5.QtCore import Qt, QSize, QRect
from PyQt5.QtGui import QColor, QPainter, QTextFormat, QTextCursor, QKeySequence

# more handy encoder reference:
encoder = get_encoder()
# get proper reverse token dictionary:
fixEncodes = tokensToUTF.getFixEncodes()


class MainWindow(QMainWindow):
    """
    Main window, holding all the top-level things

    TODO:
        - settings
            - centralWidget
        - save as
        - over-all hotkeys/shortcuts
            - switching modes
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

        # get settings from file:
        if os.path.isfile('./settings.json'):
            print('settings found!')
            with open('./settings.json', 'r', encoding='UTF-8') as settingsFile:
                self.settings = json.loads(settingsFile.read())
        else:
            print('no settings file found!')

        # window title:
        self.setWindowTitle('Gnurros FinetuneReFormatter')
        if self.settings:
            windowSize = self.settings['general']['windowSize']
            self.setGeometry(windowSize[0], windowSize[1], windowSize[2], windowSize[3],)
            windowPosition = self.settings['general']['windowPosition']
            self.move(windowPosition[0], windowPosition[1])
        else:
            self.setGeometry(1000, 1000, 800, 800)
            self.move(800, 50)
        # overall values used for file handling:
        self.curFileInfo = ''
        self.curFilePath = ''
        self.curFileType = ''
        self.curFileName = ''
        # currently allowed GUI modes, determined by file type:
        self.allowedModes = []
        # current mode:
        self.curMode = 'none'
        # actual, temporary data edited:
        self.curData = ''
        # file saving tracker:
        self.dataIsSaved = True
        # mode value persistence:
        self.persistentChunkStackStartIndex = 0
        # intro screen showing on start:
        InitialIntroScreen = IntroScreen()
        self.setCentralWidget(InitialIntroScreen)
        # save file keyboard shortcut:
        self.fileSaveShortcut = QShortcut(QKeySequence('Ctrl+S'), self)
        self.fileSaveShortcut.activated.connect(self.saveCurFile)
        # switch mode keyboard shortcut:
        self.switchModeShortcut = QShortcut(QKeySequence('Ctrl+M'), self)
        self.switchModeShortcut.activated.connect(self.switchMode)

        # self._createToolbar()

        # self._createStatusBar()

    def setMode(self, modeID):
        """set/switch to different GUI modes"""
        # print(f'setMode called with {modeID}')
        if modeID == 'ChunkStack':
            print('Set mode to ChunkStack.')
            self.curMode = 'ChunkStack'
            curChunkStack = ChunkStack()
            self.setCentralWidget(curChunkStack)
        if modeID == 'ChunkCombiner':
            print('Set mode to ChunkCombiner.')
            self.curMode = 'ChunkCombiner'
            curChunkCombiner = ChunkCombiner()
            self.setCentralWidget(curChunkCombiner)
        if modeID == 'SourceInspector':
            print('Set mode to SourceInspector.')
            self.curMode = 'SourceInspector'
            curSourceInspector = SourceInspector()
            self.setCentralWidget(curSourceInspector)
        if modeID == 'InitialPrep':
            print('Set mode to InitialPrep.')
            self.curMode = 'InitialPrep'
            curInitialPrep = InitialPrep()
            self.setCentralWidget(curInitialPrep)

    def switchMode(self):
        """quickly switch between GUI modes"""
        if self.curMode == 'ChunkStack':
            self.setMode('ChunkCombiner')
        if self.curMode == 'ChunkCombiner':
            self.setMode('ChunkStack')
        if self.curMode == 'SourceInspector':
            self.setMode('InitialPrep')
        if self.curMode == 'InitialPrep':
            self.setMode('SourceInspector')

    def fileSelect(self):
        """
        file selection, setting allowed modes and loading
        """
        self.curFileInfo = QFileDialog.getOpenFileName(caption='Open source file...', filter='txt or ChunkFile (*.txt *.json)')
        self.curFilePath = self.curFileInfo[0]
        self.curFileName = self.curFilePath.split('/')[-1]
        self.curFileType = self.curFilePath.split('.')[-1]
        if self.curFileType == 'txt':
            try:
                self.curData = open(self.curFilePath, "r", encoding="UTF-8").read()
            except:
                QMessageBox.about(self, 'Error', f'The selected file ({self.curFileInfo[0]}) is not compatible! Make sure text files are UTF-8.')
            else:
                print('Current file type is plaintext, allowing appropriate modes...')
                self.allowedModes = ['InitialPrep', 'SourceInspector']
                self.setMode('SourceInspector')
                # self.setMode('InitialPrep')
                self._createMenu()
                self.setWindowTitle(f'Gnurros FinetuneReFormatter - {self.curFileName}')
        elif self.curFileType == 'json':
            print('Current file type is JSON, allowing appropriate modes...')
            # print(self.curData)
            self.allowedModes = ['ChunkStack', 'ChunkCombiner']
            self.curData = json.loads(open(self.curFilePath, "r", encoding="UTF-8").read())
            self.setMode('ChunkStack')
            self._createMenu()
            self.setWindowTitle(f'Gnurros FinetuneReFormatter - {self.curFileName}')
        else:
            # print('File type of selected file is not compatible!')
            self.setWindowTitle(f'Gnurros FinetuneReFormatter')
            QMessageBox.about(self, 'Error', f'File type ({self.curFileType}) of selected file ({self.curFileInfo[0]}) is not compatible!')

    def saveCurFile(self):
        with open(self.curFilePath, 'w', encoding='UTF-8') as outData:
            if self.curFileType == 'json':
                outData.write(json.dumps(self.curData))
            else:
                outData.write(self.curData)
        self.dataIsSaved = True
        self.setWindowTitle(f'Gnurros FinetuneReFormatter - {self.curFileName}')

    def saveSettings(self):
        if self.settings:
            with open('./settings.json', 'w', encoding='UTF-8') as settingsFile:
                outSettings = json.dumps(self.settings)
                settingsFile.write(outSettings)
                print('Settings saved to file.')

    def toggleFileUnsaved(self):
        # print('data is not saved')
        self.dataIsSaved = False
        self.setWindowTitle(f'Gnurros FinetuneReFormatter - {self.curFileName}*')

    def closeEvent(self, event):
        if not self.dataIsSaved:
            unsavedDataWarnBox = QMessageBox.question(self, 'Unsaved Data Warning', f'Your current data has unsaved changes!', QMessageBox.Save | QMessageBox.Ignore, QMessageBox.Save)
            if unsavedDataWarnBox == QMessageBox.Save:
                self.saveCurFile()

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
    """
    def __init__(self):
        super(SourceInspector, self).__init__()

        self.layout = QGridLayout()
        # self.layout.setAlignment(Qt.AlignLeft)
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
        # TODO: make this generic:
        self.newlineModeComboBox.addItems(['LineEnd', 'InLine', 'NoDoubles'])
        self.newlineModeComboBox.currentIndexChanged.connect(self.newLineModeChange)

        self.nextBadLineButton = QPushButton()
        # TODO: make this generic:
        self.nextBadLineButton.setText('Move cursor to bad line')
        self.nextBadLineButton.clicked.connect(self.findBadLines)

        self.curIssue = 0
        self.issueBrowseLabel = QLabel()

        self.prevIssueButton = QPushButton('◄')
        self.prevIssueButton.clicked.connect(self.prevIssue)
        self.nextIssueButton = QPushButton('►')
        self.nextIssueButton.clicked.connect(self.nextIssue)

        self.countBadLines()
        # self.newlinesLabel.setText(f'Newlines: {str(self.newlineCount)} Bad newlines: {str(self.badLineCount)}')

        # self.issueBrowseLabel.setText(f'{str(self.curIssue + 1)}/{str(self.badLineCount)}')

        # misc warnings:
        self.warningsLabel = QLabel('Warnings:')
        # self.warningsLabel.setText('Warnings:')
        self.checkWarnables()

        # putting all the widgets into layout:
        self.layout.addWidget(self.tokensLabel, 0, 0)
        self.layout.addWidget(self.tokenCountButton, 0, 1)
        self.layout.addWidget(self.tokensCheckBox, 0, 2)

        self.layout.addWidget(self.newlinesLabel, 0, 3)
        self.layout.addWidget(self.newlineModeComboBox, 0, 4)
        self.layout.addWidget(self.issueBrowseLabel, 0, 5)
        self.layout.addWidget(self.prevIssueButton, 0, 6)
        self.layout.addWidget(self.nextIssueButton, 0, 7)

        self.layout.addWidget(self.textField, 1, 0, 1, 8)

        # self.layout.addWidget(self.warningsLabel, 2, 0)

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
        self.findBadLines()

    def countBadLines(self):
        """
        count 'bad lines'/newlines that might be detrimental for finetuning
        """
        # make sure that counter/list are empty to prevent duplicates:
        self.badLineList = []
        priorBadLineCount = self.badLineCount
        self.badLineCount = 0
        # list of strings that are proper ends of lines/end sentences:
        lineEnders = ['.', '!', '?', '<|endoftext|>', '”', '“', ':', '—', '*', ')', '_', '’', ']', ',', '"']
        if self.findMainWindow().settings:
            lineEnders = self.findMainWindow().settings['SourceInspector']['lineEnders']
        # process line by line:
        for lineIndex in range(0, len(self.textLines)):
            line = self.textLines[lineIndex]
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
            # self.badLineList.append(self.textLines.index(line))
            self.badLineList.append(lineIndex)
        # update GUI newline info display and button interactivity:
        self.newlinesLabel.setText(f'Newlines: {str(self.newlineCount)} Bad newlines: {str(self.badLineCount)}')

        if priorBadLineCount > self.badLineCount > 0:
            # print('there are less bad lines now!')
            self.curIssue -= 1

        if self.badLineCount == 0:
            self.issueBrowseLabel.setText(f'{str(self.curIssue)}/{str(self.badLineCount)}')
            self.nextBadLineButton.setEnabled(False)
        # elif self.curIssue <= -1:
            # self.curIssue = 0
            # self.issueBrowseLabel.setText(f'{str(self.curIssue)}/{str(self.badLineCount)}')
        else:
            self.issueBrowseLabel.setText(f'{str(self.curIssue + 1)}/{str(self.badLineCount)}')
            self.nextBadLineButton.setEnabled(True)

    def findBadLines(self):
        """move the text cursor to the first bad newline and focus the text field"""
        # ...but only if there are any:
        if len(self.badLineList) > 0:
            # print(f'found badLineList with content: {self.badLineList}')
            # get the string position of the first bad newline:
            # curBadLineTextIndex = self.getLineStringIndexList()[self.badLineList[0]]
            curBadLineTextIndex = self.getLineStringIndexList()[self.badLineList[self.curIssue]]
            # print(f'got text index of first badLine: {curBadLineTextIndex}')
            # put the text cursor there:
            self.setTextCursorPosition(curBadLineTextIndex)
            # focus on the text field so the cursor isn't placed somewhere else by manual mouseclick focus:
            self.textField.setFocus()

    def prevIssue(self):
        if self.curIssue > 0:
            self.curIssue -= 1
            self.issueBrowseLabel.setText(f'{str(self.curIssue + 1)}/{str(self.badLineCount)}')
            self.findBadLines()
        elif self.curIssue == 0:
            self.findBadLines()
        elif self.badLineCount == 1:
            self.findBadLines()

    def nextIssue(self):
        if self.curIssue + 1 < self.badLineCount:
            self.curIssue += 1
            self.issueBrowseLabel.setText(f'{str(self.curIssue + 1)}/{str(self.badLineCount)}')
            self.findBadLines()
        elif self.badLineCount == 1:
            self.findBadLines()

    def getLineStringIndexList(self):
        """returns list of text string indexes of the start of lines"""
        # print('trying to get line text indexes')
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
        self.findMainWindow().toggleFileUnsaved()

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
    """
    line numbers area for QCodeEditor
    Source: https://stackoverflow.com/questions/40386194/create-text-area-textedit-with-line-number-in-pyqt/49790764#49790764
    """
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)


class QCodeEditor(QPlainTextEdit):
    """
    plaintext editor with line numbers and more
    Source: https://stackoverflow.com/questions/40386194/create-text-area-textedit-with-line-number-in-pyqt/49790764#49790764
    """
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
                # painter.drawText(0, top, self.lineNumberArea.width(), height, Qt.AlignRight, number)
                painter.drawText(0, int(top), self.lineNumberArea.width(), height, Qt.AlignRight, number)

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
            - PDF export issue fixes
                - page numbers
                - headers
            - wiki fixes from other prep scripts?
        - re-chunk adventure logs
            - detect adventure logs first?
            - proper advlog check?
        - more chunkfile creation options
            - low/high token thresholds
            - additional metadata?
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
        # placeholder string for sentence endings:
        self.sentenceEndPlaceholder = '%%%%%'
        if self.findMainWindow().settings:
            self.sentenceEndPlaceholder = self.findMainWindow().settings['InitialPrep']['sentenceEndPlaceholder']
        self.sentences = []
        # tokenize button:
        self.tokenizeButton = QPushButton('Tokenize data')
        self.tokenizeButton.clicked.connect(self.tokenizeData)
        # token distribution:
        self.tokenDistLabel = QLabel('Token distribution:')
        self.tokenDistributionButton = QPushButton('Calculate token distribution')
        self.tokenDistributionButton.setEnabled(False)
        self.tokenDistributionButton.clicked.connect(self.calculateTokenDistribution)
        # sentence list:
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
        if self.findMainWindow().settings:
            self.makeChunksFileTknsPerChunk.setValue(self.findMainWindow().settings['InitialPrep']['chunking']['targetTokensPerChunk'])
        self.makeChunksFileTknsPerChunk.setMaximum(200)  # subject to change
        if self.findMainWindow().settings:
            self.makeChunksFileTknsPerChunk.setMaximum(self.findMainWindow().settings['InitialPrep']['chunking']['maxTokensPerChunk'])
        # placeholder chunks insertion:
        self.makeChunksFileInsertsCheckbox = QCheckBox('Insert placeholder chunks')
        if self.findMainWindow().settings:
            self.makeChunksFileInsertsCheckbox.setChecked(self.findMainWindow().settings['InitialPrep']['chunking']['addPlaceholders'])
        # placeholder chunk interval:
        # TODO: add this?
        # self.makeChunksFileInsertsIntervalLabel = QLabel('Chunk insertion interval:')
        # self.makeChunksFileInsertsInterval = QSpinBox()
        # self.makeChunksFileInsertsInterval.setMinimum(2)
        # placeholder chunk metadata type:
        self.makeChunksFileInsertsTypeLabel = QLabel('Placeholder type tag:')
        self.makeChunksFileInsertsTypeString = 'generic'
        if self.findMainWindow().settings:
            self.makeChunksFileInsertsTypeString = self.findMainWindow().settings['InitialPrep']['chunking']['placeholderType']
        self.makeChunksFileInsertsType = QLineEdit(self.makeChunksFileInsertsTypeString)
        self.makeChunksFileInsertsType.setMaxLength(12)
        # placeholder chunk placeholder text:
        self.makeChunksFileInsertsTextLabel = QLabel('Placeholder text:')
        self.makeChunksFileInsertsTextString = 'PLACEHOLDER'
        if self.findMainWindow().settings:
            self.makeChunksFileInsertsTextString = self.findMainWindow().settings['InitialPrep']['chunking']['placeholderText']
        self.makeChunksFileInsertsText = QLineEdit(self.makeChunksFileInsertsTextString)
        # chunk file export:
        self.makeChunksFileTknSuffix = f'Chunk file suffix: _{self.makeChunksFileTknsPerChunk.value()}'
        if self.findMainWindow().settings:
            if not self.findMainWindow().settings['InitialPrep']['chunking']['autoTokensPerChunkSuffix']:
                self.makeChunksFileTknSuffix = f'Chunk file suffix: _'
        self.makeChunksFileSuffixLabel = QLabel(self.makeChunksFileTknSuffix)
        self.makeChunksFileSuffixString = 'tknChunks'
        if self.findMainWindow().settings:
            self.makeChunksFileSuffixString = self.findMainWindow().settings['InitialPrep']['chunking']['chunkFileSuffix']
        self.makeChunksFileSuffix = QLineEdit(self.makeChunksFileSuffixString)
        self.makeChunksButton = QPushButton('Create chunks and save')
        self.makeChunksButton.clicked.connect(self.exportChunks)
        # save chunking settings button:
        self.saveChunkingSettingsButton = QPushButton('Save chunking settings')
        self.saveChunkingSettingsButton.clicked.connect(self.saveChunkingSettings)
        # stats and token distribution export:
        self.exportStatsAndTknDistButton = QPushButton('Export statistics')
        self.exportStatsAndTknDistButton.clicked.connect(self.exportStatsAndTknDist)
        self.exportStatsAndTknDistButton.setEnabled(False)
        # one-button fixes:
        self.miscPrepLabel = QLabel('<b>QuickFixes:</b>')
        # remove spaces at line ends:
        self.lineEndSpaceRemoveButton = QPushButton('Remove spaces at line ends')
        self.lineEndSpaceRemoveButton.clicked.connect(self.lineEndSpaceRemove)
        # remove spaces at line starts:
        self.lineStartSpaceRemoveButton = QPushButton('Remove spaces at line starts')
        self.lineStartSpaceRemoveButton.clicked.connect(self.lineStartSpaceRemove)
        # remove double newlines:
        self.doubleNewlineRemoveButton = QPushButton('Remove double newlines')
        self.doubleNewlineRemoveButton.clicked.connect(self.doubleNewlineRemove)
        # remove block layout newlines:
        self.blockLayoutRemoveButton = QPushButton('Remove block layout')
        self.blockLayoutRemoveButton.clicked.connect(self.blockLayoutRemove)

        # get basic statistics:
        self.getDataStats()

        self.layout.addWidget(self.tokenizeButton, 0, 0)
        self.layout.addWidget(self.tokenDistributionButton, 0, 1)
        self.layout.addWidget(self.exportStatsAndTknDistButton, 0, 2)

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
        self.layout.addWidget(self.saveChunkingSettingsButton, 6, 3)

        self.layout.addWidget(self.miscPrepLabel, 7, 0)

        self.layout.addWidget(self.lineEndSpaceRemoveButton, 8, 0)
        self.layout.addWidget(self.lineStartSpaceRemoveButton, 8, 1)
        self.layout.addWidget(self.doubleNewlineRemoveButton, 8, 2)
        self.layout.addWidget(self.blockLayoutRemoveButton, 8, 3)

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
        if self.findMainWindow().settings:
            sentenceEnders = self.findMainWindow().settings['InitialPrep']['sentenceEnders']
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
        # disable button:
        self.tokenizeButton.setEnabled(False)
        # enable token distribution button:
        self.tokenDistributionButton.setEnabled(True)
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
        topTokenAmount = 10
        if self.findMainWindow().settings:
            topTokenAmount = self.findMainWindow().settings['InitialPrep']['topTokenAmount']
        for tokenFrequency in self.tokenDistribution[:topTokenAmount]:
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

        # disable button to avoid crashes:
        self.tokenDistributionButton.setEnabled(False)
        self.exportStatsAndTknDistButton.setEnabled(True)

    def exportStatsAndTknDist(self):
        # exports data statistics
        decodedTokenDist = []
        for tokenFrequency in self.tokenDistribution:
            for key, value in fixEncodes.items():
                if value == tokenFrequency[0]:
                    curDecodeToken = key
            decodedTokenDist.append((curDecodeToken, tokenFrequency[1]))
        statsData = {
            'counts': {
                'characters': self.curCharCount,
                'words': self.curWordCount,
                'lines': self.curLineCount,
                'sentences': len(self.sentences),
                'tokens': self.tokenCount,
                'uniqueTokens': self.uniqueTokenCount,
            },
            'tokenDistribution': decodedTokenDist
        }
        with open(f'{self.findMainWindow().curFilePath.replace(".txt", "")}_stats.json',
                  'w', encoding='utf-8') as statsOutFile:
            statsOutFile.write(json.dumps(statsData))

    def exportSentenceList(self):
        """exports data split into sentences as JSON (array)"""
        with open(f'{self.findMainWindow().curFilePath.replace(".txt", "")}{self.chopSentencesFileSuffix.text()}.json', 'w', encoding='utf-8') as sentenceOutFile:
            sentenceOutFile.write(json.dumps(self.sentences))

    def exportChunks(self):
        """
        build chunks of a defined number of tokens from complete sentences and save as chunkFile

        TODO:
            - fix wonky parts
            - make placeholder insertion generic?
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
                curChunk = f"{self.sentences[index]} "
                curTokenCount = len(currentTokens)
            else:
                # print("-> Still below chunk token cap.")
                # curChunk += f"{self.sentences[index]} "
                curChunk += f"{self.sentences[index]} "

        if curChunk[-1] == " ":
            curChunk = curChunk[:-1]

        if len(curChunk) > 0:
            chunkList.append(curChunk)

        fullList = []

        if self.makeChunksFileInsertsCheckbox.isChecked():
            for chunk in chunkList:
                fullList.append({'text': chunk, 'type': 'sourceText'})
                fullList.append({'text': self.makeChunksFileInsertsText.text(), 'type': self.makeChunksFileInsertsType.text()})
        else:
            for chunk in chunkList:
                fullList.append({'text': chunk, 'type': 'sourceText'})

        # add project data:
        fullData = {'projectData': {'targetTknsPerChunk': self.makeChunksFileTknsPerChunk.value(), 'tagTypeData': {}}, 'chunks': fullList}
        fullDataJSON = json.dumps(fullData)

        if self.findMainWindow().settings:
            if self.findMainWindow().settings['general']['overwriteWarnings']:
                if os.path.isfile(f'{self.findMainWindow().curFilePath.replace(".txt", "")}_{self.makeChunksFileTknsPerChunk.value()}{self.makeChunksFileSuffix.text()}.json'):
                    overWriteWarnBox = QMessageBox.question(self, 'Overwrite Warning', f'"{self.findMainWindow().curFilePath.replace(".txt", "")}_{self.makeChunksFileTknsPerChunk.value()}{self.makeChunksFileSuffix.text()}.json" already exists! Do you want to overwrite it?', QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Cancel)
                    if overWriteWarnBox == QMessageBox.Ok:
                        with open(f'{self.findMainWindow().curFilePath.replace(".txt", "")}_{self.makeChunksFileTknsPerChunk.value()}{self.makeChunksFileSuffix.text()}.json', 'w', encoding='utf-8') as chunksOutFile:
                            chunksOutFile.write(fullDataJSON)
                else:
                    with open(f'{self.findMainWindow().curFilePath.replace(".txt", "")}_{self.makeChunksFileTknsPerChunk.value()}{self.makeChunksFileSuffix.text()}.json', 'w', encoding='utf-8') as chunksOutFile:
                        chunksOutFile.write(fullDataJSON)
            else:
                with open(f'{self.findMainWindow().curFilePath.replace(".txt", "")}_{self.makeChunksFileTknsPerChunk.value()}{self.makeChunksFileSuffix.text()}.json', 'w', encoding='utf-8') as chunksOutFile:
                    chunksOutFile.write(fullDataJSON)
        else:
            with open(f'{self.findMainWindow().curFilePath.replace(".txt", "")}_{self.makeChunksFileTknsPerChunk.value()}{self.makeChunksFileSuffix.text()}.json', 'w', encoding='utf-8') as chunksOutFile:
                chunksOutFile.write(fullDataJSON)

    def updateTokensPerChunk(self):
        """inserts desired token number into suffix automatically"""
        self.makeChunksFileTknSuffix = f'Chunk file suffix: _{self.makeChunksFileTknsPerChunk.value()}'
        if self.findMainWindow().settings:
            if not self.findMainWindow().settings['InitialPrep']['chunking']['autoTokensPerChunkSuffix']:
                self.makeChunksFileTknSuffix = f'Chunk file suffix: _'
        self.makeChunksFileSuffixLabel.setText(self.makeChunksFileTknSuffix)

    def saveChunkingSettings(self):
        if self.findMainWindow().settings:
            self.findMainWindow().settings['InitialPrep']['chunking']['targetTokensPerChunk'] = self.makeChunksFileTknsPerChunk.value()
            self.findMainWindow().settings['InitialPrep']['chunking']['addPlaceholders'] = self.makeChunksFileInsertsCheckbox.isChecked()
            self.findMainWindow().settings['InitialPrep']['chunking']['placeholderType'] = self.makeChunksFileInsertsType.text()
            self.findMainWindow().settings['InitialPrep']['chunking']['placeholderText'] = self.makeChunksFileInsertsText.text()
            self.findMainWindow().settings['InitialPrep']['chunking']['chunkFileSuffix'] = self.makeChunksFileSuffix.text()
            self.findMainWindow().saveSettings()

    def lineEndSpaceRemove(self):
        """removes spaces at line ends"""
        self.findMainWindow().curData = self.findMainWindow().curData.replace(' \n', '\n')
        self.findMainWindow().toggleFileUnsaved()

    def lineStartSpaceRemove(self):
        """removes spaces at line beginnings"""
        self.findMainWindow().curData = self.findMainWindow().curData.replace('\n ', '\n')
        self.findMainWindow().toggleFileUnsaved()

    def doubleNewlineRemove(self):
        """removes double newlines"""
        self.findMainWindow().curData = self.findMainWindow().curData.replace('\n\n', '\n')
        self.findMainWindow().toggleFileUnsaved()

    def blockLayoutRemove(self):
        """removes block layout GREEDILY"""
        greedyBlockLayoutRemoveWarnBox = QMessageBox.question(self, 'Warning',
                                                f'Block layout removal is a brute force method and will remove all single linebreaks indiscriminately! '
                                                f'Double newlines will be preserved.\nClick OK if you are sure that this will not remove too much.',
                                                QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Cancel)
        if greedyBlockLayoutRemoveWarnBox == QMessageBox.Ok:
            doubleNewlinePlaceholder = '%%%%%'
            if self.findMainWindow().settings:
                doubleNewlinePlaceholder = self.findMainWindow().settings['InitialPrep']['sentenceEndPlaceholder']
            self.findMainWindow().curData = self.findMainWindow().curData.replace('\n\n', doubleNewlinePlaceholder)
            self.findMainWindow().curData = self.findMainWindow().curData.replace('\n', ' ')
            # the line above can lead to double spaces if the source has trailing/leading spaces on lines
            # so those get removed, as well:
            self.findMainWindow().curData = self.findMainWindow().curData.replace('  ', ' ')
            self.findMainWindow().curData = self.findMainWindow().curData.replace(doubleNewlinePlaceholder, '\n\n')
            self.findMainWindow().toggleFileUnsaved()

    def findMainWindow(self):
        """helper method to conveniently get the MainWindow widget object"""
        for widget in app.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                return widget
        return None


class ChunkStack(QWidget):
    """
    A list of consecutive chunks in the form of ChunkTextEdits

    TODO:
        - add unsaved file handling
        - make navigation more convenient
            - keyboard shortcuts
            - Buttons: 'scrolling'?
        - make this cover the approximate context window?
            - make chunk widgets more compact
            - apply fitting chunkAmount
    """
    def __init__(self, startIndex=0, chunkAmount=8):
        super(ChunkStack, self).__init__()

        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setContentsMargins(1, 1, 1, 1)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)
        # initial view position:
        self.startIndex = startIndex
        if not self.findMainWindow().persistentChunkStackStartIndex == 0:
            self.startIndex = self.findMainWindow().persistentChunkStackStartIndex
        self.chunkAmount = chunkAmount
        if self.findMainWindow().settings:
            self.chunkAmount = self.findMainWindow().settings['ChunkStack']['chunkAmount']
        # change view position:
        curNavBar = ChunkStackNavigation(startIndex=self.startIndex, chunkAmount=self.chunkAmount)
        self.navBar = curNavBar

        self.layout.addWidget(self.navBar)
        # initial stack filling:
        self.fillStack()

    def fillStack(self):
        """update the displayed chunk stack"""
        # print('Trying to clear ChunkStack..')
        self.clearStack()
        # print('Filling ChunkStack...')
        for chunkTextIndex in range(self.startIndex, self.startIndex + self.chunkAmount):
            self.layout.addWidget(ChunkTextEdit(chunkID=chunkTextIndex, chunkContent=self.findMainWindow().curData['chunks'][chunkTextIndex]))

    def clearStack(self):
        """clears the chunk stack"""
        # print('Clearing ChunkStack...')
        for actionIndex in reversed(range(1, self.layout.count())):
            self.layout.itemAt(actionIndex).widget().setParent(None)

    def findMainWindow(self):
        for widget in app.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                return widget
        return None


class ChunkStackNavigation(QWidget):
    """
    navigation bar for the ChunkStack

    TODO:
        - add keyboard shortcuts
    """
    def __init__(self, startIndex, chunkAmount):
        super(ChunkStackNavigation, self).__init__()

        self.layout = QGridLayout()
        self.layout.setAlignment(Qt.AlignLeft)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        # initial view position:
        self.startIndex = startIndex
        self.chunkAmount = chunkAmount
        # info label:
        self.navLabel = QLabel('View beginning at chunk index:')
        # change view position:
        self.startIndexSpinBox = QSpinBox()
        self.startIndexSpinBox.setMaximum(len(self.findMainWindow().curData['chunks']) - self.chunkAmount)
        if not self.findMainWindow().persistentChunkStackStartIndex == 0:
            self.startIndexSpinBox.setValue(self.findMainWindow().persistentChunkStackStartIndex)
        self.startIndexSpinBox.valueChanged.connect(self.startIndexChange)
        # current viewed token total:
        self.currentTokensInView = 0
        self.tokensInViewLabel = QLabel(f'Tokens in current view: {str(self.currentTokensInView)}')
        # count tokens on demand:
        self.countButton = QPushButton('Count')
        self.countButton.clicked.connect(self.updateTokensInView)

        self.layout.addWidget(self.navLabel, 0, 0)
        self.layout.addWidget(self.startIndexSpinBox, 0, 1)
        self.layout.addWidget(self.tokensInViewLabel, 0, 2)
        self.layout.addWidget(self.countButton, 0, 3)

    def startIndexChange(self):
        """track changes in view position"""
        # make sure indexing can't be messed up:
        self.startIndexSpinBox.setMaximum(len(self.findMainWindow().curData['chunks']) - self.chunkAmount)
        # apply the spinbox value:
        self.startIndex = self.startIndexSpinBox.value()
        self.parentWidget().startIndex = self.startIndex
        # update the stack:
        self.parentWidget().fillStack()
        # make view position persistent for session:
        self.findMainWindow().persistentChunkStackStartIndex = self.startIndex
        self.updateTokensInView()

    def updateTokensInView(self):
        """recalculate total tokens in view and update display"""
        self.currentTokensInView = 0
        for chunkEdit in range(1, self.parentWidget().layout.count()):
            self.currentTokensInView += self.parentWidget().layout.itemAt(chunkEdit).widget().tokenCount
        self.tokensInViewLabel.setText(f'Tokens in current view: {str(self.currentTokensInView)}')

    def findMainWindow(self):
        for widget in app.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                return widget
        return None


class ChunkTextEdit(QWidget):
    """
    Interactive widget holding a single chunk/action

    TODO:
        - add unsaved edits detection
        - token threshold warnings
            - ...define token thresholds and store them
        - change chunkType edit to dropdown?
            -> chunkTypes defined elsewhere
            - might only work nicely with chunkFile/project handler widget
        - make more compact version
    """
    def __init__(self, chunkID=0, chunkContent={'text': 'Chunk content text...', 'type': 'generic'}):
        super(ChunkTextEdit, self).__init__()

        self.layout = QGridLayout()
        self.layout.setContentsMargins(1, 1, 1, 1)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)

        # chunk index:
        self.chunkID = chunkID
        self.IDlabel = QLabel('ID: ' + str(chunkID))
        # chunk type tag:
        self.typeField = QLineEdit(chunkContent['type'])
        self.typeField.setMaxLength(12)
        self.typeField.setMaximumWidth(80)
        self.typeField.setEnabled(False)
        self.typeField.editingFinished.connect(self.updateType)
        # chunk content text editor:
        self.textField = QTextEdit()
        self.textField.setAcceptRichText(False)
        self.textField.setText(chunkContent['text'])
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
        # delete chunk:
        deleteChunkAction = QWidgetAction(self.advancedMenu)
        deleteChunkAction.setText('Delete chunk.')
        deleteChunkAction.triggered.connect(self.deleteChunk)
        self.advancedMenu.menu().addAction(deleteChunkAction)

        self.infoLabel = QLabel('ID: ' + str(chunkID) + ' Tokens: ' + str(self.tokenCount))

        self.layout.addWidget(self.textField, 0, 0, 4, 1)

        self.layout.addWidget(self.IDlabel, 0, 1, alignment=Qt.AlignTop)

        # self.layout.addWidget(self.infoLabel, 0, 1, alignment=Qt.AlignTop)
        # self.layout.addWidget(self.infoLabel, 0, 1, alignment=Qt.AlignRight)

        self.layout.addWidget(self.tokensLabel, 1, 1, alignment=Qt.AlignTop)

        # self.layout.addWidget(self.typeField, 1, 1, alignment=Qt.AlignRight)
        self.layout.addWidget(self.typeField, 2, 1, alignment=Qt.AlignTop)

        # self.layout.addWidget(self.advancedMenu, 2, 1, alignment=Qt.AlignRight)
        self.layout.addWidget(self.advancedMenu, 3, 1, alignment=Qt.AlignTop)

    def findMainWindow(self):
        for widget in app.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                return widget
        return None

    def textChange(self):
        """
        track text changes, instantly calculate token count and update working data

        TODO:
            - token threshold warnings
                - fancy colors?
                - warning icon?
        """
        self.tokens = encoder.encode(self.textField.toPlainText())
        self.tokenCount = len(self.tokens)
        self.tokensLabel.setText('Tokens: ' + str(self.tokenCount))
        self.findMainWindow().curData['chunks'][self.chunkID]['text'] = self.textField.toPlainText()
        self.findMainWindow().toggleFileUnsaved()

    def spliceAbove(self):
        """add a chunk above this chunk"""
        insertChunk = {'text': 'PLACEHOLDER', 'type': 'generic'}
        if self.findMainWindow().settings:
            insertChunkText = self.findMainWindow().settings['ChunkStack']['insertChunkText']
            insertChunkType = self.findMainWindow().settings['ChunkStack']['insertChunkType']
            insertChunk = {'text': insertChunkText, 'type': insertChunkType}
        self.findMainWindow().curData['chunks'].insert(self.chunkID, insertChunk)
        self.parentWidget().fillStack()
        self.findMainWindow().toggleFileUnsaved()

    def spliceBelow(self):
        """add a chunk above this chunk"""
        insertChunk = {'text': 'PLACEHOLDER', 'type': 'generic'}
        if self.findMainWindow().settings:
            insertChunkText = self.findMainWindow().settings['ChunkStack']['insertChunkText']
            insertChunkType = self.findMainWindow().settings['ChunkStack']['insertChunkType']
            insertChunk = {'text': insertChunkText, 'type': insertChunkType}
        self.findMainWindow().curData['chunks'].insert(self.chunkID+1, insertChunk)
        self.parentWidget().fillStack()
        self.findMainWindow().toggleFileUnsaved()

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
        self.findMainWindow().curData['chunks'][self.chunkID]['type'] = self.typeField.text()
        self.findMainWindow().toggleFileUnsaved()

    def deleteChunk(self):
        """delete this chunk"""
        self.findMainWindow().curData['chunks'].pop(self.chunkID)
        self.findMainWindow().toggleFileUnsaved()
        # make sure GUI doesn't break due to bad indexing:
        newEndIndex = self.parentWidget().startIndex + self.parentWidget().chunkAmount
        if newEndIndex > len(self.findMainWindow().curData['chunks']):
            self.parentWidget().startIndex = self.parentWidget().startIndex-1
            self.parentWidget().navBar.startIndex = self.parentWidget().navBar.startIndex-1
        # update the stack:
        self.parentWidget().fillStack()


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
        self.fileSuffixString = '_combined'
        if self.findMainWindow().settings:
            self.fileSuffixString = self.findMainWindow().settings['ChunkCombiner']['chunkFileSuffix']
        self.fileSuffix = QLineEdit(self.fileSuffixString)
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
    """
    holds single chunk type handling

    TODO:
        - change (not saved) note to (not defined)
    """
    def __init__(self, tagType):
        super(TagTypeHolder, self).__init__()

        self.layout = QGridLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.setLayout(self.layout)

        self.tagType = tagType
        self.tagTypeIdLabel = QLabel(tagType)
        self.tagTypeSaveWarnLabel = QLabel('')

        self.tagTypeFrontNewlineCheckbox = QCheckBox('Add newline before')
        self.tagTypeFrontNewlineCheckbox.clicked.connect(self.dataChanged)
        self.tagTypeBackNewlineCheckbox = QCheckBox('Add newline after')
        self.tagTypeBackNewlineCheckbox.clicked.connect(self.dataChanged)

        self.tagTypePrefixLabel = QLabel('Prefix:')
        self.tagTypePrefix = QLineEdit()
        self.tagTypePrefix.textChanged.connect(self.dataChanged)

        self.tagTypeSuffixLabel = QLabel('Suffix:')
        self.tagTypeSuffix = QLineEdit()
        self.tagTypeSuffix.textChanged.connect(self.dataChanged)

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

    def dataChanged(self):
        self.findMainWindow().toggleFileUnsaved()

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
