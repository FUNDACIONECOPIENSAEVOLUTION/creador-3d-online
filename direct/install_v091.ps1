param([switch]$Demo)
$ErrorActionPreference = 'Stop'
$root = 'D:\programas creados\conector-blender-freecad'
$agent = Join-Path $root 'agent'
$base = 'https://raw.githubusercontent.com/FUNDACIONECOPIENSAEVOLUTION/creador-3d-online/4398ef3ca5bc100f9197599382fe7e4a556000f4/direct'
$stage = Join-Path $agent ('update-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stage | Out-Null
try {
    $files = @('architecture_plus_v091.py','reality_v091.py','reality_painter_v091.py','painter_panel_v091.py','test_studio_v091.py','agent_v04.py')
    foreach ($name in $files) { Invoke-WebRequest "$base/$name" -OutFile (Join-Path $stage $name) }
    $python = "$root\painter-env\Scripts\python.exe"
    if (!(Test-Path $python)) { throw 'Instale primero el entorno Painter v0.7' }
    foreach ($name in $files) {
        & $python -m py_compile (Join-Path $stage $name)
        if ($LASTEXITCODE -ne 0) { throw "Error de sintaxis: $name" }
    }
    foreach ($name in @('architecture_plus_v091.py','reality_v091.py','reality_painter_v091.py')) {
        & $python (Join-Path $stage $name) --selftest
        if ($LASTEXITCODE -ne 0) { throw "Error en prueba: $name" }
    }
    foreach ($name in $files) {
        $target = Join-Path $agent $name
        if (Test-Path $target) { Copy-Item $target "$target.bak" -Force }
        Copy-Item (Join-Path $stage $name) $target -Force
    }
} finally { Remove-Item -LiteralPath $stage -Recurse -Force }
$env:ECOBLEND_BLENDER = 'D:\amazonlibro\blender 3d\blender.exe'
$env:ECOBLEND_FREECAD = 'D:\freecad\programa instalado\bin\freecadcmd.exe'
if ($Demo) {
    & $python (Join-Path $agent 'test_studio_v091.py')
    if ($LASTEXITCODE -ne 0) { throw 'Error de prueba integral. Conserve los registros.' }
}
Write-Host 'EcoBlend 0.9.1: pruebas solicitadas superadas.' -ForegroundColor Green
