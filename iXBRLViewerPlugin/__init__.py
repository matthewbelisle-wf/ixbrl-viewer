# Copyright 2019 Workiva Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import argparse
import logging
import os
import sys
import tempfile
import traceback

from arelle.LocalViewer import LocalViewer
from arelle.ModelDocument import Type
from arelle.webserver.bottle import static_file

from iXBRLViewerPlugin.constants import DEFAULT_VIEWER_PATH
from .iXBRLViewer import IXBRLViewerBuilder, IXBRLViewerBuilderError


#
# GUI operation:
#
#     if submenu View->iXBRL Viewer->Launch viewer on load is checkmarked, a local viewer is automatically opened to view
#
#     to save a viewable file Tools->Save iXBRL Viewer Instance (dialog requests linkable js location and save location)
#
# Command line operation:
#
#     parameters --save-viewer (file system location to save at) and --viewer-url (linkable js location)
#
# Web Server operation:
#
#     example uploading an ESEF report package and receiving a zip of viewable .xhtml and viewer javascript file:
#
#         curl -X POST "-HContent-type: application/zip"
#              -T /Users/mystuff/ESMA/samples/bzwbk_2016.zip
#              -o ~/temp/out.zip
#              "http://localhost:8080/rest/xbrl/validation?&media=zip&plugins=iXBRLViewerPlugin&packages=somewhere/esef_taxonomy_2017.zip"
#
#     In the zip, the iXBRLViewer files are in a subdirectory VIEWER_BASENAME_SUFFIX to separate them from possible EdgarRenderer and other output files
#


def iXBRLViewerCommandLineOptionExtender(parser, *args, **kwargs):
    parser.add_option("--save-viewer",
                      action="store",
                      dest="saveViewerFile",
                      help="Save an HTML viewer file for an iXBRL report. Specify either a filename or directory.")
    parser.add_option("--viewer-url",
                      action="store",
                      dest="viewerURL",
                      default=DEFAULT_VIEWER_PATH,
                      help="Specify the URL to ixbrlviewer.js")
    parser.add_option("--viewer-validation-messages",
                      dest="validationMessages",
                      action="store_true",
                      help="Include validation messages in the viewer")
    # Force logging to use a buffer so that messages are retained and can be
    # retrieved for inclusion with the viewer.
    parser.add_option("--logToBuffer", action="store_true", dest="logToBuffer", default=True, help=argparse.SUPPRESS)
    parser.add_option("--use-stub-viewer",
                      action="store_true",
                      dest="useStubViewer",
                      help="Use stub viewer for faster loading of inspector (requires web server)")
    parser.add_option("--viewer-suffix",
                      action="store",
                      default="",
                      dest="viewerBasenameSuffix",
                      help="Suffix for basename of viewer files")
    parser.add_option("--zip-viewer-output",
                      action="store_true",
                      default=False,
                      dest="zipViewerOutput",
                      help="Converts the viewer output into a self contained zip")


def generateViewer(cntlr, saveViewerFile, viewerURL=DEFAULT_VIEWER_PATH, showValidationMessages=False, useStubViewer=False, zipViewerOutput=False):
    # extend XBRL-loaded run processing for this option
    if cntlr.modelManager is None or cntlr.modelManager.modelXbrl is None or not cntlr.modelManager.modelXbrl.modelDocument:
        cntlr.addToLog("No taxonomy loaded.")
        return
    modelXbrl = cntlr.modelManager.modelXbrl
    if modelXbrl.modelDocument.type not in (Type.INLINEXBRL, Type.INLINEXBRLDOCUMENTSET):
        cntlr.addToLog("No inline XBRL document loaded.")
        return
    try:
        out = saveViewerFile
        if out:
            viewerBuilder = IXBRLViewerBuilder(modelXbrl)
            iv = viewerBuilder.createViewer(scriptUrl=viewerURL, showValidations=showValidationMessages, useStubViewer=useStubViewer)
            if iv is not None:
                iv.save(out, zipOutput=zipViewerOutput)
    except IXBRLViewerBuilderError as ex:
        print(ex.message)
    except Exception as ex:
        cntlr.addToLog("Exception {} \nTraceback {}".format(ex, traceback.format_tb(sys.exc_info()[2])))


def iXBRLViewerCommandLineXbrlRun(cntlr, options, *args, **kwargs):
    generateViewer(
        cntlr,
        options.saveViewerFile or kwargs.get("responseZipStream"),
        options.viewerURL,
        options.validationMessages,
        options.useStubViewer,
        options.zipViewerOutput
    )


def iXBRLViewerMenuCommand(cntlr):
    from .ui import SaveViewerDialog
    if cntlr.modelManager is None or cntlr.modelManager.modelXbrl is None:
        cntlr.addToLog("No document loaded.")
        return
    modelXbrl = cntlr.modelManager.modelXbrl
    if modelXbrl.modelDocument.type not in (Type.INLINEXBRL, Type.INLINEXBRLDOCUMENTSET):
        cntlr.addToLog("No inline XBRL document loaded.")
        return
    dialog = SaveViewerDialog(cntlr)
    if dialog.accepted and dialog.filename():
        viewerBuilder = IXBRLViewerBuilder(modelXbrl)
        iv = viewerBuilder.createViewer(scriptUrl=dialog.scriptUrl(), showValidations=False)
        if iv is not None:
            iv.save(dialog.filename(), zipOutput=dialog.zipViewerOutput())


def iXBRLViewerToolsMenuExtender(cntlr, menu, *args, **kwargs):
    # Extend menu with an item for the savedts plugin
    menu.add_command(label="Save iXBRL Viewer Instance",
                     underline=0,
                     command=lambda: iXBRLViewerMenuCommand(cntlr))


def toolsMenuExtender(cntlr, menu, *args, **kwargs):
    iXBRLViewerToolsMenuExtender(cntlr, menu, *args, **kwargs)


def commandLineOptionExtender(*args, **kwargs):
    iXBRLViewerCommandLineOptionExtender(*args, **kwargs)


def commandLineRun(*args, **kwargs):
    iXBRLViewerCommandLineXbrlRun(*args, **kwargs)


def viewMenuExtender(cntlr, viewMenu, *args, **kwargs):
    # persist menu selections for showing filing data and tables menu
    from tkinter import Menu, BooleanVar  # must only import if GUI present (no tkinter on GUI-less servers)
    def setLaunchIXBRLViewer(self, *args):
        cntlr.config["LaunchIXBRLViewer"] = cntlr.launchIXBRLViewer.get()
        cntlr.saveConfig()
    erViewMenu = Menu(cntlr.menubar, tearoff=0)
    viewMenu.add_cascade(label=_("iXBRL Viewer"), menu=erViewMenu, underline=0)
    cntlr.launchIXBRLViewer = BooleanVar(value=cntlr.config.get("LaunchIXBRLViewer", True))
    cntlr.launchIXBRLViewer.trace("w", setLaunchIXBRLViewer)
    erViewMenu.add_checkbutton(label=_("Launch viewer on load"), underline=0, variable=cntlr.launchIXBRLViewer, onvalue=True, offvalue=False)


class iXBRLViewerLocalViewer(LocalViewer):
    # plugin-specific local file handler
    def getLocalFile(self, file, relpath, request):
        _report, _sep, _file = file.partition("/")
        if file == 'ixbrlviewer.js':
            return static_file('ixbrlviewer.js', os.path.dirname(DEFAULT_VIEWER_PATH))
        elif _report.isnumeric():  # in reportsFolder folder
            # check if file is in the current or parent directory
            _fileDir = self.reportsFolders[int(_report)]
            _fileExists = False
            if os.path.exists(os.path.join(_fileDir, _file)):
                _fileExists = True
            elif "/" in _file and os.path.exists(os.path.join(_fileDir, os.path.filepart(_file))):
                # xhtml in a subdirectory for output files may refer to an image file in parent directory
                _fileExists = True
                _file = os.path.filepart(_file)
            if not _fileExists:
                self.cntlr.addToLog("http://localhost:{}/{}".format(self.port, file), messageCode="localViewer:fileNotFound", level=logging.DEBUG)
            return static_file(_file, root=_fileDir, headers=self.noCacheHeaders)  # extra_headers modification to py-bottle
        return static_file(file, root="/")  # probably can't get here unless path is wrong


def guiRun(cntlr, modelXbrl, attach, *args, **kwargs):
    """ run iXBRL Viewer using GUI interactions for a single instance or testcases """
    try:
        import webbrowser
        global tempViewer
        tempViewer = tempfile.TemporaryDirectory()
        viewer_file_name = 'ixbrlviewer.html'
        generateViewer(cntlr, tempViewer.name, useStubViewer = True)
        localViewer = iXBRLViewerLocalViewer("iXBRL Viewer",  os.path.dirname(__file__))
        localhost = localViewer.init(cntlr, tempViewer.name)
        webbrowser.open(f'{localhost}/{viewer_file_name}')
    except Exception as ex:
        modelXbrl.error(
            "viewer:exception",
            "Exception %(exception)s \sTraceback %(traceback)s",
            modelObject=modelXbrl, exception=ex, traceback=traceback.format_tb(sys.exc_info()[2])
        )


def load_plugin_url():
    return __file__


__pluginInfo__ = {
    'name': 'ixbrl-viewer',
    'version': '0.1',
    'description': "iXBRL Viewer creator",
    'license': 'License :: OSI Approved :: Apache License, Version 2.0 (Apache-2.0)',
    'author': 'Paul Warren',
    'copyright': 'Copyright :: Workiva Inc. :: 2019',
    'CntlrCmdLine.Options': commandLineOptionExtender,
    'CntlrCmdLine.Xbrl.Run': commandLineRun,
    'CntlrWinMain.Menu.Tools': toolsMenuExtender,
    'CntlrWinMain.Menu.View': viewMenuExtender,
    'CntlrWinMain.Xbrl.Loaded': guiRun,
}
