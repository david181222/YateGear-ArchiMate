# Genera el proyecto C# de un contexto desde el modelo ArchiMate de YateGear.
# Pasos: entorno de Python, exportar con la ACLI de Archi, extraer, revisar el YAML, generar y compilar.
# Se detiene en el primer paso que falle y dice cuál.
#
# Uso (desde la carpeta generador):
#   powershell -ExecutionPolicy Bypass -File .\generar.ps1
#
# Este archivo va en UTF-8 con BOM: Windows PowerShell 5.1 lee sin BOM como ANSI.
param(
    [string]$Modelo = "..\modelo\YateGear.archimate",
    [string]$Contexto = "Contexto Gestión del arriendo",
    [string]$Specs = "specs\gestion-del-arriendo.yaml",
    [string]$Archi = "C:\Program Files\Archi\Archi.exe"
)

Set-Location $PSScriptRoot
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$py = ".\.venv\Scripts\python.exe"
$xml = Join-Path $PSScriptRoot "salida\intermedio\YateGear.xml"
$json = "salida\intermedio\modelo-ddd.json"

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
    py -3.13 -m venv .venv
    if ($LASTEXITCODE -ne 0) { Fallo "no se pudo crear el entorno virtual con 'py -3.13'. Instala Python 3.13." }
    & $py -m pip install --disable-pip-version-check -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Fallo "no se pudieron instalar las librerías de requirements.txt." }
} else {
    Write-Host "Ya existe .venv."
}

Paso 2 "Exportar el modelo al formato de intercambio con la ACLI de Archi"
if (-not (Test-Path $Modelo)) { Fallo "no existe el modelo $Modelo." }
if (-not (Test-Path $Archi)) { Fallo "no existe $Archi. Usa el parámetro -Archi con la ruta de Archi.exe." }
$modeloAbs = (Resolve-Path $Modelo).Path
# El "| Out-Host" hace que PowerShell espere a que Archi termine.
& $Archi -application com.archimatetool.commandline.app -consoleLog -nosplash -a --loadModel $modeloAbs --xmlexchange.export $xml | Out-Host
if ($LASTEXITCODE -ne 0) { Fallo "la ACLI de Archi terminó con código $LASTEXITCODE." }
if (-not (Test-Path $xml)) { Fallo "la ACLI no escribió $xml." }

Paso 3 "Extraer el contexto a modelo-ddd.json"
& $py src\extraer.py $xml $Contexto $json
if ($LASTEXITCODE -ne 0) { Fallo "la extracción encontró errores en el modelo (ver arriba)." }

Paso 4 "Revisar el YAML contra el modelo"
& $py src\specs.py $json $Specs
if ($LASTEXITCODE -ne 0) { Fallo "el YAML no cumple con el modelo (ver arriba)." }

Paso 5 "Generar el proyecto C#"
& $py src\generar.py $json $Specs salida
if ($LASTEXITCODE -ne 0) { Fallo "la generación falló (ver arriba)." }

Paso 6 "Compilar con .NET 8"
Push-Location salida
dotnet build -nologo
$codigo = $LASTEXITCODE
Pop-Location
if ($codigo -ne 0) { Fallo "la compilación falló (ver arriba)." }

Write-Host ""
# Se corre desde salida para que dotnet use el global.json (SDK 8).
Write-Host "Listo. Para correr la aplicación: cd salida; dotnet run --project GestionDelArriendo" -ForegroundColor Green
