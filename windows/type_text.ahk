#Requires AutoHotkey v2.0
#SingleInstance Force
#NoTrayIcon

; type_text: read text from STDIN (preferred), else from command line args, SendText(), exit.

text := ""

; Preferred: STDIN, avoids quoting/length issues
try {
    stdin := FileOpen("*", "r")
    text := stdin.Read()
} catch {
    text := ""
}

; Fallback: join all args with spaces
if (text = "") {
    if (A_Args.Length < 1)
        ExitApp(2)

    for i, a in A_Args
        text .= (i = 1 ? "" : " ") a
}

SetKeyDelay(-1, -1)
SendText(text)
ExitApp(0)

