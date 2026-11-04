# Prueba los escenarios del YAML contra la aplicación generada.
# Compila, levanta la aplicación desde salida\ (SDK 8 del global.json), ejecuta los escenarios
# de salida\escenarios.json, marca cada paso con ✓ o ✗ y detiene la aplicación.
# Termina con código 1 si algún paso falla.
#
# Uso (desde la carpeta generador, después de generar.ps1):
#   powershell -ExecutionPolicy Bypass -File .\probar.ps1                  (Windows)
#   pwsh ./probar.ps1                                                       (Linux)
#   ... -Puerto 5090    (si el puerto está ocupado)
#
# Este archivo va en UTF-8 con BOM: Windows PowerShell 5.1 lee sin BOM como ANSI.
param(
    [int]$Puerto = 0
)

Set-Location $PSScriptRoot
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$proyecto = "GestionDelArriendo"
# Windows: .venv\Scripts y el dotnet del PATH. Linux: .venv/bin y, si existe, el SDK de ~/.dotnet.
$enWindows = [System.Environment]::OSVersion.Platform -eq "Win32NT"
$py = if ($enWindows) { "./.venv/Scripts/python.exe" } else { "./.venv/bin/python" }
$dotnet = "dotnet"
if (-not $enWindows -and (Test-Path "$HOME/.dotnet/dotnet")) { $dotnet = "$HOME/.dotnet/dotnet"; $env:DOTNET_ROOT = "$HOME/.dotnet" }
$escenarios = "salida/escenarios.json"

function Fallo([string]$texto) {
    Write-Host "ERROR: $texto" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $escenarios)) { Fallo "no existe $escenarios. Ejecuta primero generar.ps1." }
if (-not (Test-Path $py)) { Fallo "no existe .venv. Ejecuta primero generar.ps1." }
if ($Puerto -eq 0) {
    $config = "salida/$proyecto/Properties/launchSettings.json"
    $Puerto = ([Uri](Get-Content $config -Raw -Encoding UTF8 | ConvertFrom-Json).profiles.$proyecto.applicationUrl).Port
}
$libre = $true
try {
    $prueba = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $Puerto)
    $prueba.Start()
    $prueba.Stop()
} catch {
    $libre = $false
}
if (-not $libre) { Fallo "el puerto $Puerto está ocupado. Usa otro: .\probar.ps1 -Puerto 5090" }

Write-Host "== Compilar"
Push-Location salida
& $dotnet build -nologo -v q
$codigo = $LASTEXITCODE
Pop-Location
if ($codigo -ne 0) { Fallo "la compilación falló (ver arriba)." }

$salidaAbs = (Resolve-Path salida).Path
$url = "http://localhost:$Puerto"
Write-Host "== Levantar la aplicación en $url"
$opciones = @{ FilePath = $dotnet; ArgumentList = "run --project $proyecto --no-build -- --urls $url"
               WorkingDirectory = $salidaAbs; PassThru = $true }
if ($enWindows) {
    $opciones.WindowStyle = "Hidden"
} else {
    # En Linux no hay ventana que ocultar: la salida de la aplicación va a salida/intermedio/aplicacion*.log.
    $opciones.RedirectStandardOutput = Join-Path $salidaAbs "intermedio/aplicacion.log"
    $opciones.RedirectStandardError = Join-Path $salidaAbs "intermedio/aplicacion-errores.log"
}
$app = Start-Process @opciones
$codigo = 1
try {
    $lista = $false
    for ($i = 0; $i -lt 60 -and -not $lista; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            Invoke-WebRequest -UseBasicParsing "$url/gestion-del-arriendo/bitacora" -TimeoutSec 2 | Out-Null
            $lista = $true
        } catch {}
    }
    if (-not $lista) {
        Write-Host "ERROR: la aplicación no respondió en 30 segundos." -ForegroundColor Red
    } else {
        Write-Host "== Ejecutar los escenarios"
        & $py src/probar.py $escenarios $url
        $codigo = $LASTEXITCODE
    }
} finally {
    # Se busca por la ruta del ejecutable y no por el nombre: en Linux el nombre se corta a 15 caracteres.
    $dentro = Join-Path $salidaAbs "*"
    Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -like $dentro } | Stop-Process -Force
    Stop-Process -Id $app.Id -Force -ErrorAction SilentlyContinue
    Write-Host ""
    Write-Host "== Aplicación detenida"
}
exit $codigo
