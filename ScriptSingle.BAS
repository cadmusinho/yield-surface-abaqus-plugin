Option Explicit

Private Function HexToLongColor(ByVal hx As String) As Long
    Dim s As String
    s = Trim$(hx)

    If Left$(s, 1) = "#" Then s = Mid$(s, 2)
    If Len(s) <> 6 Then
        HexToLongColor = RGB(0, 0, 0)
        Exit Function
    End If

    Dim r As Long, g As Long, b As Long
    r = CLng("&H" & Mid$(s, 1, 2))
    g = CLng("&H" & Mid$(s, 3, 2))
    b = CLng("&H" & Mid$(s, 5, 2))

    HexToLongColor = RGB(r, g, b)
End Function

Sub Main()

    Dim chartsDir As String
    Dim csvPath As String
    Dim chartTitle As String
    Dim xLab As String, yLab As String, zLab As String
    Dim colorHex As String

    Dim fn As Integer
    fn = FreeFile

    On Error GoTo cfg_err
    Open "config_single.txt" For Input As #fn
        Line Input #fn, chartsDir
        Line Input #fn, csvPath
        Line Input #fn, chartTitle
        Line Input #fn, xLab
        Line Input #fn, yLab
        Line Input #fn, zLab
        Line Input #fn, colorHex
    Close #fn
    On Error GoTo 0

    chartsDir = Trim$(chartsDir)
    csvPath = Trim$(csvPath)
    chartTitle = Trim$(chartTitle)
    xLab = Trim$(xLab)
    yLab = Trim$(yLab)
    zLab = Trim$(zLab)
    colorHex = Trim$(colorHex)

    If chartsDir = "" Or csvPath = "" Then
        MsgBox "config_single.txt: chartsDir/csvPath empty"
        Exit Sub
    End If

    Dim c As Long
    c = HexToLongColor(colorHex)

    Dim Grapher As Object
    Set Grapher = CreateObject("Grapher.Application")
    Grapher.Visible = True

    Dim doc As Object
    Set doc = Grapher.Documents.Add(grfPlotDoc)

    On Error Resume Next
    doc.Windows.Item(1).PageUnits(grfInches)
    On Error GoTo 0

    doc.Shapes.AddXYZPlotGraph csvPath, 1, 2, 3

    Dim g As Object
    Set g = doc.Shapes.Item(1)

    On Error Resume Next
    g.Title.Text = chartTitle
    g.Axes.Item(1).Title.Text = xLab
    g.Axes.Item(2).Title.Text = yLab
    g.Axes.Item(3).Title.Text = zLab
    On Error GoTo 0

    Dim YAxis1 As Object, XAxis1 As Object, ZAxis1 As Object
    Set YAxis1 = g.Axes.Item(2)
    YAxis1.Link.ToAxis = "X Axis 1"
    YAxis1.Link.XPos = True

    Set XAxis1 = g.Axes.Item(1)
    XAxis1.Link.ToAxis = "Y Axis 1"
    XAxis1.Link.YPos = True

    Set ZAxis1 = g.Axes.Item(3)
    ZAxis1.Link.ToAxis = "X Axis 1"
    ZAxis1.Link.XPos = True
    ZAxis1.Link.YPos = True

    Dim pPlot As Object
    Set pPlot = g.Plots.Item(1)

    pPlot.Line.Style = "Invisible"

    On Error Resume Next
    pPlot.BackProjection = True
    pPlot.SideProjection = True
    pPlot.BottomProjection = True
    On Error GoTo 0

    On Error Resume Next
    pPlot.Symbol.Size = 0.06
    pPlot.Symbol.Fill.ForeColor = grfColorGreen
    On Error GoTo 0

    Dim outJpg As String
    outJpg = chartsDir & "\" & chartTitle & ".jpg"

    On Error Resume Next
    doc.Export2 outJpg, False, "ColorDepth=24;ColorReductionMethod=5;ExportImageFormatBGR24=1;HDPI=96;Height=790;Hide3DVectorControls=1;HideCoordinateSystemControls=1;KeepAspect=1;KeepPixelSize=0;Quality=100;Update_ColorDepth=24;Update_ColorReductionMethod=5;Update_Height=790;Update_Width=747;VDPI=96;Width=747", True, "jpg"
    If Err.Number <> 0 Then
        Err.Clear
        doc.Export outJpg
    End If
    On Error GoTo 0

    Grapher.Quit
    Exit Sub

cfg_err:
    MsgBox "Cannot read config_single.txt from working directory. Error: " & Err.Description
    On Error Resume Next
    Close #fn
    On Error GoTo 0

End Sub
