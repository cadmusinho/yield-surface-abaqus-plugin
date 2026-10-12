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

Private Function BuildLegendLabel(ByVal fileName As String) As String
    Dim base As String
    base = fileName

    If LCase$(Right$(base, 4)) = ".csv" Then
        base = Left$(base, Len(base) - 4)
    End If

    Dim model As String
    Dim peeq As String
    model = base
    peeq = ""

    Dim p As Long
    p = InStr(1, base, "__target_")
    If p > 1 Then
        model = Left$(base, p - 1)

        Dim rest As String
        rest = Mid$(base, p + Len("__target_"))

        Dim p2 As Long
        p2 = InStr(1, rest, "__")
        If p2 > 1 Then
            peeq = Left$(rest, p2 - 1)
        Else
            peeq = rest
        End If

        peeq = Replace$(peeq, "p", ".")
    End If

    If peeq <> "" Then
        BuildLegendLabel = model & " | PEEQ=" & peeq
    Else
        BuildLegendLabel = model
    End If
End Function

Private Function RectsOverlap(ByVal ax As Double, ByVal ay As Double, ByVal aw As Double, ByVal ah As Double, _
                              ByVal bx As Double, ByVal by As Double, ByVal bw As Double, ByVal bh As Double) As Boolean
    If ax + aw <= bx Then RectsOverlap = False: Exit Function
    If bx + bw <= ax Then RectsOverlap = False: Exit Function
    If ay + ah <= by Then RectsOverlap = False: Exit Function
    If by + bh <= ay Then RectsOverlap = False: Exit Function
    RectsOverlap = True
End Function

Sub Main()

    Dim chartsDir As String
    Dim csvDir As String
    Dim chartTitle As String
    Dim xLab As String
    Dim yLab As String
    Dim zLab As String
    Dim nSeries As Long

    Dim fn As Integer
    Dim tmp As String

    fn = FreeFile
    On Error GoTo cfg_err
    Open "config.txt" For Input As #fn
        Line Input #fn, chartsDir
        Line Input #fn, csvDir
        Line Input #fn, chartTitle
        Line Input #fn, xLab
        Line Input #fn, yLab
        Line Input #fn, zLab
        Line Input #fn, tmp
        tmp = Trim$(tmp)
        If tmp = "" Then tmp = "0"
        nSeries = CLng(tmp)
    Close #fn
    On Error GoTo 0

    chartsDir = Trim$(chartsDir)
    csvDir = Trim$(csvDir)
    chartTitle = Trim$(chartTitle)
    xLab = Trim$(xLab)
    yLab = Trim$(yLab)
    zLab = Trim$(zLab)

    If chartsDir = "" Or csvDir = "" Then
        MsgBox "config.txt: chartsDir/csvDir empty"
        Exit Sub
    End If

    If nSeries <= 0 Then
        MsgBox "config.txt: nSeries <= 0"
        Exit Sub
    End If

    Dim colors() As Long
    ReDim colors(1 To nSeries)

    Dim i As Long
    fn = FreeFile

    Open "config.txt" For Input As #fn
        For i = 1 To 7
            If EOF(fn) Then Exit For
            Line Input #fn, tmp
        Next i

        For i = 1 To nSeries
            If EOF(fn) Then
                colors(i) = RGB(0, 0, 0)
            Else
                Line Input #fn, tmp
                colors(i) = HexToLongColor(tmp)
            End If
        Next i
    Close #fn

    Dim Grapher As Object
    Set Grapher = CreateObject("Grapher.Application")
    Grapher.Visible = True

    Dim doc As Object
    Set doc = Grapher.Documents.Add(grfPlotDoc)

    On Error Resume Next
    doc.Windows.Item(1).PageUnits(grfInches)
    On Error GoTo 0

    Dim firstCsv As String
    firstCsv = Dir$(csvDir & "\*.csv")

    If firstCsv = "" Then
        MsgBox "No CSV files found in: " & csvDir
        Grapher.Quit
        Exit Sub
    End If

    Dim firstPath As String
    firstPath = csvDir & "\" & firstCsv

    doc.Shapes.AddXYZPlotGraph firstPath, 1, 2, 3

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
    pPlot.Symbol.Fill.ForeColor = colors(1)

    Dim lbl As String
    lbl = BuildLegendLabel(firstCsv)

    On Error Resume Next
    pPlot.Name = lbl
    On Error GoTo 0

    Dim idx As Long
    idx = 2

    Dim fileName As String
    fileName = Dir$(csvDir & "\*.csv")

    Do While fileName <> ""
        If fileName <> firstCsv Then
            g.AddXYZPlot csvDir & "\" & fileName, 1, 2, 3, "X Axis 1", "Y Axis 1", "Z Axis 1"

            Set pPlot = g.Plots.Item(idx)
            pPlot.Line.Style = "Invisible"

            If idx <= nSeries Then
                pPlot.Symbol.Fill.ForeColor = colors(idx)
            Else
                pPlot.Symbol.Fill.ForeColor = colors(((idx - 1) Mod nSeries) + 1)
            End If

            lbl = BuildLegendLabel(fileName)
            On Error Resume Next
            pPlot.Name = lbl
            On Error GoTo 0

            idx = idx + 1
        End If

        fileName = Dir$()
    Loop

    Dim leg As Object
    On Error Resume Next
    Err.Clear
    Set leg = doc.Shapes.AddLegend()
    If Err.Number <> 0 Then
        Err.Clear
        Set leg = doc.Shapes.AddLegendShape()
    End If
    On Error GoTo 0

    If Not leg Is Nothing Then
        On Error Resume Next
        leg.Visible = True
        On Error GoTo 0
    End If

    If Not leg Is Nothing Then

        Dim pageW As Double, pageH As Double
        pageW = 0: pageH = 0

        On Error Resume Next
        doc.Windows.Item(1).PageUnits(grfInches)
        pageW = doc.PageSetup.Width
        pageH = doc.PageSetup.Height
        On Error GoTo 0

        If pageW > 0 And pageH > 0 Then

            Dim m As Double
            m = 0.25 ' margines

            Dim gX As Double, gY As Double, gW As Double, gH As Double
            On Error Resume Next
            gX = g.Left: gY = g.Top: gW = g.Width: gH = g.Height
            On Error GoTo 0

            Dim topFromBottom As Boolean
            topFromBottom = False
            On Error Resume Next
            If gY > (pageH / 2) Then topFromBottom = True
            On Error GoTo 0

            Dim graphTop As Double
            If topFromBottom Then
                ' "góra" = y + h
                graphTop = gY + gH
            Else
                ' "góra" = y
                graphTop = gY
            End If

            On Error Resume Next
            leg.Left = (gX + gW) - leg.Width - m
            If topFromBottom Then
                leg.Top = graphTop - leg.Height - m
            Else
                leg.Top = graphTop + m
            End If
            On Error GoTo 0

            Dim lX As Double, lY As Double, lW As Double, lH As Double
            On Error Resume Next
            lX = leg.Left: lY = leg.Top: lW = leg.Width: lH = leg.Height
            On Error GoTo 0

            Dim overlap As Boolean
            overlap = RectsOverlap(gX, gY, gW, gH, lX, lY, lW, lH)

            If lH > (gH * 0.55) Then overlap = True

            If overlap Then
                Dim reserveW As Double
                reserveW = leg.Width + m + 0.05

                Dim maxGraphW As Double
                maxGraphW = pageW - gX - reserveW - m

                On Error Resume Next
                If maxGraphW > (gW * 0.60) Then
                    g.Width = maxGraphW
                End If
                On Error GoTo 0

                On Error Resume Next
                leg.Left = gX + g.Width + m
                If topFromBottom Then
                    leg.Top = (gY + gH) - leg.Height - m
                Else
                    leg.Top = gY + m
                End If
                On Error GoTo 0
            End If

            On Error Resume Next
            If leg.Left + leg.Width > pageW - m Then leg.Left = pageW - leg.Width - m
            If leg.Left < m Then leg.Left = m

            If topFromBottom Then
                If leg.Top < m Then leg.Top = m
                If leg.Top + leg.Height > pageH - m Then leg.Top = pageH - leg.Height - m
            Else
                If leg.Top < m Then leg.Top = m
                If leg.Top + leg.Height > pageH - m Then leg.Top = pageH - leg.Height - m
            End If
            On Error GoTo 0

        End If
    End If

    Dim outJpg As String
    outJpg = chartsDir & "\" & chartTitle & ".jpg"

    On Error Resume Next
    doc.Export2 outJpg, "JPG"
    If Err.Number <> 0 Then
        Err.Clear
        doc.Export outJpg
    End If
    On Error GoTo 0

    Grapher.Quit
    Exit Sub

cfg_err:
    MsgBox "Cannot read config.txt from working directory. Error: " & Err.Description
    On Error Resume Next
    Close #fn
    On Error GoTo 0

End Sub
