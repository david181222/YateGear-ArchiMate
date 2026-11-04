# Levanta la aplicación generada desde salida\, con el SDK 8 que fija salida\global.json.
# Se detiene con Ctrl+C.
#
# Uso (desde la carpeta generador):
#   powershell -ExecutionPolicy Bypass -File .\ejecutar.ps1                (Windows)
#   pwsh ./ejecutar.ps1                                                     (Linux)
#   ... -Puerto 5090    (si el puerto está ocupado)
#
# Con -Puerto el cambio es solo para esta vez: cambia también @base en salida/pruebas.http.
# Para cambiarlo siempre, cambia PUERTO en src/generar.py y vuelve a generar.
#
# Este archivo va en UTF-8 con BOM: Windows PowerShell 5.1 lee sin BOM como ANSI.
param(
    [int]$Puerto = 0
)

Set-Location $PSScriptRoot
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$proyecto = "GestionDelArriendo"
# Windows: el dotnet del PATH. Linux: si existe, el SDK de ~/.dotnet, para no cambiar el dotnet del sistema.
$enWindows = [System.Environment]::OSVersion.Platform -eq "Win32NT"
$dotnet = "dotnet"
if (-not $enWindows -and (Test-Path "$HOME/.dotnet/dotnet")) { $dotnet = "$HOME/.dotnet/dotnet"; $env:DOTNET_ROOT = "$HOME/.dotnet" }
$csproj = "salida/$proyecto/$proyecto.csproj"
$config = "salida/$proyecto/Properties/launchSettings.json"

if (-not (Test-Path $csproj)) {
    Write-Host "ERROR: no existe $csproj. Ejecuta primero generar.ps1." -ForegroundColor Red
    exit 1
}
if ($Puerto -eq 0) {
    $url = (Get-Content $config -Raw -Encoding UTF8 | ConvertFrom-Json).profiles.$proyecto.applicationUrl
    $Puerto = ([Uri]$url).Port
}
# El puerto está libre si se puede abrir aquí mismo.
$libre = $true
try {
    $prueba = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $Puerto)
    $prueba.Start()
    $prueba.Stop()
} catch {
    $libre = $false
}
if (-not $libre) {
    Write-Host "ERROR: el puerto $Puerto está ocupado. Usa otro: .\ejecutar.ps1 -Puerto 5090" -ForegroundColor Red
    exit 1
}

Write-Host "Aplicación en http://localhost:$Puerto/gestion-del-arriendo  (Ctrl+C para detener)" -ForegroundColor Green
# Desde salida, para que dotnet use el global.json (SDK 8).
Set-Location salida
& $dotnet run --project $proyecto -- --urls "http://localhost:$Puerto"
exit $LASTEXITCODE
