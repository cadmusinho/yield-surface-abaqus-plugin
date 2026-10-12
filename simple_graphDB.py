from abaqusGui import *
from abaqusConstants import *

class simple_graphDB(AFXDataDialog):
    def __init__(self, form):
        AFXDataDialog.__init__(self, form, "Simple Graph (Multi-Surface)",
                               self.OK | self.CANCEL, DIALOG_ACTIONS_SEPARATOR)

        V = AFXVerticalAligner(p=self, pl=0, pr=0, pt=0, pb=0)

        self._path_rows = []
        self._next_row = 1

        box = FXVerticalFrame(p=V, opts=LAYOUT_FILL_X)

        for i, (kwPath, kwName) in enumerate(zip(form.pathsGuiKws, form.namesGuiKws)):
            row = FXHorizontalFrame(p=box, hs=DEFAULT_SPACING, vs=DEFAULT_SPACING, opts=LAYOUT_FILL_X)

            label = "CSV directory:" if i == 0 else ("CSV directory %d:" % (i + 1))
            AFXTextField(p=row, ncols=45, labelText=label, tgt=kwPath, sel=0)

            FXButton(p=row, text=" Select Folder ", ic=afxGetIcon("fileOpen", AFX_ICON_SMALL),
                     tgt=DirSelectHandler(kwPath), sel=AFXMode.ID_ACTIVATE)

            AFXTextField(p=row, ncols=18, labelText="Model:", tgt=kwName, sel=0)

            if i == 0:
                FXButton(p=row, text=" + ", tgt=AddRowHandler(self), sel=AFXMode.ID_ACTIVATE)

            if i > 0:
                row.hide()

            self._path_rows.append(row)


        hf_peeq = FXHorizontalFrame(p=V, pt=10, hs=DEFAULT_SPACING)
        AFXTextField(p=hf_peeq, ncols=30,
                     labelText='Target PEEQ values (e.g. 0.01; 0.03; 0.05):',
                     tgt=form.target_valuesKw, sel=0,
                     opts=AFXTEXTFIELD_STRING | LAYOUT_CENTER_Y)

        hf_axis_labels = FXHorizontalFrame(p=V, pt=6, hs=DEFAULT_SPACING, opts=LAYOUT_FILL_X)
        AFXTextField(p=hf_axis_labels, ncols=10, labelText="X label:", tgt=form.xLabelKw, sel=0)
        AFXTextField(p=hf_axis_labels, ncols=10, labelText="Y label:", tgt=form.yLabelKw, sel=0)
        AFXTextField(p=hf_axis_labels, ncols=10, labelText="Z label:", tgt=form.zLabelKw, sel=0)

        gb_opts = FXGroupBox(p=V, text="Plot options", opts=FRAME_GROOVE | LAYOUT_FILL_X, pt=10)
        vf_opts = FXVerticalFrame(p=gb_opts, opts=LAYOUT_FILL_X, hs=DEFAULT_SPACING, vs=DEFAULT_SPACING)

        FXCheckButton(
            p=vf_opts,
            text="Show points",
            tgt=form.showPointsKw,
            sel=0
        )

        FXCheckButton(
            p=vf_opts,
            text="Show cylinder axis line",
            tgt=form.showAxisKw,
            sel=0
        )


class AddRowHandler(FXObject):
    def __init__(self, dialog):
        self.dialog = dialog
        FXObject.__init__(self)
        FXMAPFUNC(self, SEL_COMMAND, AFXMode.ID_ACTIVATE, AddRowHandler.activate)

    def activate(self, sender, sel, ptr):
        i = self.dialog._next_row
        if i < len(self.dialog._path_rows):
            self.dialog._path_rows[i].show()
            self.dialog._next_row += 1

            try:
                self.dialog.recalc()
                self.dialog.layout()
                self.dialog.resize(self.dialog.getDefaultWidth(), self.dialog.getDefaultHeight())
            except:
                pass


class DirSelectHandler(FXObject):
    def __init__(self, kw):
        self.kw = kw
        self.readOnlyKw = AFXBoolKeyword(None, "readOnly", AFXBoolKeyword.TRUE_FALSE, False)
        FXObject.__init__(self)
        FXMAPFUNC(self, SEL_COMMAND, AFXMode.ID_ACTIVATE, DirSelectHandler.activate)

    def activate(self, sender, sel, ptr):
        dlg = AFXFileSelectorDialog(getAFXApp().getAFXMainWindow(),
                                    "Select Directory",
                                    self.kw, self.readOnlyKw,
                                    AFXSELECTFILE_DIRECTORY,
                                    '*', AFXIntTarget(0))
        dlg.create()
        dlg.showModal()
