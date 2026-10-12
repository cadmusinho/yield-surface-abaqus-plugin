from abaqusGui import *
from abaqusConstants import *

class GrapherSingleDB(AFXDataDialog):
    def __init__(self, form):
        AFXDataDialog.__init__(self, form, "Grapher (Single graph)",
                               self.OK | self.CANCEL, DIALOG_ACTIONS_SEPARATOR)

        V = AFXVerticalAligner(p=self, pl=0, pr=0, pt=0, pb=0)

        row = FXHorizontalFrame(p=V, hs=DEFAULT_SPACING, vs=DEFAULT_SPACING, opts=LAYOUT_FILL_X)
        AFXTextField(p=row, ncols=52, labelText="CSV folder:", tgt=form.folderKw, sel=0)
        FXButton(
            p=row, text=" Select Folder ",
            ic=afxGetIcon("fileOpen", AFX_ICON_SMALL),
            tgt=DirSelectHandler(form.folderKw), sel=AFXMode.ID_ACTIVATE
        )

        row2 = FXHorizontalFrame(p=V, hs=DEFAULT_SPACING, vs=DEFAULT_SPACING, opts=LAYOUT_FILL_X)
        AFXTextField(p=row2, ncols=30, labelText="Model name:", tgt=form.modelKw, sel=0)

        row3 = FXHorizontalFrame(p=V, hs=DEFAULT_SPACING, vs=DEFAULT_SPACING, opts=LAYOUT_FILL_X)
        AFXTextField(p=row3, ncols=15, labelText="Target value (PEEQ):", tgt=form.targetKw, sel=0)

        row4 = FXHorizontalFrame(p=V, pt=10, hs=DEFAULT_SPACING, vs=DEFAULT_SPACING, opts=LAYOUT_FILL_X)
        AFXTextField(p=row4, ncols=52, labelText="Output directory:", tgt=form.outDirKw, sel=0)
        FXButton(
            p=row4, text=" Select Folder ",
            ic=afxGetIcon("fileOpen", AFX_ICON_SMALL),
            tgt=DirSelectHandler(form.outDirKw), sel=AFXMode.ID_ACTIVATE
        )

        row5 = FXHorizontalFrame(p=V, pt=10, hs=DEFAULT_SPACING, opts=LAYOUT_FILL_X)
        AFXTextField(p=row5, ncols=35, labelText="Title:", tgt=form.titleKw, sel=0)

        row6 = FXHorizontalFrame(p=V, pt=6, hs=DEFAULT_SPACING, opts=LAYOUT_FILL_X)
        AFXTextField(p=row6, ncols=10, labelText="X label:", tgt=form.xLabelKw, sel=0)
        AFXTextField(p=row6, ncols=10, labelText="Y label:", tgt=form.yLabelKw, sel=0)
        AFXTextField(p=row6, ncols=10, labelText="Z label:", tgt=form.zLabelKw, sel=0)


class DirSelectHandler(FXObject):
    def __init__(self, kw):
        self.kw = kw
        self.readOnlyKw = AFXBoolKeyword(None, "readOnly", AFXBoolKeyword.TRUE_FALSE, False)
        FXObject.__init__(self)
        FXMAPFUNC(self, SEL_COMMAND, AFXMode.ID_ACTIVATE, DirSelectHandler.activate)

    def activate(self, sender, sel, ptr):
        dlg = AFXFileSelectorDialog(
            getAFXApp().getAFXMainWindow(),
            "Select Directory",
            self.kw, self.readOnlyKw,
            AFXSELECTFILE_DIRECTORY,
            "*", AFXIntTarget(0)
        )
        dlg.create()
        dlg.showModal()