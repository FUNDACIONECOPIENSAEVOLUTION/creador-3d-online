param([switch]$Demo)
$ErrorActionPreference = 'Stop'
$root = 'D:\programas creados\conector-blender-freecad'
$agent = Join-Path $root 'agent'
$base = 'https://raw.githubusercontent.com/FUNDACIONECOPIENSAEVOLUTION/creador-3d-online/68036b14a8783a6c9376cc5ca40f96f4d3b32732/direct'
$stage = Join-Path $agent ('update-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stage | Out-Null
try {
    foreach ($name in @('gallery_v062.py','reality_v062.py','architecture_v05.py','agent_v04.py')) {
        Invoke-WebRequest "$base/$name" -OutFile (Join-Path $stage $name)
    }
    & py -3 -m py_compile (Join-Path $stage 'gallery_v062.py') (Join-Path $stage 'reality_v062.py')
    if ($LASTEXITCODE -ne 0) { throw 'Error de sintaxis' }
    & py -3 (Join-Path $stage 'reality_v062.py') --selftest
    if ($LASTEXITCODE -ne 0) { throw 'Error en prueba UV' }
    foreach ($name in @('gallery_v062.py','reality_v062.py','architecture_v05.py','agent_v04.py')) {
        $target = Join-Path $agent $name
        if (Test-Path $target) { Copy-Item $target "$target.bak" -Force }
        Copy-Item (Join-Path $stage $name) $target -Force
    }
    $gallery = Join-Path $agent 'gallery.py'
    Copy-Item $gallery "$gallery.v061.bak" -Force
    Copy-Item (Join-Path $agent 'gallery_v062.py') $gallery -Force
} finally { Remove-Item -LiteralPath $stage -Recurse -Force }
Write-Host 'EcoBlend v0.6.2 instalado. Reinicie EcoBlend Direct Web para cargar el visor nuevo.' -ForegroundColor Green
if ($Demo) {
    $env:ECOBLEND_BLENDER = 'D:\amazonlibro\blender 3d\blender.exe'
    & py -3 (Join-Path $agent 'reality_v062.py') --demo --project job-a8uw3l46
    if ($LASTEXITCODE -ne 0) { throw 'Error de textura/exportacion. Revisar reality.log y reality_report.json.' }
}
