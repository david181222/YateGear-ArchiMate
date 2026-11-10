# Verifica que el generador y lo generado están bien, con un solo comando. En orden:
#   1. generar.ps1: exporta, extrae, revisa los YAML (y los contratos entre contextos), genera y compila sin
#      advertencias (las advertencias son errores de compilación).
#   2. Determinismo: generar.ps1 otra vez y la misma huella de la carpeta de salida.
#   3. Trazabilidad completa: cada elemento de los contextos generados está en su CSV.
#   4. Pruebas del validador: cada copia rota a propósito de un YAML da el error esperado (pruebas-validador/casos.yaml).
#   5. Código a mano completo: ningún archivo manual conserva un valor provisional del generador (PENDIENTE).
#   6. probar.ps1: la documentación de la API (OpenAPI y Swagger), los escenarios de cada contexto y los de punta
#      a punta, sin errores en el bus.
# Al final muestra una tabla con cada revisión y termina con código 1 si alguna falla.
#
# Uso (desde la carpeta generador):
#   powershell -ExecutionPolicy Bypass -File .\verificar.ps1     (Windows)
#   pwsh ./verificar.ps1                                          (Linux)
#   ... -Modelo, -Specs, -Archi y -Salida pasan a generar.ps1 y probar.ps1; -Puerto, solo a probar.ps1 (el puerto de
#       las pruebas; el de lo generado se elige con generar.ps1 -Puerto).
#   ... -SinPruebasDelValidador   (por ejemplo, con el modelo de ejemplo: los casos son de los YAML de specs/)
#
# Este archivo va en UTF-8 con BOM: Windows PowerShell 5.1 lee sin BOM como ANSI.
param(
    [string]$Modelo = "",
    [string[]]$Specs = @(),
    [string]$Archi = "",
    [string]$Salida = "salida",
    [int]$Puerto = 0,
    [switch]$SinPruebasDelValidador
)
$casos = "pruebas-validador/casos.yaml"

Set-Location $PSScriptRoot
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$enWindows = [System.Environment]::OSVersion.Platform -eq "Win32NT"
$py = if ($enWindows) { "./.venv/Scripts/python.exe" } else { "./.venv/bin/python" }
$shell = (Get-Process -Id $PID).Path                  # el mismo PowerShell que corre este script
$resultados = @()

function Revision([string]$nombre, [bool]$ok, [string]$detalle) {
    $script:resultados += [pscustomobject]@{ Revision = $nombre; Resultado = $(if ($ok) { "✓" } else { "✗" }); Detalle = $detalle }
    $color = if ($ok) { "Green" } else { "Red" }
    Write-Host ""
    Write-Host "== $(if ($ok) { '✓' } else { '✗' }) $nombre. $detalle" -ForegroundColor $color
}

function Generar {
    $argumentos = @("-ExecutionPolicy", "Bypass", "-File", "./generar.ps1", "-Salida", $Salida)
    if ($Modelo) { $argumentos += @("-Modelo", $Modelo) }
    if ($Specs.Count -gt 0) { $argumentos += @("-Specs", ($Specs -join ",")) }
    if ($Archi) { $argumentos += @("-Archi", $Archi) }
    & $shell @argumentos | Out-Host
    return $LASTEXITCODE -eq 0
}

function Huella {
    $linea = & $py src/herramientas/huella.py $Salida
    return ($linea -split "\s+")[2]
}

# 1. Generar y compilar.
$ok = Generar
Revision "Generar y compilar sin advertencias" $ok $(if ($ok) { "generar.ps1 terminó bien." } else { "generar.ps1 falló (ver arriba)." })
if (-not $ok) {
    $resultados | Format-Table -AutoSize | Out-Host
    exit 1
}

# 2. Determinismo: dos generaciones seguidas dan la misma huella.
$h1 = Huella
$ok = Generar
$h2 = Huella
$ok = $ok -and $h1 -eq $h2
Revision "Determinismo" $ok $(if ($ok) { "La misma huella en dos generaciones seguidas: $($h1.Substring(0, 12))..." } else { "Huellas distintas: $h1 y $h2." })

# 3. Trazabilidad.
& $py src/herramientas/revisar_trazabilidad.py "$Salida/intermedio/modelo-ddd.json" $Salida | Out-Host
$ok = $LASTEXITCODE -eq 0
Revision "Trazabilidad completa" $ok $(if ($ok) { "Todos los elementos de los contextos generados tienen su fila." } else { "Faltan filas o archivos (ver arriba)." })

# 4. Pruebas del validador.
if (-not $SinPruebasDelValidador) {
    & $py src/herramientas/probar_validador.py "$Salida/intermedio/modelo-ddd.json" $casos | Out-Host
    $ok = $LASTEXITCODE -eq 0
    Revision "Pruebas del validador" $ok $(if ($ok) { "specs.py detecta cada copia rota de $casos." } else { "Algún caso no da el error esperado (ver arriba)." })
}

# 5. Código a mano completo: el generador marca con PENDIENTE cada valor provisional que deja en un archivo manual
# (un dato calculado, un filtro o las raíces de un comando sobre todas). Si queda alguno, la aplicación responde con
# ese valor provisional y un escenario que no lo afirme no lo nota.
$pendientes = @(Get-ChildItem $Salida -Recurse -Filter "*.cs" -File |
    Where-Object { $_.Name -notlike "*.g.cs" -and $_.FullName -notmatch "[\\/](bin|obj)[\\/]" } |
    Select-String -Pattern "PENDIENTE" -SimpleMatch)
foreach ($x in $pendientes) { Write-Host "  PENDIENTE en $($x.Filename), línea $($x.LineNumber): $($x.Line.Trim())" -ForegroundColor Yellow }
$ok = $pendientes.Count -eq 0
Revision "Código a mano completo" $ok $(if ($ok) { "Ningún archivo manual tiene un valor provisional (PENDIENTE)." } else { "$($pendientes.Count) valor(es) provisional(es) por escribir a mano (ver arriba)." })

# 6. Escenarios.
$argumentos = @("-ExecutionPolicy", "Bypass", "-File", "./probar.ps1", "-Salida", $Salida)
if ($Puerto) { $argumentos += @("-Puerto", $Puerto) }
& $shell @argumentos | Out-Host
$ok = $LASTEXITCODE -eq 0
Revision "API y escenarios" $ok $(if ($ok) { "Swagger responde, todos los pasos en verde y ningún error en el bus." } else { "Algún paso falló (ver arriba)." })

Write-Host ""
$resultados | Format-Table -AutoSize | Out-Host
if ($resultados | Where-Object { $_.Resultado -eq "✗" }) {
    Write-Host "Hay revisiones con falla." -ForegroundColor Red
    exit 1
}
Write-Host "Todo bien." -ForegroundColor Green
exit 0
