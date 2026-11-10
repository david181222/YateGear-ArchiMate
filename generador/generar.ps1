# Genera la solución C# desde un modelo ArchiMate: un proyecto por cada contexto que tiene YAML en specs/,
# más el host que los levanta y el bus entre contextos.
# Pasos: entorno de Python, exportar con la ACLI de Archi, extraer, revisar los YAML, generar y compilar.
# Se detiene en el primer paso que falle y dice cuál.
#
# Uso (desde la carpeta generador):
#   powershell -ExecutionPolicy Bypass -File .\generar.ps1     (Windows)
#   pwsh ./generar.ps1                                          (Linux)
#   ... -Specs specs/uno.yaml,specs/otro.yaml                   (solo esos contextos)
#   ... -SoloValidar                                            (exporta, extrae y revisa los YAML; no genera ni compila)
#   ... -Modelo ejemplo/Biblioteca.archimate -Specs ejemplo/specs/prestamos.yaml -Salida ejemplo/salida   (otro modelo)
#
# -Modelo: por defecto, el único .archimate de ../modelo. -Specs: por defecto, todos los specs/*.yaml.
# -Salida: la carpeta de lo generado, por defecto salida. -Puerto: el puerto de la aplicación generada, por defecto 5080. -SoloValidar no toca esa carpeta: el XML y el JSON
# intermedios van a una carpeta temporal.
#
# Las rutas van con "/", que sirve en Windows y en Linux.
# Este archivo va en UTF-8 con BOM: Windows PowerShell 5.1 lee sin BOM como ANSI.
param(
    [string]$Modelo = "",
    [string[]]$Specs = @(),
    [string]$Archi = "",
    [string]$Salida = "salida",
    [int]$Puerto = 5080,
    [switch]$SoloValidar
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
# Los intermedios (el XML exportado y modelo-ddd.json) van en <Salida>/intermedio; con -SoloValidar, a una carpeta temporal.
$intermedio = if ($SoloValidar) { Join-Path ([System.IO.Path]::GetTempPath()) "generador-solo-validar" } else { "$Salida/intermedio" }
New-Item -ItemType Directory -Force $intermedio | Out-Null
$json = "$intermedio/modelo-ddd.json"

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
if (-not $Modelo) {
    $modelos = @(Get-ChildItem "../modelo" -Filter "*.archimate" -File -ErrorAction SilentlyContinue)
    if ($modelos.Count -ne 1) { Fallo "en ../modelo hay $($modelos.Count) archivos .archimate; di cuál con -Modelo." }
    $Modelo = $modelos[0].FullName
}
if (-not (Test-Path $Modelo)) { Fallo "no existe el modelo $Modelo." }
# El XML se llama como el modelo: <Salida>/intermedio/<modelo>.xml (no se versiona).
$xml = Join-Path (Resolve-Path $intermedio).Path ([System.IO.Path]::GetFileNameWithoutExtension($Modelo) + ".xml")
if (-not (Test-Path $Archi)) { Fallo "no existe $Archi. Usa el parámetro -Archi con la ruta del ejecutable de Archi." }
$modeloAbs = (Resolve-Path $Modelo).Path
# El "| Out-Host" hace que PowerShell espere a que Archi termine.
& $Archi -application com.archimatetool.commandline.app -consoleLog -nosplash -a --loadModel $modeloAbs --xmlexchange.export $xml | Out-Host
if ($LASTEXITCODE -ne 0) { Fallo "la ACLI de Archi terminó con código $LASTEXITCODE." }
if (-not (Test-Path $xml)) { Fallo "la ACLI no escribió $xml." }

Paso 3 "Extraer los contextos a modelo-ddd.json"
& $py src/extraer.py $xml $json
if ($LASTEXITCODE -ne 0) { Fallo "la extracción encontró errores en el modelo (ver arriba)." }

Paso 4 "Revisar cada YAML contra el modelo"
# Con -File, "-Specs a,b" llega como un solo texto: se separa por comas.
$Specs = @($Specs | ForEach-Object { $_ -split "," } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
if ($Specs.Count -eq 0) { $Specs = @(Get-ChildItem "specs" -Filter "*.yaml" -File | Sort-Object Name | ForEach-Object { "specs/" + $_.Name }) }
if ($Specs.Count -eq 0) { Fallo "no hay ningún YAML en specs/: escribe uno por cada contexto que quieras generar." }
foreach ($s in $Specs) {
    Write-Host "-- $s"
    & $py src/specs.py $json $s
    if ($LASTEXITCODE -ne 0) { Fallo "$s no cumple con el modelo (ver arriba)." }
}

if ($SoloValidar) {
    Write-Host ""
    Write-Host "Listo: el modelo y los YAML están bien. No se generó nada (-SoloValidar)." -ForegroundColor Green
    exit 0
}

Paso 5 "Generar la solución C#"
& $py src/generar.py --puerto $Puerto $json $Salida @Specs
if ($LASTEXITCODE -ne 0) { Fallo "la generación falló (ver arriba)." }

Paso 6 "Compilar con .NET 8"
# Desde la carpeta de salida, para que dotnet use el global.json (SDK 8).
Push-Location $Salida
& $dotnet build -nologo
$codigo = $LASTEXITCODE
Pop-Location
if ($codigo -ne 0) { Fallo "la compilación falló (ver arriba)." }

Write-Host ""
Write-Host "Listo. Para correr la aplicación: ejecutar.ps1; para probar los escenarios: probar.ps1" -ForegroundColor Green
