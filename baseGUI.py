"""
Base module for the GUI

TODO:
    - CLEANUP!
    - lowercase UPPERCASE chapter intros?
    - check for lines beginning with lowercase
    -
    - CLI flags to instantly apply common fixes?
    -
    - multifile/directory mode?
        - open list of files
        - 'save and open next file' option/shortcut
"""

import sys
import os

import json

import re
import time

import tokensToUTF

from transformers import GPT2Tokenizer

from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QStatusBar, QToolBar, QTextEdit, QVBoxLayout, QAction
from PyQt5.QtWidgets import QHBoxLayout, QWidget, QGridLayout, QPushButton, QToolButton, QMenu, QWidgetAction, QSpinBox
from PyQt5.QtWidgets import QFileDialog, QPlainTextEdit, QCheckBox, QComboBox, QLineEdit, QSizePolicy, QMessageBox, QShortcut
from PyQt5.QtWidgets import QProgressBar, QFrame, QListWidget
import PyQt5.QtCore as QtCore
from PyQt5.QtCore import Qt, QSize, QRect, QThread, QObject
from PyQt5.QtGui import QColor, QPainter, QTextFormat, QTextCursor, QKeySequence

import nltk

import argparse

argParser = argparse.ArgumentParser()
argParser.add_argument('--file', type=str, help='Specify file to open')
argParser.add_argument('--mode', type=str, help='Specify mode to show specified file in on start')
args = argParser.parse_args()

# encoder = GPT2Tokenizer.from_pretrained("gpt2")
# get reverse token dictionary:
fixEncodes = tokensToUTF.getFixEncodes()


def findMainWindow():
    """helper function to conveniently get the MainWindow widget object"""
    for widget in app.topLevelWidgets():
        if isinstance(widget, QMainWindow):
            return widget
    return None


class MainWindow(QMainWindow):
    """
    Main window, holding all the top-level things
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        # get settings from file:
        if os.path.isfile('./settings.json'):
            print('Settings found!')
            with open('./settings.json', 'r', encoding='UTF-8') as settingsFile:
                self.settings = json.loads(settingsFile.read())
        else:
            print('No settings file found!')

        # window title:
        self.setWindowTitle('Gnurros FinetuneReFormatter')
        if self.settings:
            windowSize = self.settings['general']['windowSize']
            self.setGeometry(windowSize[0], windowSize[1], windowSize[2], windowSize[3],)
            windowPosition = self.settings['general']['windowPosition']
            self.move(windowPosition[0], windowPosition[1])
        else:
            self.setGeometry(1000, 1000, 800, 800)
            self.move(800, 20)

        # only check for nltk modules once:
        self.nltkLoaded = False

        # only load tokenizer once:
        self.tokenizerLoaded = False

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

        if not args.file:
            # intro screen showing on start:
            InitialIntroScreen = IntroScreen()
            self.setCentralWidget(InitialIntroScreen)
        else:
            self.curFilePath = args.file
            self.curFileName = self.curFilePath.split('/')[-1]
            self.curFileType = self.curFilePath.split('.')[-1]
            if self.curFileType == 'txt':
                try:
                    self.curData = open(self.curFilePath, "r", encoding="UTF-8").read()
                except:
                    QMessageBox.about(self, 'Error',
                                      f'The selected file ({self.curFileInfo[0]}) is not compatible! Make sure text files are UTF-8.')
                else:
                    print('Current file type is plaintext, allowing appropriate modes...')
                    self.allowedModes = ['InitialPrep', 'SourceInspector', 'StatViewer']
                    if args.mode:
                        self.setMode(args.mode)
                    else:
                        self.setMode('SourceInspector')
                    self._createMenu()
                    self.setWindowTitle(f'Gnurros FinetuneReFormatter - {self.curFileName}')
            elif self.curFileType == 'json':
                print('Current file type is JSON, allowing appropriate modes...')
                self.allowedModes = ['ChunkStack', 'ChunkCombiner']
                self.curData = json.loads(open(self.curFilePath, "r", encoding="UTF-8").read())
                if args.mode:
                    self.setMode(args.mode)
                else:
                    self.setMode('ChunkStack')
                self._createMenu()
                self.setWindowTitle(f'Gnurros FinetuneReFormatter - {self.curFileName}')

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
        if modeID == 'StatViewer':
            print('Set mode to StatViewer.')
            self.curMode = 'StatViewer'
            curStatViewer = StatViewer()
            self.setCentralWidget(curStatViewer)

    def switchMode(self):
        """quickly switch between GUI modes"""
        if self.curMode == 'ChunkStack':
            self.setMode('ChunkCombiner')
        elif self.curMode == 'ChunkCombiner':
            self.setMode('ChunkStack')
        elif self.curMode == 'SourceInspector':
            self.setMode('InitialPrep')
        elif self.curMode == 'InitialPrep':
            self.setMode('StatViewer')
        elif self.curMode == 'StatViewer':
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
                self.allowedModes = ['InitialPrep', 'SourceInspector', 'StatViewer']
                self.setMode('SourceInspector')
                # self.setMode('StatViewer')
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

    def saveAs(self):
        asFileInfo = QFileDialog.getSaveFileName(directory=f'{self.curFileName}', caption='Save as...')
        # print(asFileInfo[0])
        with open(asFileInfo[0], 'w', encoding='UTF-8') as outData:
            if self.curFileType == 'json':
                outData.write(json.dumps(self.curData))
            else:
                outData.write(self.curData)
        self.curFilePath = asFileInfo[0]
        self.curFileName = self.curFilePath.split('/')[-1]
        self.curFileType = self.curFilePath.split('.')[-1]
        self.setWindowTitle(f'Gnurros FinetuneReFormatter - {self.curFileName}')

    def saveSettings(self):
        if self.settings:
            with open('./settings.json', 'w', encoding='UTF-8') as settingsFile:
                outSettings = json.dumps(self.settings, ensure_ascii=False)
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
        self.menuFile.addAction('&Open', self.fileSelect)
        self.menuFile.addAction('&Save', self.saveCurFile)
        self.menuFile.addAction('&Save as...', self.saveAs)
        self.menuFile.addAction('&Exit', self.close)
        # if there are multiple allowed modes:
        if len(self.allowedModes) > 1:
            # add the mode menu
            self.menuMode = self.topMenu.addMenu('&Mode')
            # go through the allowed modes and add a menu option for each
            for allowedMode in self.allowedModes:
                """tried many more dynamic approaches, but none worked, so this is done explicitly for each mode..."""

                if allowedMode == 'SourceInspector':
                    self.menuMode.addAction(allowedMode, lambda: self.setMode('SourceInspector'))

                if allowedMode == 'InitialPrep':
                    self.menuMode.addAction(allowedMode, lambda: self.setMode('InitialPrep'))

                if allowedMode == 'StatViewer':
                    self.menuMode.addAction(allowedMode, lambda: self.setMode('StatViewer'))

                if allowedMode == 'ChunkStack':
                    self.menuMode.addAction(allowedMode, lambda: self.setMode('ChunkStack'))

                if allowedMode == 'ChunkCombiner':
                    self.menuMode.addAction(allowedMode, lambda: self.setMode('ChunkCombiner'))
    """
    def _createToolbar(self):
        tools = QToolBar()
        self.addToolBar(tools)
        tools.addAction('Save', self.saveData)

    def _createStatusBar(self):
        status = QStatusBar()
        status.showMessage('Nothing to tell yet...')
        self.setStatusBar(status)
    """


class IntroScreen(QWidget):
    """
    Intro splash screen with file selection and access to non-file based modes
    """
    def __init__(self):
        super(IntroScreen, self).__init__()

        self.layout = QGridLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.setLayout(self.layout)

        self.headLineLabel = QLabel('<h1><b>Gnurros Finetune-ReFormatter</h1></b>')
        self.layout.addWidget(self.headLineLabel, 0, 0)

        self.openFileButton = QPushButton('Open File')
        self.openFileButton.clicked.connect(self.openFile)
        self.layout.addWidget(self.openFileButton, 1, 0)

        self.settingsMenuButton = QPushButton('Edit Settings')
        self.settingsMenuButton.clicked.connect(self.toSettingsMenu)
        self.layout.addWidget(self.settingsMenuButton, 2, 0)

        self.exploreTokensButton = QPushButton('Explore tokens')
        self.exploreTokensButton.clicked.connect(self.toTokenExplorer)
        self.layout.addWidget(self.exploreTokensButton, 3, 0)

    def openFile(self):
        findMainWindow().fileSelect()

    def toTokenExplorer(self):
        curTokenExplorer = TokenExplorer()
        findMainWindow().setCentralWidget(curTokenExplorer)

    def toSettingsMenu(self):
        curSettingsMenu = SettingsMenu()
        findMainWindow().setCentralWidget(curSettingsMenu)


class SettingsMenu(QWidget):
    """ GUI for settings """
    def __init__(self):
        super(SettingsMenu, self).__init__()

        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.setLayout(self.layout)

        self.settings = findMainWindow().settings

        print(self.settings)

        self.initGeneralSettingsLayout()
        self.layout.addWidget(QHLine())
        self.initSourceInspectorSettingsLayout()
        self.layout.addWidget(QHLine())
        self.initInitialPrepSettingsLayout()
        self.layout.addWidget(QHLine())
        self.initChunkStackSettingsLayout()
        self.layout.addWidget(QHLine())

        self.saveSettingsButton = QPushButton('Save Settings')
        self.saveSettingsButton.clicked.connect(self.updateMainSettingsAndSave)
        self.layout.addWidget(self.saveSettingsButton)

        self.backToIntroButton = QPushButton('Back')
        self.backToIntroButton.clicked.connect(lambda: findMainWindow().setCentralWidget(IntroScreen()))
        self.layout.addWidget(self.backToIntroButton)

    def initGeneralSettingsLayout(self):
        self.generalSettingsLayout = QVBoxLayout()

        self.windowSettingsHeaderLayout = QHBoxLayout()
        self.windowSettingsHeaderLabel = QLabel('<b>Window Settings:</b>')
        self.windowSettingsHeaderLayout.addWidget(self.windowSettingsHeaderLabel)
        self.generalSettingsLayout.addLayout(self.windowSettingsHeaderLayout)

        self.windowDimensionsLayout = QHBoxLayout()

        self.windowDimensionsXPosLabel = QLabel('X position:')
        self.windowDimensionsLayout.addWidget(self.windowDimensionsXPosLabel)
        self.windowDimensionsXPosLine = QLineEdit(f"{self.settings['general']['windowSize'][0]}")
        self.windowDimensionsXPosLine.textChanged.connect(lambda: self.updateSetting(['general', 'windowSize', 0], int(self.windowDimensionsXPosLine.text())))
        self.windowDimensionsLayout.addWidget(self.windowDimensionsXPosLine)

        self.windowDimensionsYPosLabel = QLabel('Y position:')
        self.windowDimensionsLayout.addWidget(self.windowDimensionsYPosLabel)
        self.windowDimensionsYPosLine = QLineEdit(f"{self.settings['general']['windowSize'][1]}")
        self.windowDimensionsYPosLine.textChanged.connect(lambda: self.updateSetting(['general', 'windowSize', 1], int(self.windowDimensionsYPosLine.text())))
        self.windowDimensionsLayout.addWidget(self.windowDimensionsYPosLine)

        self.windowDimensionsWidthLabel = QLabel('Width:')
        self.windowDimensionsLayout.addWidget(self.windowDimensionsWidthLabel)
        self.windowDimensionsWidthLine = QLineEdit(f"{self.settings['general']['windowSize'][2]}")
        self.windowDimensionsWidthLine.textChanged.connect(lambda: self.updateSetting(['general', 'windowSize', 2], int(self.windowDimensionsWidthLine.text())))
        self.windowDimensionsLayout.addWidget(self.windowDimensionsWidthLine)

        self.windowDimensionsHeightLabel = QLabel('Height:')
        self.windowDimensionsLayout.addWidget(self.windowDimensionsHeightLabel)
        self.windowDimensionsHeightLine = QLineEdit(f"{self.settings['general']['windowSize'][3]}")
        self.windowDimensionsHeightLine.textChanged.connect(lambda: self.updateSetting(['general', 'windowSize', 3], int(self.windowDimensionsHeightLine.text())))
        self.windowDimensionsLayout.addWidget(self.windowDimensionsHeightLine)

        self.generalSettingsLayout.addLayout(self.windowDimensionsLayout)

        self.windowMoveLayout = QHBoxLayout()

        self.windowMoveXPosLabel = QLabel('Move window to X:')
        self.windowMoveLayout.addWidget(self.windowMoveXPosLabel)
        self.windowMoveXPosLine = QLineEdit(f"{self.settings['general']['windowPosition'][0]}")
        self.windowMoveXPosLine.textChanged.connect(lambda: self.updateSetting(['general', 'windowPosition', 0], int(self.windowMoveXPosLine.text())))
        self.windowMoveLayout.addWidget(self.windowMoveXPosLine)

        self.windowMoveYPosLabel = QLabel('Y:')
        self.windowMoveLayout.addWidget(self.windowMoveYPosLabel)
        self.windowMoveYPosLine = QLineEdit(f"{self.settings['general']['windowPosition'][1]}")
        self.windowMoveYPosLine.textChanged.connect(lambda: self.updateSetting(['general', 'windowPosition', 1], int(self.windowMoveYPosLine.text())))
        self.windowMoveLayout.addWidget(self.windowMoveYPosLine)

        self.generalSettingsLayout.addLayout(self.windowMoveLayout)

        self.warningsLayout = QHBoxLayout()

        self.warningsCheckbox = QCheckBox('Show overwrite warnings')
        self.warningsCheckbox.setChecked(self.settings['general']['overwriteWarnings'])
        # self.warningsCheckbox.stateChanged.connect(lambda: print(f"warnings state changed to {self.warningsCheckbox.isChecked()}"))
        self.warningsCheckbox.stateChanged.connect(lambda: self.updateSetting(['general', 'overwriteWarnings'], self.warningsCheckbox.isChecked()))
        # self.warningsCheckbox.stateChanged.connect(lambda: print(f"warnings state in settings is now {self.settings['general']['overwriteWarnings']}"))
        self.warningsLayout.addWidget(self.warningsCheckbox)

        self.generalSettingsLayout.addLayout(self.warningsLayout)

        self.layout.addLayout(self.generalSettingsLayout)

    def initSourceInspectorSettingsLayout(self):
        self.SourceInspectorSettingsLayout = QVBoxLayout()

        self.SourceInspectorSettingsHeaderLayout = QHBoxLayout()
        self.SourceInspectorSettingsHeaderLabel = QLabel('<b>SourceInspector Settings:</b>')
        self.SourceInspectorSettingsHeaderLayout.addWidget(self.SourceInspectorSettingsHeaderLabel)
        self.SourceInspectorSettingsLayout.addLayout(self.SourceInspectorSettingsHeaderLayout)

        self.SourceInspectorSettingsLineendersHeaderLayout = QHBoxLayout()

        self.SourceInspectorSettingsLineendersLabel = QLabel('Line Enders:')
        self.SourceInspectorSettingsLineendersHeaderLayout.addWidget(self.SourceInspectorSettingsLineendersLabel)

        self.SourceInspectorSettingsLayout.addLayout(self.SourceInspectorSettingsLineendersHeaderLayout)

        self.SourceInspectorSettingsLineendersListerLayout = QHBoxLayout()

        self.SourceInspectorSettingsLineendersList = QListWidget()
        self.SourceInspectorSettingsLineendersList.addItems(self.settings['SourceInspector']['lineEnders'])
        self.SourceInspectorSettingsLineendersListerLayout.addWidget(self.SourceInspectorSettingsLineendersList)

        self.SourceInspectorSettingsLineendersRemoveButton = QPushButton('Remove Line Ender')
        # self.SourceInspectorSettingsLineendersRemoveButton.clicked.connect(lambda: self.SourceInspectorSettingsLineendersList.removeItemWidget(self.SourceInspectorSettingsLineendersList.currentItem()))
        self.SourceInspectorSettingsLineendersRemoveButton.clicked.connect(lambda: self.SourceInspectorSettingsLineendersList.takeItem(self.SourceInspectorSettingsLineendersList.currentRow()))
        # self.SourceInspectorSettingsLineendersRemoveButton.clicked.connect(lambda: print([self.SourceInspectorSettingsLineendersList.item(index).text() for index in range(self.SourceInspectorSettingsLineendersList.count())]))
        self.SourceInspectorSettingsLineendersRemoveButton.clicked.connect(lambda: self.updateSetting(['SourceInspector', 'lineEnders'], [self.SourceInspectorSettingsLineendersList.item(index).text() for index in range(self.SourceInspectorSettingsLineendersList.count())]))
        self.SourceInspectorSettingsLineendersListerLayout.addWidget(self.SourceInspectorSettingsLineendersRemoveButton)

        self.SourceInspectorSettingsLayout.addLayout(self.SourceInspectorSettingsLineendersListerLayout)

        self.SourceInspectorSettingsLineendersAddLayout = QHBoxLayout()

        self.SourceInspectorSettingsLineendersAddLine = QLineEdit()
        self.SourceInspectorSettingsLineendersAddLayout.addWidget(self.SourceInspectorSettingsLineendersAddLine)

        self.SourceInspectorSettingsLineendersAddButton = QPushButton('Add Line Ender')
        self.SourceInspectorSettingsLineendersAddButton.clicked.connect(lambda: self.SourceInspectorSettingsLineendersList.addItem(self.SourceInspectorSettingsLineendersAddLine.text()))
        self.SourceInspectorSettingsLineendersAddButton.clicked.connect(lambda: self.updateSetting(['SourceInspector', 'lineEnders'], [self.SourceInspectorSettingsLineendersList.item(index).text() for index in range(self.SourceInspectorSettingsLineendersList.count())]))
        self.SourceInspectorSettingsLineendersAddButton.clicked.connect(lambda: self.SourceInspectorSettingsLineendersAddLine.setText(''))
        self.SourceInspectorSettingsLineendersAddLayout.addWidget(self.SourceInspectorSettingsLineendersAddButton)

        self.SourceInspectorSettingsLayout.addLayout(self.SourceInspectorSettingsLineendersAddLayout)

        self.layout.addLayout(self.SourceInspectorSettingsLayout)

    def initInitialPrepSettingsLayout(self):
        self.InitialPrepSettingsLayout = QVBoxLayout()

        self.InitialPrepSettingsHeaderLayout = QHBoxLayout()
        self.InitialPrepSettingsHeaderLabel = QLabel('<b>InitialPrep Settings:</b>')
        self.InitialPrepSettingsHeaderLayout.addWidget(self.InitialPrepSettingsHeaderLabel)
        self.InitialPrepSettingsLayout.addLayout(self.InitialPrepSettingsHeaderLayout)

        self.InitialPrepSettingsSentenceendPlaceholderLayout = QHBoxLayout()

        self.InitialPrepSettingsSentenceendPlaceholderLabel = QLabel('Sentence End Placeholder:')
        self.InitialPrepSettingsSentenceendPlaceholderLayout.addWidget(self.InitialPrepSettingsSentenceendPlaceholderLabel)

        self.InitialPrepSettingsSentenceendPlaceholderLine = QLineEdit(f"{self.settings['InitialPrep']['sentenceEndPlaceholder']}")
        self.InitialPrepSettingsSentenceendPlaceholderLine.textChanged.connect(lambda: self.updateSetting(['InitialPrep', 'sentenceEndPlaceholder'], self.InitialPrepSettingsSentenceendPlaceholderLine.text()))
        self.InitialPrepSettingsSentenceendPlaceholderLayout.addWidget(self.InitialPrepSettingsSentenceendPlaceholderLine)

        self.InitialPrepSettingsLayout.addLayout(self.InitialPrepSettingsSentenceendPlaceholderLayout)


        self.InitialPrepSettingsSentenceendersHeaderLayout = QHBoxLayout()
        self.InitialPrepSettingsSentenceendersLabel = QLabel('Sentence Enders:')
        self.InitialPrepSettingsSentenceendersHeaderLayout.addWidget(self.InitialPrepSettingsSentenceendersLabel)
        self.InitialPrepSettingsLayout.addLayout(self.InitialPrepSettingsSentenceendersHeaderLayout)

        self.InitialPrepSettingsSentenceendersListerLayout = QHBoxLayout()

        self.InitialPrepSettingsSentenceendersList = QListWidget()
        self.InitialPrepSettingsSentenceendersList.addItems(self.settings['InitialPrep']['sentenceEnders'])
        self.InitialPrepSettingsSentenceendersListerLayout.addWidget(self.InitialPrepSettingsSentenceendersList)

        self.InitialPrepSettingsSentenceendersRemoveButton = QPushButton('Remove Sentence Ender')
        self.InitialPrepSettingsSentenceendersRemoveButton.clicked.connect(
            lambda: self.InitialPrepSettingsSentenceendersList.takeItem(
                self.InitialPrepSettingsSentenceendersList.currentRow()))
        self.InitialPrepSettingsSentenceendersRemoveButton.clicked.connect(
            lambda: self.updateSetting(['InitialPrep', 'sentenceEnders'],
                                       [self.InitialPrepSettingsSentenceendersList.item(index).text() for index in
                                        range(self.InitialPrepSettingsSentenceendersList.count())]))
        self.InitialPrepSettingsSentenceendersListerLayout.addWidget(self.InitialPrepSettingsSentenceendersRemoveButton)

        self.InitialPrepSettingsLayout.addLayout(self.InitialPrepSettingsSentenceendersListerLayout)

        self.InitialPrepSettingsSentenceendersAddLayout = QHBoxLayout()

        self.InitialPrepSettingsSentenceendersAddLine = QLineEdit()
        self.InitialPrepSettingsSentenceendersAddLayout.addWidget(self.InitialPrepSettingsSentenceendersAddLine)

        self.InitialPrepSettingsSentenceendersAddButton = QPushButton('Add Sentence Ender')

        self.InitialPrepSettingsSentenceendersAddButton.clicked.connect(
            lambda: self.InitialPrepSettingsSentenceendersList.addItem(
                self.InitialPrepSettingsSentenceendersAddLine.text()))
        self.InitialPrepSettingsSentenceendersAddButton.clicked.connect(
            lambda: self.updateSetting(['InitialPrep', 'sentenceEnders'],
                                       [self.InitialPrepSettingsSentenceendersList.item(index).text() for index in
                                        range(self.InitialPrepSettingsSentenceendersList.count())]))
        self.InitialPrepSettingsSentenceendersAddButton.clicked.connect(
            lambda: self.InitialPrepSettingsSentenceendersAddLine.setText(''))

        self.InitialPrepSettingsSentenceendersAddLayout.addWidget(self.InitialPrepSettingsSentenceendersAddButton)

        self.InitialPrepSettingsLayout.addLayout(self.InitialPrepSettingsSentenceendersAddLayout)


        self.InitialPrepSettingsDinkussesHeaderLayout = QHBoxLayout()

        self.InitialPrepSettingsDinkussesLabel = QLabel('Standard Bad Dinkusses:')
        self.InitialPrepSettingsDinkussesHeaderLayout.addWidget(self.InitialPrepSettingsDinkussesLabel)

        self.InitialPrepSettingsLayout.addLayout(self.InitialPrepSettingsDinkussesHeaderLayout)

        self.InitialPrepSettingsDinkussesListerLayout = QHBoxLayout()

        self.InitialPrepSettingsDinkussesList = QListWidget()
        self.InitialPrepSettingsDinkussesList.addItems(self.settings['InitialPrep']['badDinkusList'])
        self.InitialPrepSettingsDinkussesListerLayout.addWidget(self.InitialPrepSettingsDinkussesList)

        self.InitialPrepSettingsDinkussesRemoveButton = QPushButton('Remove Bad Dinkus')

        self.InitialPrepSettingsDinkussesRemoveButton.clicked.connect(
            lambda: self.InitialPrepSettingsDinkussesList.takeItem(
                self.InitialPrepSettingsDinkussesList.currentRow()))
        self.InitialPrepSettingsDinkussesRemoveButton.clicked.connect(
            lambda: self.updateSetting(['InitialPrep', 'badDinkusList'],
                                       [self.InitialPrepSettingsDinkussesList.item(index).text() for index in
                                        range(self.InitialPrepSettingsDinkussesList.count())]))

        self.InitialPrepSettingsDinkussesListerLayout.addWidget(self.InitialPrepSettingsDinkussesRemoveButton)

        self.InitialPrepSettingsLayout.addLayout(self.InitialPrepSettingsDinkussesListerLayout)

        self.InitialPrepSettingsDinkussesAddLayout = QHBoxLayout()

        self.InitialPrepSettingsDinkussesAddLine = QLineEdit()
        self.InitialPrepSettingsDinkussesAddLayout.addWidget(self.InitialPrepSettingsDinkussesAddLine)

        self.InitialPrepSettingsDinkussesAddButton = QPushButton('Add Bad Dinkus')

        self.InitialPrepSettingsDinkussesAddButton.clicked.connect(
            lambda: self.InitialPrepSettingsDinkussesList.addItem(
                self.InitialPrepSettingsDinkussesAddLine.text()))
        self.InitialPrepSettingsDinkussesAddButton.clicked.connect(
            lambda: self.updateSetting(['InitialPrep', 'badDinkusList'],
                                       [self.InitialPrepSettingsDinkussesList.item(index).text() for index in
                                        range(self.InitialPrepSettingsDinkussesList.count())]))
        self.InitialPrepSettingsDinkussesAddButton.clicked.connect(
            lambda: self.InitialPrepSettingsDinkussesAddLine.setText(''))

        self.InitialPrepSettingsDinkussesAddLayout.addWidget(self.InitialPrepSettingsDinkussesAddButton)

        self.InitialPrepSettingsLayout.addLayout(self.InitialPrepSettingsDinkussesAddLayout)


        self.InitialPrepSettingsChunkingLayout = QHBoxLayout()
        self.InitialPrepSettingsChunkingTknsInfixCheckbox = QCheckBox("Add 'tokens per chunk' to ChunkFile name")
        self.InitialPrepSettingsChunkingTknsInfixCheckbox.setChecked(self.settings['InitialPrep']['chunking']['autoTokensPerChunkSuffix'])
        self.InitialPrepSettingsChunkingTknsInfixCheckbox.stateChanged.connect(lambda: self.updateSetting(['InitialPrep', 'chunking', 'autoTokensPerChunkSuffix'], self.InitialPrepSettingsChunkingTknsInfixCheckbox.isChecked()))

        self.InitialPrepSettingsChunkingLayout.addWidget(self.InitialPrepSettingsChunkingTknsInfixCheckbox)
        self.InitialPrepSettingsLayout.addLayout(self.InitialPrepSettingsChunkingLayout)

        self.layout.addLayout(self.InitialPrepSettingsLayout)

    def initChunkStackSettingsLayout(self):
        self.ChunkStackSettingsLayout = QVBoxLayout()

        self.ChunkStackSettingsHeaderLayout = QHBoxLayout()
        self.ChunkStackSettingsHeaderLabel = QLabel('<b>ChunkStack Settings:</b>')
        self.ChunkStackSettingsHeaderLayout.addWidget(self.ChunkStackSettingsHeaderLabel)
        self.ChunkStackSettingsLayout.addLayout(self.ChunkStackSettingsHeaderLayout)

        self.ChunkStackSettingsMaxDisplayChunksLayout = QHBoxLayout()

        self.ChunkStackSettingsMaxDisplayChunksLabel = QLabel('Maximum number of chunks in view:')
        self.ChunkStackSettingsMaxDisplayChunksLayout.addWidget(self.ChunkStackSettingsMaxDisplayChunksLabel)

        self.ChunkStackSettingsMaxDisplayChunksSpin = QSpinBox()
        self.ChunkStackSettingsMaxDisplayChunksSpin.setValue(self.settings['ChunkStack']['maxDisplayedChunks'])
        self.ChunkStackSettingsMaxDisplayChunksSpin.setMinimum(1)

        self.ChunkStackSettingsMaxDisplayChunksSpin.valueChanged.connect(lambda: self.updateSetting(['ChunkStack', 'maxDisplayedChunks'], self.ChunkStackSettingsMaxDisplayChunksSpin.value()))

        self.ChunkStackSettingsMaxDisplayChunksLayout.addWidget(self.ChunkStackSettingsMaxDisplayChunksSpin)

        self.ChunkStackSettingsLayout.addLayout(self.ChunkStackSettingsMaxDisplayChunksLayout)


        self.ChunkStackSettingsInsertChunktypeLayout = QHBoxLayout()

        self.ChunkStackSettingsInsertChunktypeLabel = QLabel('Type of inserted chunks:')
        self.ChunkStackSettingsInsertChunktypeLayout.addWidget(self.ChunkStackSettingsInsertChunktypeLabel)

        self.ChunkStackSettingsInsertChunktypeLine = QLineEdit(f"{self.settings['ChunkStack']['insertChunkType']}")
        self.ChunkStackSettingsInsertChunktypeLine.textChanged.connect(lambda: self.updateSetting(['ChunkStack', 'insertChunkType'], self.ChunkStackSettingsInsertChunktypeLine.text()))
        self.ChunkStackSettingsInsertChunktypeLayout.addWidget(self.ChunkStackSettingsInsertChunktypeLine)

        self.ChunkStackSettingsLayout.addLayout(self.ChunkStackSettingsInsertChunktypeLayout)

        self.ChunkStackSettingsInsertChunktextLayout = QHBoxLayout()
        self.ChunkStackSettingsInsertChunktextLabel = QLabel('Text in inserted chunks:')
        self.ChunkStackSettingsInsertChunktextLayout.addWidget(self.ChunkStackSettingsInsertChunktextLabel)

        self.ChunkStackSettingsInsertChunktextLine = QLineEdit(f"{self.settings['ChunkStack']['insertChunkText']}")
        self.ChunkStackSettingsInsertChunktextLine.textChanged.connect(lambda: self.updateSetting(['ChunkStack', 'insertChunkText'], self.ChunkStackSettingsInsertChunktextLine.text()))
        self.ChunkStackSettingsInsertChunktextLayout.addWidget(self.ChunkStackSettingsInsertChunktextLine)

        self.ChunkStackSettingsLayout.addLayout(self.ChunkStackSettingsInsertChunktextLayout)


        self.layout.addLayout(self.ChunkStackSettingsLayout)

    def updateSetting(self, setting, value):
        if len(setting) == 2:
            self.settings[f"{setting[0]}"][f"{setting[1]}"] = value
        if len(setting) == 3:
            # print(type(setting[2]))
            if type(setting[2]) is int:
                self.settings[f"{setting[0]}"][f"{setting[1]}"][setting[2]] = value
            else:
                self.settings[f"{setting[0]}"][f"{setting[1]}"][f"{setting[2]}"] = value

        print('Settings changed:')
        print(self.settings)

    def updateMainSettingsAndSave(self):
        findMainWindow().settings = self.settings
        findMainWindow().saveSettings()


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
        self.textField.setPlainText(findMainWindow().curData)
        self.textField.textChanged.connect(self.textChange)

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

        self.layout.addWidget(self.newlinesLabel, 0, 0)
        self.layout.addWidget(self.newlineModeComboBox, 0, 1)
        self.layout.addWidget(self.issueBrowseLabel, 0, 2)
        self.layout.addWidget(self.prevIssueButton, 0, 3)
        self.layout.addWidget(self.nextIssueButton, 0, 4)

        self.layout.addWidget(self.textField, 1, 0, 1, 5)

    def newLineModeChange(self):
        """newline checking mode selection and updating"""
        self.newlineMode = self.newlineModeComboBox.currentText()
        print(f'Newline checking mode set to {self.newlineMode}')
        self.countBadLines()
        self.findBadLines()

    def countBadLines(self):
        """
        count 'bad lines'/newlines that might be detrimental for finetuning

        TODO:
            - untangle this into proper methods
            - add 'multiple caps at line start' checker
        """
        # make sure that counter/list are empty to prevent duplicates:
        self.badLineList = []
        priorBadLineCount = self.badLineCount
        self.badLineCount = 0
        # list of strings that are proper ends of lines/end sentences:
        if findMainWindow().settings:
            print('line ender settings found!')
            lineEnders = findMainWindow().settings['SourceInspector']['lineEnders']
        else:
            lineEnders = ['.', '!', '?', '<|endoftext|>', '”', '“', ':', '—', '*', ')', '_', '’', ']', ',', '"']
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

    def textChange(self):
        """event method for realtime text checking"""
        # update newline checks:
        self.newlineCount = self.textField.toPlainText().count('\n')
        self.textLines = self.textField.toPlainText().split('\n')
        self.countBadLines()
        # update the cached text at toplevel:
        findMainWindow().curData = self.textField.toPlainText()
        findMainWindow().toggleFileUnsaved()


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
    Utility mode to perform simple data preparation

    TODO:
        - more quick utilities:
            - PDF export issue fixes?
                - page numbers
                - headers
            - wiki fixes from other prep scripts?
        - QuickFixes:
            -
        - file saving dialogs?
    """
    def __init__(self):
        super(InitialPrep, self).__init__()

        self.layout = QGridLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.setLayout(self.layout)

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
        if findMainWindow().settings:
            self.makeChunksFileTknsPerChunk.setValue(findMainWindow().settings['InitialPrep']['chunking']['targetTokensPerChunk'])
        self.makeChunksFileTknsPerChunk.setMaximum(200)  # subject to change
        if findMainWindow().settings:
            self.makeChunksFileTknsPerChunk.setMaximum(findMainWindow().settings['InitialPrep']['chunking']['maxTokensPerChunk'])
        # placeholder chunks insertion:
        self.makeChunksFileInsertsCheckbox = QCheckBox('Insert placeholder chunks')
        if findMainWindow().settings:
            self.makeChunksFileInsertsCheckbox.setChecked(findMainWindow().settings['InitialPrep']['chunking']['addPlaceholders'])
        # placeholder chunk interval:
        # TODO: add this?
        # self.makeChunksFileInsertsIntervalLabel = QLabel('Chunk insertion interval:')
        # self.makeChunksFileInsertsInterval = QSpinBox()
        # self.makeChunksFileInsertsInterval.setMinimum(2)
        # placeholder chunk metadata type:
        self.makeChunksFileInsertsTypeLabel = QLabel('Placeholder type tag:')
        self.makeChunksFileInsertsTypeString = 'generic'
        if findMainWindow().settings:
            self.makeChunksFileInsertsTypeString = findMainWindow().settings['InitialPrep']['chunking']['placeholderType']
        self.makeChunksFileInsertsType = QLineEdit(self.makeChunksFileInsertsTypeString)
        self.makeChunksFileInsertsType.setMaxLength(12)
        # placeholder chunk placeholder text:
        self.makeChunksFileInsertsTextLabel = QLabel('Placeholder text:')
        self.makeChunksFileInsertsTextString = 'PLACEHOLDER'
        if findMainWindow().settings:
            self.makeChunksFileInsertsTextString = findMainWindow().settings['InitialPrep']['chunking']['placeholderText']
        self.makeChunksFileInsertsText = QLineEdit(self.makeChunksFileInsertsTextString)
        # chunk file export:
        self.makeChunksFileTknSuffix = f'Chunk file suffix: _{self.makeChunksFileTknsPerChunk.value()}'
        if findMainWindow().settings:
            if not findMainWindow().settings['InitialPrep']['chunking']['autoTokensPerChunkSuffix']:
                self.makeChunksFileTknSuffix = f'Chunk file suffix: _'
        self.makeChunksFileSuffixLabel = QLabel(self.makeChunksFileTknSuffix)
        self.makeChunksFileSuffixString = 'tknChunks'
        if findMainWindow().settings:
            self.makeChunksFileSuffixString = findMainWindow().settings['InitialPrep']['chunking']['chunkFileSuffix']
        self.makeChunksFileSuffix = QLineEdit(self.makeChunksFileSuffixString)
        self.makeChunksButton = QPushButton('Create chunks and save')
        self.makeChunksButton.clicked.connect(self.exportChunks)
        # save chunking settings button:
        self.saveChunkingSettingsButton = QPushButton('Save chunking settings')
        self.saveChunkingSettingsButton.clicked.connect(self.saveChunkingSettings)

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

        # find bad paragraph break characters:
        self.badDinkusFindButton = QPushButton('Find bad breakers')
        self.badDinkusFindButton.clicked.connect(self.badDinkusFind)
        self.badDinkusLabel = QLabel('Found bad breakers:')
        self.foundDinkusses = []
        # replace bad paragraph break characters:
        self.badDinkusReplaceButton = QPushButton('Remove bad paragraph breakers')
        self.badDinkusReplaceButton.clicked.connect(self.badDinkusReplace)

        # remove tab characters:
        self.tabRemoveButton = QPushButton('Remove tab characters')
        self.tabRemoveButton.clicked.connect(self.tabRemove)

        # replace fancy quotes:
        self.quoteReplaceButton = QPushButton('Replace fancy quote characters')
        self.quoteReplaceButton.clicked.connect(self.quoteReplace)

        self.layout.addWidget(self.chopSentencesFileSuffixLabel, 0, 0)
        self.layout.addWidget(self.chopSentencesFileSuffix, 0, 1)
        self.layout.addWidget(self.chopSentencesButton, 0, 2)

        self.layout.addWidget(self.makeChunksHeaderLabel, 1, 0)

        self.layout.addWidget(self.makeChunksFileTknsPerChunkLabel, 2, 0)
        self.layout.addWidget(self.makeChunksFileTknsPerChunk, 2, 1)

        self.layout.addWidget(self.makeChunksFileInsertsCheckbox, 3, 0)
        self.layout.addWidget(self.makeChunksFileInsertsTypeLabel, 3, 1)
        self.layout.addWidget(self.makeChunksFileInsertsType, 3, 2)
        self.layout.addWidget(self.makeChunksFileInsertsTextLabel, 3, 3)
        self.layout.addWidget(self.makeChunksFileInsertsText, 3, 4)

        self.layout.addWidget(self.makeChunksFileSuffixLabel, 4, 0)
        self.layout.addWidget(self.makeChunksFileSuffix, 4, 1)
        self.layout.addWidget(self.makeChunksButton, 4, 2)
        self.layout.addWidget(self.saveChunkingSettingsButton, 4, 3)

        self.layout.addWidget(self.miscPrepLabel, 5, 0)

        self.layout.addWidget(self.lineEndSpaceRemoveButton, 6, 0)
        self.layout.addWidget(self.lineStartSpaceRemoveButton, 6, 1)
        self.layout.addWidget(self.doubleNewlineRemoveButton, 6, 2)
        self.layout.addWidget(self.blockLayoutRemoveButton, 6, 3)

        self.layout.addWidget(self.badDinkusFindButton, 7, 0)
        self.layout.addWidget(self.badDinkusLabel, 7, 1)
        self.layout.addWidget(self.badDinkusReplaceButton, 7, 2)

        self.layout.addWidget(self.tabRemoveButton, 8, 0)
        self.layout.addWidget(self.quoteReplaceButton, 8, 1)

    def exportSentenceList(self):
        """exports data split into sentences as JSON (array)"""
        # sentences:
        if findMainWindow().settings:
            sentenceEnders = findMainWindow().settings['InitialPrep']['sentenceEnders']
        else:
            sentenceEnders = ['.', '!', '?', ':']
        if findMainWindow().settings:
            self.sentenceEndPlaceholder = findMainWindow().settings['InitialPrep']['sentenceEndPlaceholder']
        else:
            self.sentenceEndPlaceholder = '%%%%%'
        rawSentencesMarked = findMainWindow().curData
        for sentenceEnder in sentenceEnders:
            rawSentencesMarked = rawSentencesMarked.replace(f"{sentenceEnder}",
                                                            f"{sentenceEnder}{self.sentenceEndPlaceholder}")
        self.sentences = rawSentencesMarked.split(f"{self.sentenceEndPlaceholder}")
        # export:
        with open(f'{findMainWindow().curFilePath.replace(".txt", "")}{self.chopSentencesFileSuffix.text()}.json', 'w', encoding='utf-8') as sentenceOutFile:
            sentenceOutFile.write(json.dumps(self.sentences, ensure_ascii=False))

    def exportChunks(self):
        """
        build chunks of a defined number of tokens from complete sentences and save as chunkFile

        TODO:
            - fix wonky parts
            - make placeholder insertion generic?
                - allow more placeholders
                - allow other spacing
        """

        if not findMainWindow().tokenizerLoaded:
            global encoder
            encoder = GPT2Tokenizer.from_pretrained("gpt2")
            findMainWindow().tokenizerLoaded = True

        # sentences:
        if findMainWindow().settings:
            sentenceEnders = findMainWindow().settings['InitialPrep']['sentenceEnders']
        else:
            sentenceEnders = ['.', '!', '?', ':']
        if findMainWindow().settings:
            self.sentenceEndPlaceholder = findMainWindow().settings['InitialPrep']['sentenceEndPlaceholder']
        else:
            self.sentenceEndPlaceholder = '%%%%%'
        rawSentencesMarked = findMainWindow().curData
        for sentenceEnder in sentenceEnders:
            rawSentencesMarked = rawSentencesMarked.replace(f"{sentenceEnder}",
                                                            f"{sentenceEnder}{self.sentenceEndPlaceholder}")
        self.sentences = rawSentencesMarked.split(f"{self.sentenceEndPlaceholder}")

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
                # if curChunk[-1] == " ":
                    # curChunk = curChunk[:-1]
                # print('Cropped trailing space.')
                # if curChunk[0] == " ":
                    # curChunk = curChunk[1:]
                # print('Cropped leading space.')
                curChunk = curChunk.replace(" \n\n", "\n\n")
                # print('Cropped line trailing spaces.')
                curChunk = curChunk.replace("  ", " ")
                # print('Cropped double spaces.')
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

        if findMainWindow().settings:
            if findMainWindow().settings['general']['overwriteWarnings']:
                if os.path.isfile(f'{findMainWindow().curFilePath.replace(".txt", "")}_{self.makeChunksFileTknsPerChunk.value()}{self.makeChunksFileSuffix.text()}.json'):
                    overWriteWarnBox = QMessageBox.question(self, 'Overwrite Warning', f'"{findMainWindow().curFilePath.replace(".txt", "")}_{self.makeChunksFileTknsPerChunk.value()}{self.makeChunksFileSuffix.text()}.json" already exists! Do you want to overwrite it?', QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Cancel)
                    if overWriteWarnBox == QMessageBox.Ok:
                        with open(f'{findMainWindow().curFilePath.replace(".txt", "")}_{self.makeChunksFileTknsPerChunk.value()}{self.makeChunksFileSuffix.text()}.json', 'w', encoding='utf-8') as chunksOutFile:
                            chunksOutFile.write(fullDataJSON)
                else:
                    with open(f'{findMainWindow().curFilePath.replace(".txt", "")}_{self.makeChunksFileTknsPerChunk.value()}{self.makeChunksFileSuffix.text()}.json', 'w', encoding='utf-8') as chunksOutFile:
                        chunksOutFile.write(fullDataJSON)
            else:
                with open(f'{findMainWindow().curFilePath.replace(".txt", "")}_{self.makeChunksFileTknsPerChunk.value()}{self.makeChunksFileSuffix.text()}.json', 'w', encoding='utf-8') as chunksOutFile:
                    chunksOutFile.write(fullDataJSON)
        else:
            with open(f'{findMainWindow().curFilePath.replace(".txt", "")}_{self.makeChunksFileTknsPerChunk.value()}{self.makeChunksFileSuffix.text()}.json', 'w', encoding='utf-8') as chunksOutFile:
                chunksOutFile.write(fullDataJSON)

    def updateTokensPerChunk(self):
        """inserts desired token number into suffix automatically"""
        self.makeChunksFileTknSuffix = f'Chunk file suffix: _{self.makeChunksFileTknsPerChunk.value()}'
        if findMainWindow().settings:
            if not findMainWindow().settings['InitialPrep']['chunking']['autoTokensPerChunkSuffix']:
                self.makeChunksFileTknSuffix = f'Chunk file suffix: _'
        self.makeChunksFileSuffixLabel.setText(self.makeChunksFileTknSuffix)

    def saveChunkingSettings(self):
        if findMainWindow().settings:
            findMainWindow().settings['InitialPrep']['chunking']['targetTokensPerChunk'] = self.makeChunksFileTknsPerChunk.value()
            findMainWindow().settings['InitialPrep']['chunking']['addPlaceholders'] = self.makeChunksFileInsertsCheckbox.isChecked()
            findMainWindow().settings['InitialPrep']['chunking']['placeholderType'] = self.makeChunksFileInsertsType.text()
            findMainWindow().settings['InitialPrep']['chunking']['placeholderText'] = self.makeChunksFileInsertsText.text()
            findMainWindow().settings['InitialPrep']['chunking']['chunkFileSuffix'] = self.makeChunksFileSuffix.text()
            findMainWindow().saveSettings()

    def lineEndSpaceRemove(self):
        """removes spaces at line ends"""
        findMainWindow().curData = re.sub(r' +\n', '\n', findMainWindow().curData)
        if findMainWindow().curData[-1] == ' ':
            findMainWindow().curData = findMainWindow().curData[0:-1]
        findMainWindow().toggleFileUnsaved()

    def lineStartSpaceRemove(self):
        """removes spaces at line beginnings"""
        findMainWindow().curData = re.sub(r'\n +', '\n', findMainWindow().curData)
        findMainWindow().toggleFileUnsaved()

    def doubleNewlineRemove(self):
        """removes double newlines"""
        findMainWindow().curData = findMainWindow().curData.replace('\n\n', '\n')
        findMainWindow().toggleFileUnsaved()

    def blockLayoutRemove(self):
        """removes block layout GREEDILY"""
        greedyBlockLayoutRemoveWarnBox = QMessageBox.question(self, 'Warning',
                                                f'Block layout removal is a brute force method and will remove all single linebreaks indiscriminately! '
                                                f'Double newlines will be preserved.\nClick OK if you are sure that this will not remove too much.',
                                                QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Cancel)
        if greedyBlockLayoutRemoveWarnBox == QMessageBox.Ok:
            doubleNewlinePlaceholder = '%%%%%'
            if findMainWindow().settings:
                doubleNewlinePlaceholder = findMainWindow().settings['InitialPrep']['sentenceEndPlaceholder']
            findMainWindow().curData = findMainWindow().curData.replace('\n\n', doubleNewlinePlaceholder)
            findMainWindow().curData = findMainWindow().curData.replace('\n', ' ')
            # the line above can lead to double spaces if the source has trailing/leading spaces on lines
            # so those get removed, as well:
            findMainWindow().curData = findMainWindow().curData.replace('  ', ' ')
            findMainWindow().curData = findMainWindow().curData.replace(doubleNewlinePlaceholder, '\n\n')
            findMainWindow().toggleFileUnsaved()

    def badDinkusFind(self):
        self.badDinkusExp = r'\n[^a-zA-Z0-9_\n]+\n'
        self.foundDinkusses = re.findall(self.badDinkusExp, findMainWindow().curData)
        self.foundDinkusses = list(filter(lambda a: a != '\n***\n', self.foundDinkusses))
        self.badDinkusLabel.setText(f'Found bad breakers:{"".join(self.foundDinkusses)}')

    def badDinkusReplace(self):
        if not self.foundDinkusses:
            if findMainWindow().settings:
                badDinkusList = findMainWindow().settings['InitialPrep']['badDinkusList']
            else:
                badDinkusList = ["❦", "§", "#", "◇", "◇ ◇ ◇", "◇◇◇", "◆", "◆◆◆", "◆ ◆ ◆", "◆ ◇ ◆", "●", "✽ ✽ ✽",
                                 "※※※※※", "× ×", "~~~"]
        else:
            badDinkusList = list(set(self.foundDinkusses))
            for dinkusID in range(len(badDinkusList)):
                badDinkusList[dinkusID] = badDinkusList[dinkusID].replace('\n', '')
        for badDinkus in badDinkusList:
            findMainWindow().curData = re.sub(f'\n{badDinkus}\n', '\n***\n', findMainWindow().curData)
        findMainWindow().toggleFileUnsaved()

    def tabRemove(self):
        """removes tab characters"""
        findMainWindow().curData = findMainWindow().curData.replace('\t', '')
        findMainWindow().toggleFileUnsaved()

    def quoteReplace(self):
        """replaces fancy quote characters with standard ones"""
        findMainWindow().curData = re.sub(r'[“”]', '"', findMainWindow().curData)
        findMainWindow().curData = re.sub(r'[‘’]', "'", findMainWindow().curData)
        findMainWindow().toggleFileUnsaved()


class StatViewer(QWidget):
    """ Calculate various statistics """
    def __init__(self):
        super(StatViewer, self).__init__()

        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.setLayout(self.layout)
        # prepare attributes:
        # basics:
        self.charCount = 0
        self.wordCount = 0
        self.lines = []
        self.lineCount = 0
        self.lineLengths = []
        self.sentences = []
        # tokens:
        self.tokens = []
        self.tokenCount = 0
        self.uniqueTokens = []
        self.uniqueTokenCount = 0
        self.tokenDistribution = {}
        self.tokenBigramCounts = []
        # POS:
        self.taggedPOS = []
        self.verbCount = 0
        # word distribution:
        self.uniqueWords = []
        self.uniqueWordCount = 0
        self.wordDistribution = {}
        # special line counts:
        self.quoteLineCount = 0
        # check for needed nltk modules:
        if not findMainWindow().nltkLoaded:
            nltk.download('punkt')
            nltk.download('averaged_perceptron_tagger')
            findMainWindow().nltkLoaded = True
        # initialize layout:
        self.initStatsHeader()
        self.initBaseStatsLayout()
        self.layout.addWidget(QHLine())
        self.initTokenStatsLayout()
        self.layout.addWidget(QHLine())
        self.initOtherStatsLayout()
        self.layout.addWidget(QHLine())
        self.initStatsProgressbar()
        self.initStatsExportButtons()

    def initStatsHeader(self):
        self.statHeaderLayout = QHBoxLayout()
        self.statHeaderLabel = QLabel('<b>Statistics:</b>')
        self.statHeaderLayout.addWidget(self.statHeaderLabel)
        self.layout.addLayout(self.statHeaderLayout)

    def initBaseStatsLayout(self):
        self.baseStatsLayout = QVBoxLayout()
        self.baseStatsButtonsLayout = QHBoxLayout()
        self.baseStatsDisplayLayout = QHBoxLayout()

        # basic stats button:
        self.baseStatsButton = QPushButton('Calculate basic statistics')
        self.baseStatsButton.clicked.connect(self.getStatsWithBar)
        self.baseStatsButtonsLayout.addWidget(self.baseStatsButton)

        # line lengths button:
        self.lineLengthsButton = QPushButton('Count line lengths')
        self.lineLengthsButton.setEnabled(False)
        self.lineLengthsButton.clicked.connect(self.getLineLengthsWithBar)
        self.baseStatsButtonsLayout.addWidget(self.lineLengthsButton)

        # word distribution button:
        self.wordDistButton = QPushButton('Calculate word distribution')
        self.wordDistButton.setEnabled(False)
        self.wordDistButton.clicked.connect(self.getWordDistWithBar)
        self.baseStatsButtonsLayout.addWidget(self.wordDistButton)

        # basics label:
        self.dataStatsLabel = QLabel('Basics:')
        self.baseStatsDisplayLayout.addWidget(self.dataStatsLabel)

        # line lengths label:
        self.lineLengthsLabel = QLabel()
        self.baseStatsDisplayLayout.addWidget(self.lineLengthsLabel)

        # word frequencies label:
        self.wordFreqLabel = QLabel()
        self.baseStatsDisplayLayout.addWidget(self.wordFreqLabel)

        self.baseStatsLayout.addLayout(self.baseStatsDisplayLayout)
        self.baseStatsLayout.addLayout(self.baseStatsButtonsLayout)
        self.layout.addLayout(self.baseStatsLayout)

    def initTokenStatsLayout(self):
        self.tokenStatsLayout = QVBoxLayout()
        self.tokenStatsButtonsLayout = QHBoxLayout()
        self.tokenStatsDisplayLayout = QHBoxLayout()

        # tokenize button:
        self.tokenizeButton = QPushButton('Tokenize data')
        self.tokenizeButton.clicked.connect(self.tokenizeDataWithBar)
        self.tokenStatsButtonsLayout.addWidget(self.tokenizeButton)

        # token distribution button:
        self.tokenDistributionButton = QPushButton('Calculate token distribution')
        self.tokenDistributionButton.setEnabled(False)
        self.tokenDistributionButton.clicked.connect(self.calculateTokenDistributionWithBar)
        self.tokenStatsButtonsLayout.addWidget(self.tokenDistributionButton)

        # token bigram count button:
        self.tokenBigramsButton = QPushButton('Get token bigrams')
        self.tokenBigramsButton.setEnabled(False)
        self.tokenBigramsButton.clicked.connect(self.getTokenBigramsWithBar)
        self.tokenStatsButtonsLayout.addWidget(self.tokenBigramsButton)

        self.tokenCountLabel = QLabel(f'Tokens:')
        self.tokenStatsDisplayLayout.addWidget(self.tokenCountLabel)

        self.tokenDistLabel = QLabel()
        self.tokenStatsDisplayLayout.addWidget(self.tokenDistLabel)

        self.tokenBigramsLabel = QLabel()
        self.tokenStatsDisplayLayout.addWidget(self.tokenBigramsLabel)

        self.tokenStatsLayout.addLayout(self.tokenStatsDisplayLayout)
        self.tokenStatsLayout.addLayout(self.tokenStatsButtonsLayout)
        self.layout.addLayout(self.tokenStatsLayout)

    def initOtherStatsLayout(self):
        self.otherStatsLayout = QVBoxLayout()
        self.otherStatsButtonsLayout = QHBoxLayout()
        self.otherStatsDisplayLayout = QHBoxLayout()

        # POS button:
        self.tagPOSButton = QPushButton('Tag POS and count verbs')
        self.tagPOSButton.clicked.connect(self.getPOSWithBar)
        self.otherStatsButtonsLayout.addWidget(self.tagPOSButton)

        # quote lines button:
        self.quoteLineCountButton = QPushButton('Count lines beginning with quotes')
        self.quoteLineCountButton.setEnabled(False)
        self.quoteLineCountButton.clicked.connect(self.getQuoteLineCountWithBar)
        self.otherStatsButtonsLayout.addWidget(self.quoteLineCountButton)

        self.moreInfoLabel = QLabel(f'Other:')
        self.otherStatsDisplayLayout.addWidget(self.moreInfoLabel)

        self.otherStatsLayout.addLayout(self.otherStatsDisplayLayout)
        self.otherStatsLayout.addLayout(self.otherStatsButtonsLayout)
        self.layout.addLayout(self.otherStatsLayout)

    def initStatsProgressbar(self):
        self.statProgressLayout = QHBoxLayout()

        self.statProgressLabel = QLabel('Progress:')
        self.statProgressLayout.addWidget(self.statProgressLabel)

        self.statProgressBar = QProgressBar()
        self.statProgressLayout.addWidget(self.statProgressBar)

        self.layout.addLayout(self.statProgressLayout)

    def startBusyBar(self):
        # show that this thing is working:
        self.statProgressBar.setMinimum(0)
        self.statProgressBar.setMaximum(0)

    def stopBusyBar(self):
        # show that this thing is done:
        self.statProgressBar.setMaximum(100)

    def setBarRange(self, min, max):
        self.statProgressBar.setRange(min, max)

    def setBarMax(self, max):
        self.statProgressBar.setRange(0, max)

    def setBarValue(self, value):
        self.statProgressBar.setValue(value)

    def resetBar(self):
        self.statProgressBar.reset()

    def initStatsExportButtons(self):
        self.statExportButtonsLayout = QHBoxLayout()
        # stats and token distribution export:
        self.exportStatsAndTknDistButton = QPushButton('Export statistics')
        self.exportStatsAndTknDistButton.clicked.connect(self.exportStatsAndTknDist)
        self.statExportButtonsLayout.addWidget(self.exportStatsAndTknDistButton)
        self.layout.addLayout(self.statExportButtonsLayout)

    def updateStatsData(self, data):
        setattr(self, data[0], data[1])

    def getStatsWithBar(self):
        """Calculates basic statistics in a separate thread to allow progress bar use"""
        # create separate thread with appropriate worker:
        self.statsThread = QThread()
        self.statsWorker = StatsWorker('getDataStats')
        self.statsWorker.moveToThread(self.statsThread)
        self.statsThread.started.connect(self.statsWorker.run)
        # connect the worker to get data while active:
        self.statsWorker.taskReturn.connect(self.updateStatsData)
        # connect the worker to apply updates when finished:
        self.statsWorker.taskFinished.connect(self.stopBusyBar)
        self.statsWorker.taskFinished.connect(lambda: self.wordDistButton.setEnabled(True))
        self.statsWorker.taskFinished.connect(lambda: self.lineLengthsButton.setEnabled(True))
        self.statsWorker.taskFinished.connect(lambda: self.quoteLineCountButton.setEnabled(True))
        self.statsWorker.taskFinished.connect(self.stopBusyBar)
        self.statsWorker.taskFinished.connect(lambda:
                                              self.dataStatsLabel.setText(f'Basics:\n'
                                                                          f'Number of characters: {self.charCount}\n'
                                                                          f'Number of words: ~{self.wordCount}\n'
                                                                          f'Number of lines: {self.lineCount}\n'
                                                                          f'Number of sentences: ~{len(self.sentences)}')
                                              )
        # clean up thread when finished:
        self.statsWorker.taskFinished.connect(self.statsThread.quit)
        self.statsWorker.taskFinished.connect(self.statsWorker.deleteLater)
        self.statsThread.finished.connect(self.statsThread.deleteLater)
        # start the busy indicator and run worker:
        self.startBusyBar()
        self.statsThread.start()

    def getWordDistWithBar(self):
        """Calculate word distribution using separate thread to allow progress bar updates"""
        # create separate thread with appropriate worker:
        self.statsThread = QThread()
        self.statsWorker = StatsWorker('getWordDistribution')
        self.statsWorker.moveToThread(self.statsThread)
        self.statsThread.started.connect(self.statsWorker.run)
        # connect the worker to get data while active:
        self.statsWorker.taskReturn.connect(self.updateStatsData)
        self.statsWorker.taskProgressBarMax.connect(self.setBarMax)
        self.statsWorker.taskProgress.connect(self.setBarValue)
        # connect the worker to apply updates when finished:
        self.statsWorker.taskFinished.connect(self.resetBar)
        # self.statsWorker.taskFinished.connect(lambda: print(self.wordDistribution))
        self.statsWorker.taskFinished.connect(self.showTopWords)
        # clean up thread when finished:
        self.statsWorker.taskFinished.connect(self.statsThread.quit)
        self.statsWorker.taskFinished.connect(self.statsWorker.deleteLater)
        self.statsThread.finished.connect(self.statsThread.deleteLater)
        # start the worker:
        self.statsThread.start()

    def showTopWords(self):
        showTopWordsString = ''
        topWordAmount = 10

        for wordFrequency in self.wordDistribution[:topWordAmount]:
            showTopWordsString += f'{wordFrequency[0]} {wordFrequency[1]}\n'

        self.wordFreqLabel.setText(f'Word counts:\n'
                                   f'Unique words: {self.uniqueWordCount}\n'
                                   f'Most frequent words:\n'
                                   f'{showTopWordsString}')

    def getLineLengthsWithBar(self):
        """Calculate line lengths using separate thread to allow progress bar updates"""
        # create separate thread with appropriate worker:
        self.statsThread = QThread()
        self.statsWorker = StatsWorker('getLineLengths')
        self.statsWorker.moveToThread(self.statsThread)
        self.statsThread.started.connect(self.statsWorker.run)
        # connect the worker to get data while active:
        self.statsWorker.taskReturn.connect(self.updateStatsData)
        self.statsWorker.taskProgressBarMax.connect(self.setBarMax)
        self.statsWorker.taskProgress.connect(self.setBarValue)
        # connect the worker to apply updates when finished:
        self.statsWorker.taskFinished.connect(self.resetBar)
        self.statsWorker.taskFinished.connect(lambda: self.lineLengthsLabel.setText(f'Line length:\n'
                                                                                    f'Average: {sum(self.lineLengths)/self.lineCount}\n'
                                                                                    f'Maximum: {max(self.lineLengths)}\n'
                                                                                    f'Minimum: {min(self.lineLengths)}'))
        # clean up thread when finished:
        self.statsWorker.taskFinished.connect(self.statsThread.quit)
        self.statsWorker.taskFinished.connect(self.statsWorker.deleteLater)
        self.statsThread.finished.connect(self.statsThread.deleteLater)
        # start the worker:
        self.statsThread.start()

    def getQuoteLineCountWithBar(self):
        """Count lines beginning with quotes using separate thread to allow progress bar updates"""
        # create separate thread with appropriate worker:
        self.statsThread = QThread()
        self.statsWorker = StatsWorker('getQuoteLineCount')
        self.statsWorker.moveToThread(self.statsThread)
        self.statsThread.started.connect(self.statsWorker.run)
        # connect the worker to get data while active:
        self.statsWorker.taskReturn.connect(self.updateStatsData)
        self.statsWorker.taskProgressBarMax.connect(self.setBarMax)
        self.statsWorker.taskProgress.connect(self.setBarValue)
        # connect the worker to apply updates when finished:
        self.statsWorker.taskFinished.connect(lambda: self.moreInfoLabel.setText(f'Other:\n'
                                                                                 f'Lines beginning with quotes: {self.quoteLineCount}'))
        self.statsWorker.taskFinished.connect(self.resetBar)
        # clean up thread when finished:
        self.statsWorker.taskFinished.connect(self.statsThread.quit)
        self.statsWorker.taskFinished.connect(self.statsWorker.deleteLater)
        self.statsThread.finished.connect(self.statsThread.deleteLater)
        # start the worker:
        self.statsThread.start()

    def getPOSWithBar(self):
        """Tags POS and counts verbs in a separate thread to allow progress bar use"""
        # create separate thread with appropriate worker:
        self.statsThread = QThread()
        self.statsWorker = StatsWorker('getPOS')
        self.statsWorker.moveToThread(self.statsThread)
        self.statsThread.started.connect(self.statsWorker.run)
        # connect the worker to get data while active:
        self.statsWorker.taskReturn.connect(self.updateStatsData)
        # connect the worker to apply updates when finished:
        self.statsWorker.taskFinished.connect(self.stopBusyBar)
        self.statsWorker.taskFinished.connect(lambda: self.moreInfoLabel.setText(f'Other:\n'
                                                                                 f'Number of verbs: {self.verbCount}'))
        # clean up thread when finished:
        self.statsWorker.taskFinished.connect(self.statsThread.quit)
        self.statsWorker.taskFinished.connect(self.statsWorker.deleteLater)
        self.statsThread.finished.connect(self.statsThread.deleteLater)
        # start the busy indicator and run worker:
        self.startBusyBar()
        self.statsThread.start()

    def tokenizeDataWithBar(self):
        """Tokenizes text in a separate thread to allow progress bar use"""
        # create separate thread with appropriate worker:
        self.statsThread = QThread()
        self.statsWorker = StatsWorker('tokenizeData')
        self.statsWorker.moveToThread(self.statsThread)
        self.statsThread.started.connect(self.statsWorker.run)
        # connect the worker to get data while active:
        self.statsWorker.taskReturn.connect(self.updateStatsData)
        # connect the worker to apply updates when finished:
        self.statsWorker.taskFinished.connect(self.stopBusyBar)
        # self.statsWorker.taskFinished.connect(lambda: print(self.tokens))
        self.statsWorker.taskFinished.connect(lambda: self.tokenizeButton.setEnabled(False))
        self.statsWorker.taskFinished.connect(lambda: self.tokenDistributionButton.setEnabled(True))
        self.statsWorker.taskFinished.connect(lambda: self.tokenBigramsButton.setEnabled(True))
        self.statsWorker.taskFinished.connect(lambda: self.tokenCountLabel.setText(f'Tokens:\n'
                                                                                   f'Number of tokens: {self.tokenCount}\n'
                                                                                   f'Approximate module steps: {self.tokenCount/255}'))
        # clean up thread when finished:
        self.statsWorker.taskFinished.connect(self.statsThread.quit)
        self.statsWorker.taskFinished.connect(self.statsWorker.deleteLater)
        self.statsThread.finished.connect(self.statsThread.deleteLater)
        # start the busy indicator and run worker:
        self.startBusyBar()
        self.statsThread.start()

    def calculateTokenDistributionWithBar(self):
        """Calculates token distribution in a separate thread to allow progress bar use"""
        self.statsThread = QThread()
        self.statsWorker = StatsWorker('calculateTokenDistribution')
        self.statsWorker.moveToThread(self.statsThread)
        self.statsThread.started.connect(self.statsWorker.run)
        # connect the worker to get data while active:
        self.statsWorker.taskReturn.connect(self.updateStatsData)
        self.statsWorker.taskProgressBarMax.connect(self.setBarMax)
        self.statsWorker.taskProgress.connect(self.setBarValue)
        # connect the worker to apply updates when finished:
        self.statsWorker.taskFinished.connect(self.resetBar)
        # self.statsWorker.taskFinished.connect(lambda: print(self.tokenDistribution))
        self.statsWorker.taskFinished.connect(self.showTopTokens)
        # clean up thread when finished:
        self.statsWorker.taskFinished.connect(self.statsThread.quit)
        self.statsWorker.taskFinished.connect(self.statsWorker.deleteLater)
        self.statsThread.finished.connect(self.statsThread.deleteLater)
        # start the worker:
        self.statsThread.start()

    def showTopTokens(self):
        showTokenDistString = ''
        topTokenAmount = 10
        if findMainWindow().settings:
            topTokenAmount = findMainWindow().settings['InitialPrep']['topTokenAmount']
        for tokenFrequency in self.tokenDistribution[:topTokenAmount]:
            curToken = encoder.decode(tokenFrequency[0])
            showTokenDistString += f'"{curToken}" {tokenFrequency[1]}\n'

        # put it all together and display:
        self.tokenCountLabel.setText(f'Tokens:\n'
                                     f'Number of tokens: {self.tokenCount}\n'
                                     f'Number of unique tokens: {self.uniqueTokenCount}\n'
                                     f'Approximate module steps: {self.tokenCount/255}')

        self.tokenDistLabel.setText(f'Most frequent tokens:\n{showTokenDistString}')

        # disable button to avoid crashes:
        # self.tokenDistributionButton.setEnabled(False)

    def getTokenBigramsWithBar(self):
        """Calculates token bigram counts in a separate thread to allow progress bar use"""
        self.statsThread = QThread()
        self.statsWorker = StatsWorker('getTokenBigrams')
        self.statsWorker.moveToThread(self.statsThread)
        self.statsThread.started.connect(self.statsWorker.run)
        # connect the worker to get data while active:
        self.statsWorker.taskReturn.connect(self.updateStatsData)
        self.statsWorker.taskProgressBarMax.connect(self.setBarMax)
        self.statsWorker.taskProgress.connect(self.setBarValue)
        # connect the worker to apply updates when finished:
        self.statsWorker.taskFinished.connect(self.resetBar)
        # self.statsWorker.taskFinished.connect(lambda: print(self.tokenBigramCounts))
        self.statsWorker.taskFinished.connect(lambda: self.showTopTokenBigrams())
        # clean up thread when finished:
        self.statsWorker.taskFinished.connect(self.statsThread.quit)
        self.statsWorker.taskFinished.connect(self.statsWorker.deleteLater)
        self.statsThread.finished.connect(self.statsThread.deleteLater)
        # start the worker:
        self.statsThread.start()

    def showTopTokenBigrams(self):
        topTokenBigramAmount = 10
        topTokenBigrams = []
        topTokenBigramCounts = []
        for firstToken in self.tokenBigramCounts.keys():
            for secondToken in self.tokenBigramCounts[firstToken].keys():
                if 1 <= len(topTokenBigramCounts) < topTokenBigramAmount:
                    if self.tokenBigramCounts[firstToken][secondToken] > topTokenBigramCounts[-1]:
                        topTokenBigrams.append([firstToken, secondToken, self.tokenBigramCounts[firstToken][secondToken]])
                        topTokenBigramCounts.append(self.tokenBigramCounts[firstToken][secondToken])
                        topTokenBigramCounts.sort(reverse=True)
                elif len(topTokenBigramCounts) < topTokenBigramAmount:
                    topTokenBigramCounts.append(self.tokenBigramCounts[firstToken][secondToken])
                    topTokenBigrams.append([firstToken, secondToken, self.tokenBigramCounts[firstToken][secondToken]])
        topTokenBigrams = sorted(topTokenBigrams, key=lambda x: x[2], reverse=True)

        showTokenBigramsString = ''
        for tokenBigramFrequency in topTokenBigrams:
            curTokenBigram = encoder.decode(tokenBigramFrequency[:2])
            showTokenBigramsString += f'"{curTokenBigram}" {tokenBigramFrequency[2]}\n'

        # put it all together and display:
        self.tokenBigramsLabel.setText(f'Most frequent token bigrams:\n{showTokenBigramsString}')

    def exportStatsAndTknDist(self):
        # exports data statistics
        statsData = {
            'counts': {
                'characters': self.charCount,
                'words': self.wordCount,
                'lines': self.lineCount,
                'sentences': len(self.sentences),
                'verbs': self.verbCount,
                'tokens': self.tokenCount,
                'uniqueTokens': self.uniqueTokenCount,
            }
        }
        if self.tokenDistribution:
            statsData['tokenDistribution'] = self.tokenDistribution
        if self.wordDistribution:
            statsData['wordDistribution'] = self.wordDistribution
        if self.lineLengths:
            statsData['lineLengths'] = self.lineLengths
        if self.tokenBigramCounts:
            statsData['tokenBigramCounts'] = self.tokenBigramCounts
        with open(f'{findMainWindow().curFilePath.replace(".txt", "")}_stats.json',
                  'w', encoding='utf-8') as statsOutFile:
            json.dump(statsData, statsOutFile, ensure_ascii=False)


class StatsWorker(QObject):
    taskFinished = QtCore.pyqtSignal()
    taskReturn = QtCore.pyqtSignal(tuple)
    taskProgress = QtCore.pyqtSignal(int)
    taskProgressBarMax = QtCore.pyqtSignal(int)

    def __init__(self, task):
        super(StatsWorker, self).__init__()
        self.curTask = task

    def run(self):
        if self.curTask == 'getWordDistribution':
            self.getWordDistribution()
        elif self.curTask == 'getDataStats':
            self.getDataStats()
        elif self.curTask == 'getLineLengths':
            self.getLineLengths()
        elif self.curTask == 'getPOS':
            self.getPOS()
        elif self.curTask == 'tokenizeData':
            self.tokenizeData()
        elif self.curTask == 'calculateTokenDistribution':
            self.calculateTokenDistribution()
        elif self.curTask == 'getTokenBigrams':
            self.getTokenBigrams()
        elif self.curTask == 'getQuoteLineCount':
            self.getQuoteLineCount()
        self.taskFinished.emit()

    def returnData(self, dataName):
        self.returnTuple = (dataName, getattr(self, dataName))
        self.taskReturn.emit(self.returnTuple)

    def getDataStats(self):
        # characters:
        self.charCount = len(findMainWindow().curData)
        self.returnData('charCount')
        # words:
        wordTokenizer = nltk.tokenize.RegexpTokenizer(r'\w+')
        self.words = wordTokenizer.tokenize(findMainWindow().curData)
        self.returnData('words')
        self.wordCount = len(self.words)
        self.returnData('wordCount')
        # lines:
        self.lines = findMainWindow().curData.split('\n')
        self.returnData('lines')
        self.lineCount = len(self.lines)
        self.returnData('lineCount')
        # sentences:
        if findMainWindow().settings:
            sentenceEnders = findMainWindow().settings['InitialPrep']['sentenceEnders']
        else:
            sentenceEnders = ['.', '!', '?', ':']
        if findMainWindow().settings:
            self.sentenceEndPlaceholder = findMainWindow().settings['InitialPrep']['sentenceEndPlaceholder']
        else:
            self.sentenceEndPlaceholder = '%%%%%'
        rawSentencesMarked = findMainWindow().curData
        for sentenceEnder in sentenceEnders:
            rawSentencesMarked = rawSentencesMarked.replace(f"{sentenceEnder}", f"{sentenceEnder}{self.sentenceEndPlaceholder}")
        self.sentences = rawSentencesMarked.split(f"{self.sentenceEndPlaceholder}")
        self.returnData('sentences')

    def getWordDistribution(self):
        self.wordCount = findMainWindow().children()[-1].wordCount
        self.taskProgressBarMax.emit(self.wordCount)
        self.uniqueWords = []
        self.wordDistribution = {}
        self.curWordIndex = 0
        for word in findMainWindow().children()[-1].words:
            if word not in self.uniqueWords:
                self.uniqueWords.append(word)
            if word not in self.wordDistribution.keys():
                self.wordDistribution[word] = 1
            elif word in self.wordDistribution.keys():
                self.wordDistribution[word] += 1
            self.curWordIndex += 1
            self.taskProgress.emit(self.curWordIndex)

        self.returnData('uniqueWords')

        self.wordDistribution = sorted(self.wordDistribution.items(), key=lambda x: x[1], reverse=True)
        self.returnData('wordDistribution')

        self.uniqueWordCount = len(self.uniqueWords)
        self.returnData('uniqueWordCount')

    def getLineLengths(self):
        self.lines = findMainWindow().children()[-1].lines
        self.lineCount = findMainWindow().children()[-1].lineCount
        self.taskProgressBarMax.emit(self.lineCount)
        self.curLineID = 0
        self.lineLengths = []
        for line in self.lines:
            self.lineLengths.append(len(line))
            self.taskProgress.emit(self.curLineID)
        self.returnData('lineLengths')

    def getQuoteLineCount(self):
        self.lines = findMainWindow().children()[-1].lines
        self.lineCount = findMainWindow().children()[-1].lineCount
        self.taskProgressBarMax.emit(self.lineCount)
        self.curLineID = 0
        self.quoteLineCount = 0
        for line in self.lines:
            if line[0] in ['"', "'"]:
                self.quoteLineCount += 1
            self.taskProgress.emit(self.curLineID)
        self.returnData('quoteLineCount')

    def getPOS(self):
        self.taggedPOS = nltk.pos_tag(nltk.word_tokenize(findMainWindow().curData))
        self.returnData('taggedPOS')
        self.verbCount = 0
        for word, pos in self.taggedPOS:
            if 'VB' in pos:
                self.verbCount += 1
        self.returnData('verbCount')

    def tokenizeData(self):
        # load tokenizer if it's not loaded yet:
        if not findMainWindow().tokenizerLoaded:
            global encoder
            encoder = GPT2Tokenizer.from_pretrained("gpt2")
            findMainWindow().tokenizerLoaded = True

        self.tokens = encoder.encode(findMainWindow().curData)
        self.returnData('tokens')
        self.tokenCount = len(self.tokens)
        self.returnData('tokenCount')

    def calculateTokenDistribution(self):
        """recursively iterate through data and count token occurrences"""
        self.tokens = findMainWindow().children()[-1].tokens
        self.tokenCount = findMainWindow().children()[-1].tokenCount
        self.taskProgressBarMax.emit(self.tokenCount)
        self.uniqueTokens = []
        self.tokenDistribution = {}
        self.curTokenIndex = 0
        for token in self.tokens:
            if token not in self.uniqueTokens:
                self.uniqueTokens.append(token)
            if token not in self.tokenDistribution.keys():
                self.tokenDistribution[token] = 1
            elif token in self.tokenDistribution.keys():
                self.tokenDistribution[token] += 1
            self.curTokenIndex += 1
            self.taskProgress.emit(self.curTokenIndex)
        self.returnData('uniqueTokens')
        self.uniqueTokenCount = len(self.uniqueTokens)
        self.returnData('uniqueTokenCount')
        self.tokenDistribution = sorted(self.tokenDistribution.items(), key=lambda x: x[1], reverse=True)
        self.returnData('tokenDistribution')

    def getTokenBigrams(self):
        self.tokens = findMainWindow().children()[-1].tokens
        self.tokenCount = findMainWindow().children()[-1].tokenCount
        self.taskProgressBarMax.emit(self.tokenCount)
        self.curTokenIndex = 0
        self.tokenBigramCounts = {}
        for tokenIndex in range(self.tokenCount - 1):
            if self.tokens[tokenIndex] not in self.tokenBigramCounts.keys():
                self.tokenBigramCounts[self.tokens[tokenIndex]] = {}
            if self.tokens[tokenIndex + 1] not in self.tokenBigramCounts[self.tokens[tokenIndex]].keys():
                self.tokenBigramCounts[self.tokens[tokenIndex]][self.tokens[tokenIndex + 1]] = 1
            else:
                self.tokenBigramCounts[self.tokens[tokenIndex]][self.tokens[tokenIndex + 1]] += 1
            self.curTokenIndex += 1
            self.taskProgress.emit(self.curTokenIndex)
        self.returnData('tokenBigramCounts')


class ChunkStack(QWidget):
    """
    A list of consecutive chunks in the form of ChunkTextEdits

    TODO:
        - make navigation more convenient
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
        # self.startIndex = startIndex
        self.startIndex = 0
        if not findMainWindow().persistentChunkStackStartIndex == 0:
            self.startIndex = findMainWindow().persistentChunkStackStartIndex

        # self.maxDisplayedChunks =

        if findMainWindow().settings:
            self.maxDisplayedChunks = findMainWindow().settings['ChunkStack']['maxDisplayedChunks']
        else:
            self.maxDisplayedChunks = 12

        # self.chunkAmount = chunkAmount

        if len(findMainWindow().curData['chunks']) < self.maxDisplayedChunks:
            self.chunkAmount = len(findMainWindow().curData['chunks'])
        else:
            self.chunkAmount = self.maxDisplayedChunks

        # change view position:
        curNavBar = ChunkStackNavigation(startIndex=self.startIndex, chunkAmount=self.chunkAmount)
        self.navBar = curNavBar

        # load tokenizer if it's not loaded yet:
        if not findMainWindow().tokenizerLoaded:
            global encoder
            encoder = GPT2Tokenizer.from_pretrained("gpt2")
            findMainWindow().tokenizerLoaded = True

        self.layout.addWidget(self.navBar)
        # initial stack filling:
        self.fillStack()

    def fillStack(self):
        """update the displayed chunk stack"""
        # if not len(findMainWindow().curData['chunks']) == self.chunkAmount and self.chunkAmount < findMainWindow().settings['ChunkStack']['chunkAmount']:
        if len(findMainWindow().curData['chunks']) < self.maxDisplayedChunks:
            self.chunkAmount = len(findMainWindow().curData['chunks'])
        else:
            self.chunkAmount = self.maxDisplayedChunks
        # print('Trying to clear ChunkStack..')
        self.clearStack()
        # print('Filling ChunkStack...')
        for chunkTextIndex in range(self.startIndex, self.startIndex + self.chunkAmount):
            self.layout.addWidget(ChunkTextEdit(chunkID=chunkTextIndex, chunkContent=findMainWindow().curData['chunks'][chunkTextIndex]))

        self.navBar.updateChunkAmount()

    def clearStack(self):
        """clears the chunk stack"""
        # print('Clearing ChunkStack...')
        for actionIndex in reversed(range(1, self.layout.count())):
            self.layout.itemAt(actionIndex).widget().setParent(None)


class ChunkStackNavigation(QWidget):
    """ navigation bar for the ChunkStack """
    def __init__(self, startIndex, chunkAmount):
        super(ChunkStackNavigation, self).__init__()

        self.layout = QGridLayout()
        self.layout.setAlignment(Qt.AlignLeft)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        if findMainWindow().settings:
            self.maxDisplayedChunks = findMainWindow().settings['ChunkStack']['maxDisplayedChunks']
        else:
            self.maxDisplayedChunks = 12

        # initial view position:
        self.startIndex = startIndex
        self.chunkAmount = chunkAmount

        if len(findMainWindow().curData['chunks']) < self.maxDisplayedChunks:
            self.chunkAmount = len(findMainWindow().curData['chunks'])
        else:
            self.chunkAmount = self.maxDisplayedChunks

        # if not len(findMainWindow().curData['chunks']) == self.chunkAmount and self.chunkAmount < findMainWindow().settings['ChunkStack']['chunkAmount']:
            # self.chunkAmount = len(findMainWindow().curData['chunks'])

        # info label:
        self.navLabel = QLabel('View beginning at chunk index:')
        # change view position:
        self.startIndexSpinBox = QSpinBox()
        self.startIndexSpinBox.setMinimum(0)
        self.startIndexSpinBox.setMaximum(len(findMainWindow().curData['chunks']) - self.chunkAmount)
        if not findMainWindow().persistentChunkStackStartIndex == 0:
            self.startIndexSpinBox.setValue(findMainWindow().persistentChunkStackStartIndex)
        self.startIndexSpinBox.valueChanged.connect(self.startIndexChange)

        # current viewed token total:
        self.currentTokensInView = 0
        self.tokensInViewLabel = QLabel(f'Tokens in current view: {str(self.currentTokensInView)}')

        # count tokens on demand:
        self.countButton = QPushButton('Count')
        self.countButton.clicked.connect(self.updateTokensInView)

        # navigation keyboard shortcuts:
        self.chunkViewIndexAddShortcut = QShortcut(QKeySequence('Ctrl+Down'), self)
        self.chunkViewIndexAddShortcut.activated.connect(self.chunkViewIndexAdd)
        self.chunkViewIndexSubShortcut = QShortcut(QKeySequence('Ctrl+Up'), self)
        self.chunkViewIndexSubShortcut.activated.connect(self.chunkViewIndexSub)

        self.layout.addWidget(self.navLabel, 0, 0)
        self.layout.addWidget(self.startIndexSpinBox, 0, 1)
        self.layout.addWidget(self.tokensInViewLabel, 0, 2)
        self.layout.addWidget(self.countButton, 0, 3)

    def startIndexChange(self):
        """track changes in view position"""
        # make sure indexing can't be messed up:
        # if len(findMainWindow().curData['chunks']) < self.chunkAmount:
        # if not len(findMainWindow().curData['chunks']) == self.chunkAmount and self.chunkAmount < findMainWindow().settings['ChunkStack']['chunkAmount']:
            # self.chunkAmount = len(findMainWindow().curData['chunks'])

        if len(findMainWindow().curData['chunks']) < self.maxDisplayedChunks:
            self.chunkAmount = len(findMainWindow().curData['chunks'])
        else:
            self.chunkAmount = self.maxDisplayedChunks

        self.startIndexSpinBox.setMaximum(len(findMainWindow().curData['chunks']) - self.chunkAmount)
        # apply the spinbox value:
        self.startIndex = self.startIndexSpinBox.value()
        self.parentWidget().startIndex = self.startIndex
        # update the stack:
        self.parentWidget().fillStack()
        # make view position persistent for session:
        findMainWindow().persistentChunkStackStartIndex = self.startIndex
        self.updateTokensInView()

    def updateChunkAmount(self):
        if len(findMainWindow().curData['chunks']) < self.maxDisplayedChunks:
            self.chunkAmount = len(findMainWindow().curData['chunks'])
        else:
            self.chunkAmount = self.maxDisplayedChunks

        self.startIndexSpinBox.setMaximum(len(findMainWindow().curData['chunks']) - self.chunkAmount)

    def chunkViewIndexAdd(self):
        """navigation shortcut method adding to startIndex"""
        if self.startIndexSpinBox.value() + 1 <= len(findMainWindow().curData['chunks']) - self.chunkAmount:
            self.startIndexSpinBox.setValue(self.startIndexSpinBox.value()+1)

    def chunkViewIndexSub(self):
        """navigation shortcut method subtracting from startIndex"""
        if self.startIndexSpinBox.value() - 1 >= 0:
            self.startIndexSpinBox.setValue(self.startIndexSpinBox.value()-1)

    def updateTokensInView(self):
        """recalculate total tokens in view and update display"""
        self.currentTokensInView = 0
        for chunkEdit in range(1, self.parentWidget().layout.count()):
            self.currentTokensInView += self.parentWidget().layout.itemAt(chunkEdit).widget().tokenCount
        self.tokensInViewLabel.setText(f'Tokens in current view: {str(self.currentTokensInView)}')


class ChunkTextEdit(QWidget):
    """
    Interactive widget holding a single chunk/action

    TODO:
        - token threshold warnings
            - ...define token thresholds and store them
        - make more compact version
    """
    def __init__(self, chunkID=0, chunkContent={'text': 'Chunk content text...', 'type': 'generic'}):
        super(ChunkTextEdit, self).__init__()

        self.layout = QGridLayout()
        self.layout.setContentsMargins(1, 1, 1, 1)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)

        # chunk content text editor:
        self.textField = QTextEdit()
        self.textField.setAcceptRichText(False)
        self.textField.setText(chunkContent['text'])
        self.textField.textChanged.connect(self.textChange)
        self.layout.addWidget(self.textField, 0, 0, 4, 1)

        # chunk index:
        self.chunkID = chunkID
        self.IDlabel = QLabel('ID: ' + str(chunkID))
        self.layout.addWidget(self.IDlabel, 0, 1, alignment=Qt.AlignTop)

        # token counter:
        self.tokens = encoder.encode(self.textField.toPlainText())
        self.tokenCount = len(self.tokens)
        self.tokensLabel = QLabel('Tokens: ' + str(self.tokenCount))
        self.layout.addWidget(self.tokensLabel, 1, 1, alignment=Qt.AlignTop)

        """
        # chunk type tag:
        self.typeField = QLineEdit(chunkContent['type'])
        self.typeField.setMaxLength(12)
        self.typeField.setMaximumWidth(80)
        self.typeField.setEnabled(False)
        self.typeField.editingFinished.connect(self.updateType)
        self.layout.addWidget(self.typeField, 2, 1, alignment=Qt.AlignTop)
        """
        # chunk type tag:
        self.typeField = QComboBox()
        self.typeField.setMaximumWidth(80)
        # get chunk types:
        if 'tagTypeData' in findMainWindow().curData['projectData'].keys():
            self.tagTypeData = findMainWindow().curData['projectData']['tagTypeData']
            # add chunk types to dropdown:
            for tagType in self.tagTypeData.keys():
                self.typeField.addItem(tagType)
            # set current chunk type:
            self.typeField.setCurrentText(chunkContent['type'])
        else:
            # if no overall chunk type data is defined, use type tag:
            self.typeField.addItem(chunkContent['type'])

        self.typeField.currentTextChanged.connect(self.updateType)

        self.layout.addWidget(self.typeField, 2, 1, alignment=Qt.AlignTop)

        # 'More' button:
        self.advancedMenu = QToolButton()
        self.advancedMenu.setText('More')
        self.advancedMenu.setPopupMode(QToolButton.InstantPopup)
        self.advancedMenu.setMenu(QMenu(self.advancedMenu))
        self.layout.addWidget(self.advancedMenu, 3, 1, alignment=Qt.AlignTop)

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
        """
        # edit action type tag:
        # TODO: change this to dropdown?
        self.editTypeAction = QWidgetAction(self.advancedMenu)
        self.editTypeAction.setText('Edit chunk type.')
        self.editTypeAction.triggered.connect(self.editActionType)
        self.advancedMenu.menu().addAction(self.editTypeAction)
        """
        # delete chunk:
        deleteChunkAction = QWidgetAction(self.advancedMenu)
        deleteChunkAction.setText('Delete chunk.')
        deleteChunkAction.triggered.connect(self.deleteChunk)
        self.advancedMenu.menu().addAction(deleteChunkAction)

        self.infoLabel = QLabel('ID: ' + str(chunkID) + ' Tokens: ' + str(self.tokenCount))

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
        findMainWindow().curData['chunks'][self.chunkID]['text'] = self.textField.toPlainText()
        findMainWindow().toggleFileUnsaved()

    def spliceAbove(self):
        """add a chunk above this chunk"""
        insertChunk = {'text': 'PLACEHOLDER', 'type': 'generic'}
        if findMainWindow().settings:
            insertChunkText = findMainWindow().settings['ChunkStack']['insertChunkText']
            insertChunkType = findMainWindow().settings['ChunkStack']['insertChunkType']
            insertChunk = {'text': insertChunkText, 'type': insertChunkType}
        findMainWindow().curData['chunks'].insert(self.chunkID, insertChunk)
        self.parentWidget().fillStack()
        findMainWindow().toggleFileUnsaved()

    def spliceBelow(self):
        """add a chunk above this chunk"""
        insertChunk = {'text': 'PLACEHOLDER', 'type': 'generic'}
        if findMainWindow().settings:
            insertChunkText = findMainWindow().settings['ChunkStack']['insertChunkText']
            insertChunkType = findMainWindow().settings['ChunkStack']['insertChunkType']
            insertChunk = {'text': insertChunkText, 'type': insertChunkType}
        findMainWindow().curData['chunks'].insert(self.chunkID+1, insertChunk)
        self.parentWidget().fillStack()
        findMainWindow().toggleFileUnsaved()

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
        # findMainWindow().curData['chunks'][self.chunkID]['type'] = self.typeField.text()
        findMainWindow().curData['chunks'][self.chunkID]['type'] = self.typeField.currentText()
        print(f"updated chunk {self.chunkID} type: {findMainWindow().curData['chunks'][self.chunkID]['type']}")
        findMainWindow().toggleFileUnsaved()

    def deleteChunk(self):
        """delete this chunk"""
        findMainWindow().curData['chunks'].pop(self.chunkID)
        findMainWindow().toggleFileUnsaved()
        # make sure GUI doesn't break due to bad indexing:
        newEndIndex = self.parentWidget().startIndex + self.parentWidget().chunkAmount
        if newEndIndex > len(findMainWindow().curData['chunks']):
            self.parentWidget().startIndex = self.parentWidget().startIndex-1
            self.parentWidget().navBar.startIndex = self.parentWidget().navBar.startIndex-1
        # update the stack:
        self.parentWidget().fillStack()


class ChunkCombiner(QWidget):
    """
    Combine chunkfile content and insert newlines, pre- and suffixes depending on chunk type

    TODO:
        - export file dialog?
    """
    def __init__(self):
        super(ChunkCombiner, self).__init__()

        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.setLayout(self.layout)

        # persistent chunk type handling settings:
        self.tagTypeData = {}
        if 'tagTypeData' in findMainWindow().curData['projectData'].keys():
            self.tagTypeData = findMainWindow().curData['projectData']['tagTypeData']
        print(f'tagTypeData: {self.tagTypeData}')

        self.initTopHeader()

        self.layout.addWidget(QHLine())

        # chunk type stack header:
        self.tagTypeStackHeaderLabel = QLabel('<b>Chunk types:</b>')
        self.layout.addWidget(self.tagTypeStackHeaderLabel)

        # chunk type settings:
        self.chunkTypeStack = TagTypeStack()
        self.layout.addWidget(self.chunkTypeStack)

        self.initTypesUtility()

        self.layout.addWidget(QHLine())

        self.initExport()

    def initTopHeader(self):
        self.topHeaderLayout = QHBoxLayout()

        self.headerFileLabel = QLabel('<b>Current chunkfile:</b>')
        self.topHeaderLayout.addWidget(self.headerFileLabel)

        self.chunkAmount = len(findMainWindow().curData['chunks'])
        self.chunkAmountLabel = QLabel(f'Number of Chunks: {self.chunkAmount}')
        self.topHeaderLayout.addWidget(self.chunkAmountLabel)

        # check working data for chunk type (tags):
        chunkTagsList = [chunk['type'] for chunk in findMainWindow().curData['chunks']]
        self.tagTypes = list(set(chunkTagsList))
        self.tagCounts = [chunkTagsList.count(tagType) for tagType in self.tagTypes]
        tagTypeCounts = [f'{self.tagTypes[index]} ({self.tagCounts[index]})' for index in range(len(self.tagTypes))]
        self.tagTypesLabel = QLabel(f'Chunk types used (amount): {", ".join(tagTypeCounts)}')
        self.topHeaderLayout.addWidget(self.tagTypesLabel)

        self.layout.addLayout(self.topHeaderLayout)

    def initTypesUtility(self):
        self.typesUtilityLayout = QVBoxLayout()

        self.typesUtilityHeaderLayout = QHBoxLayout()

        self.typesUtilityHeaderLabel = QLabel('<b>Type handling:</b>')
        self.typesUtilityHeaderLayout.addWidget(self.typesUtilityHeaderLabel)

        self.typesUtilityLayout.addLayout(self.typesUtilityHeaderLayout)

        self.typesUtilityNewTypeLayout = QHBoxLayout()

        # new chunk type name label:
        self.addTypeNameLabel = QLabel('New type name:')
        self.typesUtilityNewTypeLayout.addWidget(self.addTypeNameLabel)

        # new chunk type name:
        self.addTypeNameEdit = QLineEdit('newType')
        self.addTypeNameEdit.setMaxLength(12)
        self.typesUtilityNewTypeLayout.addWidget(self.addTypeNameEdit)

        # add chunk type:
        self.addTypeButton = QPushButton('Add new type')
        self.addTypeButton.clicked.connect(self.addChunkType)
        self.typesUtilityNewTypeLayout.addWidget(self.addTypeButton)

        self.typesUtilityLayout.addLayout(self.typesUtilityNewTypeLayout)

        # saving chunk type handling to project file:
        self.saveTagTypeDataButton = QPushButton('Save type handling data')
        self.saveTagTypeDataButton.clicked.connect(self.saveTagTypeData)
        self.typesUtilityLayout.addWidget(self.saveTagTypeDataButton)

        self.layout.addLayout(self.typesUtilityLayout)

    def initExport(self):
        self.exportLayout = QVBoxLayout()

        self.exportHeaderLayout = QHBoxLayout()

        self.exportHeaderLabel = QLabel('<b>Combine & export:')
        self.exportHeaderLayout.addWidget(self.exportHeaderLabel)

        self.exportLayout.addLayout(self.exportHeaderLayout)

        self.exportUtilityLayout = QHBoxLayout()

        # combined file settings:
        self.fileSuffixLabel = QLabel('Combined file suffix:')
        self.exportUtilityLayout.addWidget(self.fileSuffixLabel)
        if findMainWindow().settings:
            self.fileSuffixString = findMainWindow().settings['ChunkCombiner']['chunkFileSuffix']
        else:
            self.fileSuffixString = '_combined'
        self.fileSuffix = QLineEdit(self.fileSuffixString)
        self.exportUtilityLayout.addWidget(self.fileSuffix)

        # add type-based strings, combine chunks and export as plaintext:
        self.combineExportButton = QPushButton('Export combined chunks')
        self.combineExportButton.clicked.connect(self.combineExport)
        self.exportUtilityLayout.addWidget(self.combineExportButton)

        self.exportLayout.addLayout(self.exportUtilityLayout)

        self.layout.addLayout(self.exportLayout)

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
        self.chunkTypeStack.updateTypes()

    def addChunkType(self):
        print('adding new chunk type')
        self.tagTypeData[self.addTypeNameEdit.text()] = [False, False, '', '']
        print(self.tagTypeData)
        findMainWindow().curData['projectData']['tagTypeData'] = self.tagTypeData
        self.chunkTypeStack.updateTypes()

    def saveTagTypeData(self):
        print('saving tag type data')
        self.getTagTypeStackItems()
        findMainWindow().curData['projectData']['tagTypeData'] = self.tagTypeData
        self.updateChunkTypeStack()
        with open(f'{findMainWindow().curFilePath}', 'w', encoding='utf-8') as chunksOutFile:
            fullDataJSON = json.dumps(findMainWindow().curData)
            chunksOutFile.write(fullDataJSON)

    def combineExport(self):
        self.getTagTypeStackItems()
        chunkTextsList = []
        for chunkIndex in range(len(findMainWindow().curData['chunks'])):
            chunkText = findMainWindow().curData['chunks'][chunkIndex]['text']
            # add prefix:
            chunkText = self.tagTypeData[findMainWindow().curData['chunks'][chunkIndex]['type']][2] + chunkText
            # add suffix:
            chunkText += self.tagTypeData[findMainWindow().curData['chunks'][chunkIndex]['type']][3]
            # check for newline adding to start of chunk text:
            if self.tagTypeData[findMainWindow().curData['chunks'][chunkIndex]['type']][0]:
                chunkText = '\n' + chunkText
            # check for newline adding to end of chunk text:
            if self.tagTypeData[findMainWindow().curData['chunks'][chunkIndex]['type']][1]:
                chunkText += '\n'
            # add updated chunk text to list:
            chunkTextsList.append(chunkText)
        # join the chunk text list:
        combinedString = ''.join(chunkTextsList)
        # print(combinedString)
        # save the whole thing:
        with open(f'{findMainWindow().curFilePath.replace(".json", "")}{self.fileSuffix.text()}.txt', 'w', encoding='utf-8') as combinedChunksFile:
            combinedChunksFile.write(combinedString)


class TagTypeStack(QWidget):
    """
    widget to hold list of chunk types and keep everything interactive
    """
    def __init__(self):
        super(TagTypeStack, self).__init__()

        self.layout = QVBoxLayout()
        # self.layout.setAlignment(Qt.AlignTop)
        # self.layout.setAlignment(Qt.AlignLeft)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)

        self.tagTypes = {}
        if 'tagTypeData' in findMainWindow().curData['projectData'].keys():
            self.tagTypes = findMainWindow().curData['projectData']['tagTypeData']

        for tagType in self.tagTypes:
            curTagTypeHolder = TagTypeHolder(tagType)
            self.layout.addWidget(curTagTypeHolder)

    def updateTypes(self):
        print('updating types')
        print(self.tagTypes)
        # clear layout:  ugly, but works...
        curId = self.layout.count()-1
        while curId >= 0:
            print(self.layout.itemAt(curId).widget())
            self.layout.itemAt(curId).widget().setParent(None)
            self.layout.removeItem(self.layout.itemAt(curId))
            curId -= 1

        print(findMainWindow().curData['projectData']['tagTypeData'])

        if 'tagTypeData' in findMainWindow().curData['projectData'].keys():
            self.tagTypes = findMainWindow().curData['projectData']['tagTypeData']

        print(self.tagTypes)

        # add types:
        for tagType in self.tagTypes:
            curTagTypeHolder = TagTypeHolder(tagType)
            self.layout.addWidget(curTagTypeHolder)


class TagTypeHolder(QWidget):
    """
    holds single chunk type handling
    """
    def __init__(self, tagType):
        super(TagTypeHolder, self).__init__()

        # self.layout = QGridLayout()
        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.setLayout(self.layout)

        self.headerLayout = QHBoxLayout()

        self.tagType = tagType
        self.tagTypeIdLabel = QLabel(f'<b>{tagType}</b>')
        self.headerLayout.addWidget(self.tagTypeIdLabel)

        self.tagTypeSaveWarnLabel = QLabel('')
        self.headerLayout.addWidget(self.tagTypeSaveWarnLabel)

        self.layout.addLayout(self.headerLayout)

        self.checksButtonsLayout = QHBoxLayout()

        self.tagTypeFrontNewlineCheckbox = QCheckBox('Add newline before')
        self.tagTypeFrontNewlineCheckbox.clicked.connect(self.dataChanged)
        self.checksButtonsLayout.addWidget(self.tagTypeFrontNewlineCheckbox)

        self.tagTypeBackNewlineCheckbox = QCheckBox('Add newline after')
        self.tagTypeBackNewlineCheckbox.clicked.connect(self.dataChanged)
        self.checksButtonsLayout.addWidget(self.tagTypeBackNewlineCheckbox)

        self.deleteButton = QPushButton('Delete')
        self.deleteButton.setFixedWidth(60)
        self.deleteButton.clicked.connect(self.deleteType)
        self.checksButtonsLayout.addWidget(self.deleteButton)

        self.layout.addLayout(self.checksButtonsLayout)

        self.prefixLayout = QHBoxLayout()

        self.tagTypePrefixLabel = QLabel('Prefix:')
        self.prefixLayout.addWidget(self.tagTypePrefixLabel)

        self.tagTypePrefix = QLineEdit()
        # self.tagTypePrefix.textChanged.connect(self.dataChanged)
        self.prefixLayout.addWidget(self.tagTypePrefix)

        self.layout.addLayout(self.prefixLayout)

        self.suffixLayout = QHBoxLayout()

        self.tagTypeSuffixLabel = QLabel('Suffix:')
        self.suffixLayout.addWidget(self.tagTypeSuffixLabel)

        self.tagTypeSuffix = QLineEdit()
        # self.tagTypeSuffix.textChanged.connect(self.dataChanged)
        self.suffixLayout.addWidget(self.tagTypeSuffix)

        self.layout.addLayout(self.suffixLayout)

        if tagType in findMainWindow().curData['projectData']['tagTypeData'].keys():
            self.tagTypeSaveWarnLabel.setText('')
            if findMainWindow().curData['projectData']['tagTypeData'][tagType][0]:
                self.tagTypeFrontNewlineCheckbox.setChecked(True)
            if findMainWindow().curData['projectData']['tagTypeData'][tagType][1]:
                self.tagTypeBackNewlineCheckbox.setChecked(True)
            if findMainWindow().curData['projectData']['tagTypeData'][tagType][2]:
                self.tagTypePrefix.setText(findMainWindow().curData['projectData']['tagTypeData'][tagType][2])
            if findMainWindow().curData['projectData']['tagTypeData'][tagType][3]:
                self.tagTypeSuffix.setText(findMainWindow().curData['projectData']['tagTypeData'][tagType][3])
        else:
            self.tagTypeSaveWarnLabel.setText('<b>(not defined)</b>')

        self.tagTypePrefix.textChanged.connect(self.dataChanged)
        self.tagTypeSuffix.textChanged.connect(self.dataChanged)

    def getContent(self):
        outTagType = self.tagType
        preNewlineBool = self.tagTypeFrontNewlineCheckbox.isChecked()
        postNewlineBool = self.tagTypeBackNewlineCheckbox.isChecked()
        prefix = self.tagTypePrefix.text()
        suffix = self.tagTypeSuffix.text()
        return outTagType, [preNewlineBool, postNewlineBool, prefix, suffix]

    def dataChanged(self):
        # self.tagTypeSaveWarnLabel.setText('<b>(not saved)</b>')
        findMainWindow().curData['projectData']['tagTypeData'][self.tagType][0] = self.tagTypeFrontNewlineCheckbox.isChecked()
        findMainWindow().curData['projectData']['tagTypeData'][self.tagType][1] = self.tagTypeBackNewlineCheckbox.isChecked()
        findMainWindow().curData['projectData']['tagTypeData'][self.tagType][2] = self.tagTypePrefix.text()
        findMainWindow().curData['projectData']['tagTypeData'][self.tagType][3] = self.tagTypeSuffix.text()
        findMainWindow().toggleFileUnsaved()

    def deleteType(self):
        findMainWindow().curData['projectData']['tagTypeData'].pop(self.tagType)
        print('Chunkcombiner children:')
        print(findMainWindow().children()[1].children())
        print('Typestack?:')
        print(findMainWindow().children()[1].children()[6])
        findMainWindow().children()[1].children()[6].updateTypes()


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
        checkStringEscaped = re.sub(r'(?P<specChar>[\[\].^$*+?{}|])', r'\\\g<specChar>', self.testString.text())
        checkExpression = re.compile(f'.*{checkStringEscaped}.*')

        for key, value in fixEncodes.items():
            matchedExpression = checkExpression.match(key)
            if matchedExpression:
                catchList.append(key)

        self.outputText.setText('\n'.join(catchList))


class QHLine(QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


if __name__ == '__main__':
    app = QApplication([])
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())
