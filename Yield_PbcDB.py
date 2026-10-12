from abaqusConstants import *
from abaqusGui import *
from kernelAccess import mdb, session
import os

thisPath = os.path.abspath(__file__)
thisDir = os.path.dirname(thisPath)

class YieldPbcDB(AFXDataDialog):

    def __init__(self, form):
        AFXDataDialog.__init__(self, form, 'Pbc',
                               self.OK | self.CANCEL, DIALOG_ACTIONS_SEPARATOR)

        okBtn = self.getActionButton(self.ID_CLICKED_OK)
        okBtn.setText('OK')

        VAligner_1 = AFXVerticalAligner(p=self, opts=0, x=0, y=0, w=0, h=0,
                                        pl=0, pr=0, pt=0, pb=0)

        fileHandler = PbcDBFileHandler(form, 'path', 'All files (*)')
        fileTextHf = FXHorizontalFrame(p=VAligner_1, opts=0, x=0, y=0, w=0, h=0,
                                       pl=0, pr=0, pt=0, pb=0,
                                       hs=DEFAULT_SPACING, vs=DEFAULT_SPACING)
        fileTextHf.setSelector(99)
        AFXTextField(p=fileTextHf, ncols=40, labelText="Output directory (.inp files):",
                     tgt=form.pathKw, sel=0,
                     opts=AFXTEXTFIELD_STRING | LAYOUT_CENTER_Y)
        icon = afxGetIcon('fileOpen', AFX_ICON_SMALL)
        FXButton(p=fileTextHf, text=' Select Folder ', ic=icon, tgt=fileHandler, sel=AFXMode.ID_ACTIVATE,
                 opts=BUTTON_NORMAL | LAYOUT_CENTER_Y)

        targetFrame = FXHorizontalFrame(p=VAligner_1, opts=0, x=0, y=0, w=0, h=0,
                                        pl=0, pr=0, pt=10, pb=0,
                                        hs=DEFAULT_SPACING, vs=DEFAULT_SPACING)

        epsFrame = FXHorizontalFrame(p=VAligner_1, opts=0, x=0, y=0, w=0, h=0,
                                     pl=0, pr=0, pt=10, pb=0,
                                     hs=DEFAULT_SPACING, vs=DEFAULT_SPACING)

        AFXTextField(p=epsFrame,ncols=12,labelText="Max macro strain amplitude",tgt=form.epsMaxKw,sel=0)
        outFrame = FXHorizontalFrame(p=VAligner_1, opts=0, x=0, y=0, w=0, h=0,
                                     pl=0, pr=0, pt=10, pb=0,
                                     hs=DEFAULT_SPACING, vs=DEFAULT_SPACING)

        AFXTextField(p=outFrame, ncols=8, labelText="Number of output intervals:", tgt=form.numIntervalsKw, sel=0)
        AFXTextField(p=outFrame, ncols=8, labelText="Step time period:",  tgt=form.timePeriodKw, sel=0)
        AFXTextField(p=outFrame, ncols=8, labelText="Max number of increments:",   tgt=form.maxNumIncKw, sel=0)

        incFrame = FXHorizontalFrame(p=VAligner_1, opts=0, x=0, y=0, w=0, h=0,
                                     pl=0, pr=0, pt=10, pb=0,
                                     hs=DEFAULT_SPACING, vs=DEFAULT_SPACING)

        AFXTextField(p=incFrame, ncols=10, labelText="Initial increment:", tgt=form.initialIncKw, sel=0)
        AFXTextField(p=incFrame, ncols=10, labelText="Minimum increment:",     tgt=form.minIncKw, sel=0)
        AFXTextField(p=incFrame, ncols=10, labelText="Maximum increment:",     tgt=form.maxIncKw, sel=0)

        genFrame = FXHorizontalFrame(p=VAligner_1, opts=0, x=0, y=0, w=0, h=0,
                                     pl=0, pr=0, pt=10, pb=0,
                                     hs=DEFAULT_SPACING, vs=DEFAULT_SPACING)

        AFXTextField(p=genFrame, ncols=10, labelText=u"Lode angle range [deg]:",   tgt=form.thetaMaxKw, sel=0)
        AFXTextField(p=genFrame, ncols=10, labelText="Number of Lode angle samples:", tgt=form.thetaCountKw, sel=0)

        genFrame2 = FXHorizontalFrame(p=VAligner_1, opts=0, x=0, y=0, w=0, h=0,
                                      pl=0, pr=0, pt=10, pb=0,
                                      hs=DEFAULT_SPACING, vs=DEFAULT_SPACING)

        AFXTextField(p=genFrame2, ncols=8, labelText="Hydrostatic levels:", tgt=form.nHydroKw, sel=0)
        AFXTextField(p=genFrame2, ncols=8, labelText="Deviatoric levels:",   tgt=form.nDevKw, sel=0)


class PbcDBFileHandler(FXObject):

    def __init__(self, form, keyword, patterns='*'):
        self.form = form
        self.patterns = patterns
        self.patternTgt = AFXIntTarget(0)
        exec('self.fileNameKw = form.%sKw' % keyword)
        self.readOnlyKw = AFXBoolKeyword(None, 'readOnly', AFXBoolKeyword.TRUE_FALSE)
        FXObject.__init__(self)
        FXMAPFUNC(self, SEL_COMMAND, AFXMode.ID_ACTIVATE, PbcDBFileHandler.activate)

    def activate(self, sender, sel, ptr):
        fileDb = AFXFileSelectorDialog(getAFXApp().getAFXMainWindow(), 'Select a Directory',
                                       self.fileNameKw, self.readOnlyKw,
                                       AFXSELECTFILE_DIRECTORY, self.patterns, self.patternTgt)
        fileDb.setReadOnlyPatterns('*.odb')
        fileDb.create()
        fileDb.showModal()