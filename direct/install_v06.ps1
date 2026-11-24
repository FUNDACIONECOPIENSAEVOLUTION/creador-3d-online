param([switch]$Demo)
$ErrorActionPreference = 'Stop'
$root = 'D:\programas creados\conector-blender-freecad'
$agent = Join-Path $root 'agent'
$base = 'https://raw.githubusercontent.com/FUNDACIONECOPIENSAEVOLUTION/creador-3d-online/82d786aa350a8b49e6c228e7ccc30cba61b509a5/direct'
$stage = Join-Path $agent ('update-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stage | Out-Null
try {
    foreach ($name in @('reality_v06.py','architecture_v05.py','agent_v04.py')) {
        Invoke-WebRequest "$base/$name" -OutFile (Join-Path $stage $name)
    }
    & py -3 -m py_compile (Join-Path $stage 'reality_v06.py') (Join-Path $stage 'architecture_v05.py') (Join-Path $stage 'agent_v04.py')
    if ($LASTEXITCODE -ne 0) { throw 'Error de sintaxis' }
    & py -3 (Join-Path $stage 'reality_v06.py') --selftest
    if ($LASTEXITCODE -ne 0) { throw 'Error de prueba UV/materiales' }
    foreach ($name in @('reality_v06.py','architecture_v05.py','agent_v04.py')) {
        $target = Join-Path $agent $name
        if (Test-Path $target) { Copy-Item $target "$target.bak" -Force }
        Copy-Item (Join-Path $stage $name) $target -Force
    }
} finally { Remove-Item -LiteralPath $stage -Recurse -Force }
Write-Host 'EcoBlend Reality v0.6 instalado; pruebas de datos correctas.' -ForegroundColor Green
if ($Demo) {
    $env:ECOBLEND_BLENDER = 'D:\amazonlibro\blender 3d\blender.exe'
    & py -3 (Join-Path $agent 'reality_v06.py') --demo
    if ($LASTEXITCODE -ne 0) { throw 'Error de Blender; consultar reality.log' }
    Start-Process 'http://127.0.0.1:8788/'
}
