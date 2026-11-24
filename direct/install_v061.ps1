param([switch]$Demo)
$ErrorActionPreference = 'Stop'
$root = 'D:\programas creados\conector-blender-freecad'
$agent = Join-Path $root 'agent'
$base = 'https://raw.githubusercontent.com/FUNDACIONECOPIENSAEVOLUTION/creador-3d-online/81646768217e0eacc5fe62455a161eeddd5f6e67/direct'
$stage = Join-Path $agent ('update-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stage | Out-Null
try {
    foreach ($name in @('reality_v061.py','gallery_v061.py','architecture_v05.py','agent_v04.py')) {
        Invoke-WebRequest "$base/$name" -OutFile (Join-Path $stage $name)
    }
    & py -3 -m py_compile (Join-Path $stage 'reality_v061.py') (Join-Path $stage 'gallery_v061.py')
    if ($LASTEXITCODE -ne 0) { throw 'Error de sintaxis' }
    & py -3 (Join-Path $stage 'reality_v061.py') --selftest
    if ($LASTEXITCODE -ne 0) { throw 'Error de prueba UV' }
    foreach ($name in @('reality_v061.py','gallery_v061.py')) {
        Copy-Item (Join-Path $stage $name) (Join-Path $agent $name) -Force
    }
    if (Test-Path (Join-Path $agent 'gallery.py')) { Copy-Item (Join-Path $agent 'gallery.py') (Join-Path $agent 'gallery_pre061.py') -Force }
    Copy-Item (Join-Path $agent 'gallery_v061.py') (Join-Path $agent 'gallery.py') -Force
} finally { Remove-Item -LiteralPath $stage -Recurse -Force }
Write-Host 'EcoBlend v0.6.1 instalado. Reinicie el visor para cargar la nueva interfaz.' -ForegroundColor Green
if ($Demo) {
    $env:ECOBLEND_BLENDER = 'D:\amazonlibro\blender 3d\blender.exe'
    & py -3 (Join-Path $agent 'reality_v061.py') --demo
    if ($LASTEXITCODE -ne 0) { throw 'Prueba no validada. Revisar reality.log y reality_report.json.' }
}
