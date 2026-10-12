from abaqusConstants import *
from abaqusGui import *
import os

thisPath = os.path.abspath(__file__)
thisDir = os.path.dirname(thisPath)

class find_resultsDB(AFXDataDialog):

    def __init__(self, form):
        AFXDataDialog.__init__(
            self, form, 'Find Results',
            self.OK | self.CANCEL, DIALOG_ACTIONS_SEPARATOR
        )

        okBtn = self.getActionButton(self.ID_CLICKED_OK)
        okBtn.setText('OK')

        V = AFXVerticalAligner(
            p=self, opts=0, x=0, y=0, w=0, h=0,
            pl=0, pr=0, pt=0, pb=0
        )

        fileHandler = findResultsFileHandler(form, 'path', 'All files (*)')
        hf = FXHorizontalFrame(
            p=V, opts=0, x=0, y=0, w=0, h=0,
            pl=0, pr=0, pt=0, pb=0,
            hs=DEFAULT_SPACING, vs=DEFAULT_SPACING
        )

        AFXTextField(
            p=hf, ncols=40,
            labelText="Choose results directory:",
            tgt=form.pathKw, sel=0,
            opts=AFXTEXTFIELD_STRING | LAYOUT_CENTER_Y
        )

        icon = afxGetIcon('fileOpen', AFX_ICON_SMALL)
        FXButton(
            p=hf, text=' Select Folder ', ic=icon,
            tgt=fileHandler, sel=AFXMode.ID_ACTIVATE,
            opts=BUTTON_NORMAL | LAYOUT_CENTER_Y
        )

class findResultsFileHandler(FXObject):

    def __init__(self, form, keyword, patterns='*'):
        self.form = form
        self.patterns = patterns
        self.patternTgt = AFXIntTarget(0)

        exec('self.fileNameKw = form.%sKw' % keyword)
        self.readOnlyKw = AFXBoolKeyword(
            None, 'readOnly', AFXBoolKeyword.TRUE_FALSE
        )

        FXObject.__init__(self)
        FXMAPFUNC(self, SEL_COMMAND, AFXMode.ID_ACTIVATE, findResultsFileHandler.activate)

    def activate(self, sender, sel, ptr):
        dlg = AFXFileSelectorDialog(
            getAFXApp().getAFXMainWindow(), 'Select Results Directory',
            self.fileNameKw, self.readOnlyKw,
            AFXSELECTFILE_DIRECTORY, self.patterns, self.patternTgt
        )
        dlg.setReadOnlyPatterns('*.odb')
        dlg.create()
        dlg.showModal()
