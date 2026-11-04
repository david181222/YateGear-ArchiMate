# Genera el proyecto C# de un contexto desde el modelo ArchiMate de YateGear.
# Pasos: entorno de Python, exportar con la ACLI de Archi, extraer, revisar el YAML, generar y compilar.
# Se detiene en el primer paso que falle y dice cuál.
#
# Uso (desde la carpeta generador):
#   powershell -ExecutionPolicy Bypass -File .\generar.ps1     (Windows)
#   pwsh ./generar.ps1                                          (Linux)
#
# Las rutas van con "/", que sirve en Windows y en Linux.
# Este archivo va en UTF-8 con BOM: Windows PowerShell 5.1 lee sin BOM como ANSI.
param(
    [string]$Modelo = "../modelo/YateGear.archimate",
    [string]$Contexto = "Contexto Gestión del arriendo",
    [string]$Specs = "specs/gestion-del-arriendo.yaml",
    [string]$Archi = ""
)

Set-Location $PSScriptRoot
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
# Windows: .venv\Scripts y el dotnet del PATH. Linux: .venv/bin y, si existe, el SDK de ~/.dotnet,
# para no cambiar el dotnet del sistema. ($IsWindows no existe en Windows PowerShell 5.1.)
$enWindows = [System.Environment]::OSVersion.Platform -eq "Win32NT"
$py = if ($enWindows) { "./.venv/Scripts/python.exe" } else { "./.venv/bin/python" }
$dotnet = "dotnet"
if (-not $enWindows -and (Test-Path "$HOME/.dotnet/dotnet")) { $dotnet = "$HOME/.dotnet/dotnet"; $env:DOTNET_ROOT = "$HOME/.dotnet" }
if (-not $Archi) {
    $candidatos = if ($enWindows) { @("C:\Program Files\Archi\Archi.exe") } else {
        @((Get-Command Archi -ErrorAction SilentlyContinue).Source, "$HOME/.local/opt/Archi/Archi", "/opt/Archi/Archi") }
    $Archi = $candidatos | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
    if (-not $Archi) { $Archi = $candidatos[-1] }
}
$xml = Join-Path $PSScriptRoot "salida/intermedio/YateGear.xml"
$json = "salida/intermedio/modelo-ddd.json"

function Paso([string]$numero, [string]$texto) {
    Write-Host ""
    Write-Host "== Paso $numero. $texto" -ForegroundColor Cyan
}

function Fallo([string]$texto) {
    Write-Host ""
    Write-Host "ERROR: $texto" -ForegroundColor Red
    exit 1
}

Paso 1 "Entorno de Python (.venv)"
if (-not (Test-Path $py)) {
    Write-Host "No existe .venv: se crea con Python 3.13 y se instala requirements.txt."
    if ($enWindows) {
        py -3.13 -m venv .venv
    } else {
        # python3.13 del sistema o, si no hay, el que instala uv (uv python install 3.13).
        $base = (Get-Command python3.13 -ErrorAction SilentlyContinue).Source
        if (-not $base -and (Get-Command uv -ErrorAction SilentlyContinue)) { $base = uv python find 3.13 2>$null }
        if (-not $base) { Fallo "no se encontró Python 3.13. Instálalo, por ejemplo con: uv python install 3.13" }
        # La ruta real: si es un enlace (como el de uv en ~/.local/bin), el venv no encuentra la biblioteca estándar.
        $base = & $base -c "import os, sys; print(os.path.realpath(sys.executable))"
        & $base -m venv .venv
    }
    if ($LASTEXITCODE -ne 0) { Fallo "no se pudo crear el entorno virtual con Python 3.13. Instala Python 3.13." }
    & $py -m pip install --disable-pip-version-check -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Fallo "no se pudieron instalar las librerías de requirements.txt." }
} else {
    Write-Host "Ya existe .venv."
}

Paso 2 "Exportar el modelo al formato de intercambio con la ACLI de Archi"
if (-not (Test-Path $Modelo)) { Fallo "no existe el modelo $Modelo." }
if (-not (Test-Path $Archi)) { Fallo "no existe $Archi. Usa el parámetro -Archi con la ruta del ejecutable de Archi." }
$modeloAbs = (Resolve-Path $Modelo).Path
# El "| Out-Host" hace que PowerShell espere a que Archi termine.
& $Archi -application com.archimatetool.commandline.app -consoleLog -nosplash -a --loadModel $modeloAbs --xmlexchange.export $xml | Out-Host
if ($LASTEXITCODE -ne 0) { Fallo "la ACLI de Archi terminó con código $LASTEXITCODE." }
if (-not (Test-Path $xml)) { Fallo "la ACLI no escribió $xml." }

Paso 3 "Extraer el contexto a modelo-ddd.json"
& $py src/extraer.py $xml $Contexto $json
if ($LASTEXITCODE -ne 0) { Fallo "la extracción encontró errores en el modelo (ver arriba)." }

Paso 4 "Revisar el YAML contra el modelo"
& $py src/specs.py $json $Specs
if ($LASTEXITCODE -ne 0) { Fallo "el YAML no cumple con el modelo (ver arriba)." }

Paso 5 "Generar el proyecto C#"
& $py src/generar.py $json $Specs salida
if ($LASTEXITCODE -ne 0) { Fallo "la generación falló (ver arriba)." }

Paso 6 "Compilar con .NET 8"
# Desde salida, para que dotnet use el global.json (SDK 8).
Push-Location salida
& $dotnet build -nologo
$codigo = $LASTEXITCODE
Pop-Location
if ($codigo -ne 0) { Fallo "la compilación falló (ver arriba)." }

Write-Host ""
Write-Host "Listo. Para correr la aplicación: ejecutar.ps1; para probar los escenarios: probar.ps1" -ForegroundColor Green
