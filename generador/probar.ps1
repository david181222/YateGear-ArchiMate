# Prueba los escenarios de los YAML contra la aplicación generada.
# Compila y, por cada contexto con escenarios (salida/contextos.json dice cuáles hay y dónde están) y para los
# escenarios entre contextos (S4), levanta el host desde salida/ (SDK 8 del global.json), ejecuta sus escenarios,
# marca cada paso con ✓ o ✗ y detiene la aplicación. Cada grupo corre con la aplicación recién levantada: con la
# integración (G12) un evento de un contexto llega a los demás, y así los escenarios de uno no cambian los de otro.
# Termina con código 1 si algún paso falla.
#
# Uso (desde la carpeta generador, después de generar.ps1):
#   powershell -ExecutionPolicy Bypass -File .\probar.ps1                  (Windows)
#   pwsh ./probar.ps1                                                       (Linux)
#   ... -Contexto "Contexto Calificaciones"   (solo ese contexto; también vale el nombre del proyecto)
#   ... -Contexto "entre contextos"           (solo los escenarios de punta a punta entre contextos)
#   ... -Puerto 5090                          (si el puerto está ocupado)
#
# Este archivo va en UTF-8 con BOM: Windows PowerShell 5.1 lee sin BOM como ANSI.
param(
    [string]$Contexto = "",
    [int]$Puerto = 0
)

Set-Location $PSScriptRoot
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
# Windows: .venv\Scripts y el dotnet del PATH. Linux: .venv/bin y, si existe, el SDK de ~/.dotnet.
$enWindows = [System.Environment]::OSVersion.Platform -eq "Win32NT"
$py = if ($enWindows) { "./.venv/Scripts/python.exe" } else { "./.venv/bin/python" }
$dotnet = "dotnet"
if (-not $enWindows -and (Test-Path "$HOME/.dotnet/dotnet")) { $dotnet = "$HOME/.dotnet/dotnet"; $env:DOTNET_ROOT = "$HOME/.dotnet" }
$manifiesto = "salida/contextos.json"
$entreContextos = "entre contextos"

function Fallo([string]$texto) {
    Write-Host "ERROR: $texto" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $manifiesto)) { Fallo "no existe $manifiesto. Ejecuta primero generar.ps1." }
if (-not (Test-Path $py)) { Fallo "no existe .venv. Ejecuta primero generar.ps1." }
$solucion = Get-Content $manifiesto -Raw -Encoding UTF8 | ConvertFrom-Json
$proyecto = $solucion.host
$soloEntre = $Contexto -eq $entreContextos
$contextos = @($solucion.contextos | Where-Object { -not $soloEntre -and (-not $Contexto -or $_.nombre -eq $Contexto -or $_.proyecto -eq $Contexto) })
if ($contextos.Count -eq 0 -and -not $soloEntre) {
    Fallo "no hay ningún contexto generado que se llame ""$Contexto"". Están: $(($solucion.contextos | ForEach-Object { $_.nombre }) -join ', '), y ""$entreContextos""."
}
# Los grupos de escenarios: uno por contexto y, sin -Contexto (o con -Contexto "entre contextos"), los de punta a punta.
$grupos = @()
foreach ($c in $contextos) {
    if ($c.escenarios) { $grupos += [pscustomobject]@{ Nombre = $c.nombre; Escenarios = $c.escenarios } }
    else { Write-Host "AVISO: $($c.nombre) no tiene escenarios en su YAML; no se prueba." -ForegroundColor Yellow }
}
if ((-not $Contexto -or $soloEntre) -and $solucion.entre_contextos) {
    $grupos += [pscustomobject]@{ Nombre = "los escenarios entre contextos"; Escenarios = $solucion.entre_contextos }
}
if ($grupos.Count -eq 0) { Fallo "no hay escenarios que probar." }
if ($Puerto -eq 0) { $Puerto = $solucion.puerto }
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

function Detener($app) {
    # Se busca por la ruta del ejecutable y no por el nombre: en Linux el nombre se corta a 15 caracteres.
    $dentro = Join-Path $salidaAbs "*"
    Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -like $dentro } | Stop-Process -Force
    if ($app) { Stop-Process -Id $app.Id -Force -ErrorAction SilentlyContinue }
    # Espera a que el puerto quede libre antes de levantar la siguiente.
    for ($i = 0; $i -lt 40; $i++) {
        try {
            $l = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $Puerto)
            $l.Start()
            $l.Stop()
            return
        } catch {
            Start-Sleep -Milliseconds 250
        }
    }
}

$codigo = 0
foreach ($g in $grupos) {
    Write-Host ""
    Write-Host "== Levantar la aplicación en $url para $($g.Nombre)"
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
    try {
        $lista = $false
        for ($i = 0; $i -lt 60 -and -not $lista; $i++) {
            Start-Sleep -Milliseconds 500
            try {
                Invoke-WebRequest -UseBasicParsing "$url/contextos" -TimeoutSec 2 | Out-Null
                $lista = $true
            } catch {}
        }
        if (-not $lista) {
            Write-Host "ERROR: la aplicación no respondió en 30 segundos." -ForegroundColor Red
            $codigo = 1
        } else {
            Write-Host "== Escenarios de $($g.Nombre)"
            & $py src/probar.py (Join-Path "salida" $g.Escenarios) $url
            if ($LASTEXITCODE -ne 0) { $codigo = 1 }
        }
    } finally {
        Detener $app
    }
}
Write-Host ""
Write-Host "== Aplicación detenida"
exit $codigo
