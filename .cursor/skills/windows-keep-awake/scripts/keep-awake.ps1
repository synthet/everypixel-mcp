param([ValidateRange(1, 1440)][int]$Minutes = 30)
$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'This helper requires Windows and PowerShell 7.' }
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class FrameworkExecutionState {
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern uint SetThreadExecutionState(uint flags);
}
'@
try {
    if ([FrameworkExecutionState]::SetThreadExecutionState(0x80000003) -eq 0) {
        throw 'SetThreadExecutionState failed.'
    }
    $taskExpiration = [DateTime]::UtcNow.AddMinutes($Minutes)
    Write-Output "Temporary keep-awake expires at $($taskExpiration.ToString('o')). Stop with Ctrl+C."
    while ([DateTime]::UtcNow -lt $taskExpiration) { Start-Sleep -Seconds 5 }
}
finally { [void][FrameworkExecutionState]::SetThreadExecutionState(0x80000000) }
