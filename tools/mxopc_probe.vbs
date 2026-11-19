' MX OPC Server 연결 확인 도구 (읽기 전용) - Computer Use 테스트 C2/C4 후속
'
' OPC DA는 32비트 COM 이라 32비트 스크립트 호스트로 실행합니다.
'   C:\Windows\SysWOW64\cscript.exe //nologo tools\mxopc_probe.vbs [장치] [태그1 태그2 ...]
' 예)
'   C:\Windows\SysWOW64\cscript.exe //nologo tools\mxopc_probe.vbs QSIM CNT_GOOD CLAMP
'
' 하는 일
'   1) Mitsubishi.MXOPC.6 에 접속해 ServerState · 버전 출력
'   2) 루트 장치 목록과 지정 장치의 태그 수 · 앞 10개 태그 출력
'   3) 지정한 태그를 장치(Device)에서 읽어 값 · 품질(192 = Good) 출력
' 쓰기는 하지 않습니다.
'
' 사용하는 COM 래퍼: OPC.SiemensDAAuto (TIA/WinCC 설치에 포함된 OPC DA Automation 2.0 래퍼, 32비트)

Option Explicit
Dim s, b, g, it, n, k, i, dev, v, q, t, args
Set args = WScript.Arguments
dev = "QSIM"
If args.Count > 0 Then dev = args(0)

Set s = CreateObject("OPC.SiemensDAAuto")
s.Connect "Mitsubishi.MXOPC.6"
WScript.Echo "[연결] Mitsubishi.MXOPC.6  ServerState=" & s.ServerState & " (1=RUNNING)  " & s.VendorInfo & " " & s.MajorVersion & "." & s.MinorVersion & "." & s.BuildNumber

Set b = s.CreateBrowser
b.ShowBranches
WScript.Echo "[장치] " & b.Count & "개"
For Each n In b : WScript.Echo "   " & n : Next

b.MoveDown dev
b.ShowLeafs
WScript.Echo "[" & dev & " 태그] " & b.Count & "개 (앞 10개)"
k = 0
For Each n In b
  k = k + 1 : If k > 10 Then Exit For
  WScript.Echo "   " & b.GetItemID(n)
Next

If args.Count > 1 Then
  Set g = s.OPCGroups.Add("probe")
  g.IsActive = True
  WScript.Echo "[읽기]"
  For i = 1 To args.Count - 1
    On Error Resume Next
    Set it = g.OPCItems.AddItem(dev & "." & args(i), i)
    If Err.Number <> 0 Then
      WScript.Echo "   " & dev & "." & args(i) & "  등록 실패 0x" & Hex(Err.Number) & " (0xC0040007 = 없는 태그 ID)"
      Err.Clear
    Else
      it.Read 2, v, q, t
      WScript.Echo "   " & dev & "." & args(i) & " = " & v & "  quality=" & q & "  " & t
    End If
    On Error GoTo 0
  Next
End If
s.Disconnect
