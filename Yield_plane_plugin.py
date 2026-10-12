from abaqusGui import *
from abaqusConstants import ALL
import os, osutils


class Pbc_plugin(AFXForm):
    def __init__(self, owner):
        AFXForm.__init__(self, owner)
        self.radioButtonGroups = {}

        self.cmd = AFXGuiCommand(
            mode=self,
            method='pbc',
            objectName='Yield_Pbc',
            registerQuery=False
        )

        self.pathKw = AFXStringKeyword(self.cmd, 'path', True, '')
        self.epsMaxKw = AFXFloatKeyword(self.cmd, 'eps_max', True, 0.15)

        self.numIntervalsKw = AFXIntKeyword(self.cmd, 'num_intervals', True, 100)
        self.timePeriodKw   = AFXFloatKeyword(self.cmd, 'time_period', True, 1.0)
        self.maxNumIncKw    = AFXIntKeyword(self.cmd, 'max_num_inc', True, 2000)
        self.initialIncKw   = AFXFloatKeyword(self.cmd, 'initial_inc', True, 0.01)
        self.minIncKw       = AFXFloatKeyword(self.cmd, 'min_inc', True, 1e-12)
        self.maxIncKw       = AFXFloatKeyword(self.cmd, 'max_inc', True, 0.01)

        self.thetaMaxKw     = AFXFloatKeyword(self.cmd, 'theta_max', True, 360.0)
        self.thetaCountKw   = AFXIntKeyword(self.cmd, 'theta_count', True, 5)
        self.nHydroKw       = AFXIntKeyword(self.cmd, 'n_hydro', True, 7)
        self.nDevKw         = AFXIntKeyword(self.cmd, 'n_dev', True, 3)

    def getFirstDialog(self):
        import Yield_PbcDB
        return Yield_PbcDB.YieldPbcDB(self)

    def doCustomChecks(self):
        return True

    def okToCancel(self):
        return False

class find_results_plugin(AFXForm):

    def __init__(self, owner):
        AFXForm.__init__(self, owner)
        self.cmd = AFXGuiCommand(
            mode=self,
            method='find_results',
            objectName='find_results',
            registerQuery=False
        )
        self.pathKw = AFXStringKeyword(self.cmd, 'path', True, '')

    def getFirstDialog(self):
        import find_resultsDB
        return find_resultsDB.find_resultsDB(self)

    def doCustomChecks(self):
        return True

    def okToCancel(self):
        return False


class SimpleGraph_plugin(AFXForm):
    def __init__(self, owner):
        AFXForm.__init__(self, owner)
        self.cmd = AFXGuiCommand(mode=self, method="simple_graph",
                                 objectName="simple_graph", registerQuery=False)

        self.pathKw = AFXStringKeyword(self.cmd, "path", True, "")

        self.target_valuesKw = AFXStringKeyword(self.cmd, 'target_values', True, "")

        self.xLabelKw = AFXStringKeyword(self.cmd, 'x_label', True, "")
        self.yLabelKw = AFXStringKeyword(self.cmd, 'y_label', True, "")
        self.zLabelKw = AFXStringKeyword(self.cmd, 'z_label', True, "")

        self.MAX_PATHS = 8
        self.pathsGuiKws = []
        self.namesGuiKws = []

        for i in range(self.MAX_PATHS):
            kw_path = AFXStringKeyword(None, "csv_path_%d" % (i + 1), True, "")
            kw_name = AFXStringKeyword(None, "csv_name_%d" % (i + 1), True, "")
            self.pathsGuiKws.append(kw_path)
            self.namesGuiKws.append(kw_name)

        self.showPointsKw = AFXBoolKeyword(self.cmd, 'show_points', AFXBoolKeyword.TRUE_FALSE, True)
        self.showAxisKw   = AFXBoolKeyword(self.cmd, 'show_axis',   AFXBoolKeyword.TRUE_FALSE, True)

    def getFirstDialog(self):
        import simple_graphDB
        return simple_graphDB.simple_graphDB(self)

    def doCustomChecks(self):
        pairs = []
        for kwPath, kwName in zip(self.pathsGuiKws, self.namesGuiKws):
            try:
                p = (kwPath.getValue() or "").strip()
            except:
                p = ""
            try:
                n = (kwName.getValue() or "").strip()
            except:
                n = ""

            if not p:
                continue

            if not n:
                n = os.path.basename(p.rstrip("\\/")) or p

            pairs.append(f"{p}|{n}")

        self.pathKw.setValue(";".join(pairs))
        return True

    def okToCancel(self):
        return False

from abaqusGui import *
from abaqusConstants import ALL
import os

class Grapher_plugin(AFXForm):
    def __init__(self, owner):
        AFXForm.__init__(self, owner)

        self.cmd = AFXGuiCommand(
            mode=self,
            method="grapher",
            objectName="Grapher",
            registerQuery=False
        )

        self.pathKw = AFXStringKeyword(self.cmd, "path", True, "")

        self.outDirKw = AFXStringKeyword(self.cmd, "out_dir", True, "")

        self.target_valuesKw = AFXStringKeyword(self.cmd, "target_values", True, "")

        self.titleKw  = AFXStringKeyword(self.cmd, "title", True, "")
        self.xLabelKw = AFXStringKeyword(self.cmd, "x_label", True, "")
        self.yLabelKw = AFXStringKeyword(self.cmd, "y_label", True, "")
        self.zLabelKw = AFXStringKeyword(self.cmd, "z_label", True, "")

        self.MAX_PATHS = 12
        self.pathsGuiKws = []
        self.namesGuiKws = []
        for i in range(self.MAX_PATHS):
            kw_path = AFXStringKeyword(None, "csv_path_%d" % (i + 1), True, "")
            kw_name = AFXStringKeyword(None, "csv_name_%d" % (i + 1), True, "")
            self.pathsGuiKws.append(kw_path)
            self.namesGuiKws.append(kw_name)

    def getFirstDialog(self):
        import GrapherDB
        return GrapherDB.GrapherDB(self)

    def doCustomChecks(self):
        pairs = []
        for kwPath, kwName in zip(self.pathsGuiKws, self.namesGuiKws):
            try:
                p = (kwPath.getValue() or "").strip()
            except:
                p = ""
            try:
                n = (kwName.getValue() or "").strip()
            except:
                n = ""

            if not p:
                continue
            if not n:
                n = os.path.basename(p.rstrip("\\/")) or p

            pairs.append("%s|%s" % (p, n))

        self.pathKw.setValue(";".join(pairs))
        return True

    def okToCancel(self):
        return False

class GrapherSingle_plugin(AFXForm):
    def __init__(self, owner):
        AFXForm.__init__(self, owner)

        self.cmd = AFXGuiCommand(
            mode=self,
            method="grapher_single",
            objectName="GrapherSingle",
            registerQuery=False
        )

        self.folderKw = AFXStringKeyword(self.cmd, "folder", True, "")
        self.targetKw = AFXStringKeyword(self.cmd, "target_value", True, "")
        self.outDirKw = AFXStringKeyword(self.cmd, "out_dir", True, "")
        self.titleKw  = AFXStringKeyword(self.cmd, "title", True, "")
        self.xLabelKw = AFXStringKeyword(self.cmd, "x_label", True, "")
        self.yLabelKw = AFXStringKeyword(self.cmd, "y_label", True, "")
        self.zLabelKw = AFXStringKeyword(self.cmd, "z_label", True, "")
        self.modelKw = AFXStringKeyword(self.cmd, "model_name", True, "")

    def getFirstDialog(self):
        import GrapherSingleDB
        return GrapherSingleDB.GrapherSingleDB(self)

    def doCustomChecks(self):
        try:
            m = (self.modelKw.getValue() or "").strip()
        except:
            m = ""
        if not m:
            try:
                f = (self.folderKw.getValue() or "").strip()
            except:
                f = ""
            if f:
                self.modelKw.setValue(os.path.basename(f.rstrip("\\/")) or f)
        return True

    def okToCancel(self):
        return False

thisPath = os.path.abspath(__file__)
thisDir = os.path.dirname(thisPath)

toolset = getAFXApp().getAFXMainWindow().getPluginToolset()

toolset.registerGuiMenuButton(
    buttonText='Yield plane|1. Preprocessing',
    object=Pbc_plugin(toolset),
    messageId=AFXMode.ID_ACTIVATE,
    icon=None,
    kernelInitString='import Yield_Pbc',
    applicableModules=ALL,
    version='1.0',
    author='Kacper Mierzwa',
    description='Automatic PBC + job generation',
    helpUrl='N/A'
)

toolset.registerGuiMenuButton(
    buttonText='Yield plane|2. Homogenization',
    object=find_results_plugin(toolset),
    messageId=AFXMode.ID_ACTIVATE,
    icon=None,
    kernelInitString='import find_results',
    applicableModules=ALL,
    version='1.0',
    author='Kacper Mierzwa',
    description='Loading ODBs and calculating homogenized yield points',
    helpUrl='N/A'
)

toolset.registerGuiMenuButton(
    buttonText="Yield plane|3. Print cylinder",
    object=SimpleGraph_plugin(toolset),
    messageId=AFXMode.ID_ACTIVATE,
    icon=None,
    kernelInitString="import simple_graph",
    applicableModules=ALL,
    version="1.0",
    author="Kacper Mierzwa",
    description="Plots graph from CSV files",
    helpUrl="N/A"
)

toolset.registerGuiMenuButton(
    buttonText='Yield plane|4. Grapher comparison',
    object=Grapher_plugin(toolset),
    messageId=AFXMode.ID_ACTIVATE,
    icon=None,
    kernelInitString='import Grapher',
    applicableModules=ALL,
    version='8.0',
    author='Kacper Mierzwa',
    description='Comparison tool for multiple datasets',
    helpUrl='N/A'
)

toolset.registerGuiMenuButton(
    buttonText='Yield plane|5. Grapher single graph',
    object=GrapherSingle_plugin(toolset),
    messageId=AFXMode.ID_ACTIVATE,
    icon=None,
    kernelInitString='import GrapherSingle',
    applicableModules=ALL,
    version='1.0',
    author='Kacper Mierzwa',
    description='Single graph: 1 folder + 1 target -> 1 plot',
    helpUrl='N/A'
)