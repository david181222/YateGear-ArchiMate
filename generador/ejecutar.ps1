# Levanta la aplicación generada (el host, con todos los contextos) desde salida/, con el SDK 8 que fija
# salida/global.json. Lee el proyecto y el puerto de salida/contextos.json. Se detiene con Ctrl+C.
#
# Uso (desde la carpeta generador):
#   powershell -ExecutionPolicy Bypass -File .\ejecutar.ps1                (Windows)
#   pwsh ./ejecutar.ps1                                                     (Linux)
#   ... -Puerto 5090    (si el puerto está ocupado)
#   ... -Salida ejemplo/salida    (otra carpeta generada; por defecto, salida)
#
# Con -Puerto el cambio es solo para esta vez: cambia también @base en salida/pruebas/<Proyecto>/pruebas.http.
# Para cambiarlo siempre, genera con otro puerto: generar.ps1 -Puerto 5090.
#
# Este archivo va en UTF-8 con BOM: Windows PowerShell 5.1 lee sin BOM como ANSI.
param(
    [int]$Puerto = 0,
    [string]$Salida = "salida"
)

Set-Location $PSScriptRoot
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
# Windows: el dotnet del PATH. Linux: si existe, el SDK de ~/.dotnet, para no cambiar el dotnet del sistema.
$enWindows = [System.Environment]::OSVersion.Platform -eq "Win32NT"
$dotnet = "dotnet"
if (-not $enWindows -and (Test-Path "$HOME/.dotnet/dotnet")) { $dotnet = "$HOME/.dotnet/dotnet"; $env:DOTNET_ROOT = "$HOME/.dotnet" }
$manifiesto = "$Salida/contextos.json"

if (-not (Test-Path $manifiesto)) {
    Write-Host "ERROR: no existe $manifiesto. Ejecuta primero generar.ps1." -ForegroundColor Red
    exit 1
}
$solucion = Get-Content $manifiesto -Raw -Encoding UTF8 | ConvertFrom-Json
$proyecto = $solucion.host
if ($Puerto -eq 0) { $Puerto = $solucion.puerto }
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

Write-Host "Aplicación en http://localhost:$Puerto  (Ctrl+C para detener)." -ForegroundColor Green
Write-Host "Rutas de la API, en el navegador: http://localhost:$Puerto/" -ForegroundColor Green
Write-Host "Contextos:" -ForegroundColor Green
foreach ($c in $solucion.contextos) { Write-Host "  http://localhost:$Puerto$($c.ruta_base)  $($c.nombre)" -ForegroundColor Green }
# Desde la carpeta de salida, para que dotnet use el global.json (SDK 8).
Set-Location $Salida
& $dotnet run --project $proyecto -- --urls "http://localhost:$Puerto"
exit $LASTEXITCODE
