param([switch]$Demo)
$ErrorActionPreference = 'Stop'
$root = 'D:\programas creados\conector-blender-freecad'
$agent = Join-Path $root 'agent'
New-Item -ItemType Directory -Force -Path $agent | Out-Null
$base = 'https://raw.githubusercontent.com/FUNDACIONECOPIENSAEVOLUTION/creador-3d-online/0bf3fb169b9af54af85682e2ba90227767f1dc90/direct'
$stage = Join-Path $agent ('update-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stage | Out-Null
try {
    foreach ($name in @('architecture_v05.py','agent_v04.py','STUDIO_SKILLS.md')) {
        Invoke-WebRequest "$base/$name" -OutFile (Join-Path $stage $name)
    }
    & py -3 -m py_compile (Join-Path $stage 'architecture_v05.py') (Join-Path $stage 'agent_v04.py')
    if ($LASTEXITCODE -ne 0) { throw 'Error de sintaxis' }
    & py -3 (Join-Path $stage 'architecture_v05.py') --selftest
    if ($LASTEXITCODE -ne 0) { throw 'Error en validacion geometrica' }
    foreach ($name in @('architecture_v05.py','agent_v04.py','STUDIO_SKILLS.md')) {
        $target = Join-Path $agent $name
        if (Test-Path $target) { Copy-Item $target "$target.bak" -Force }
        Copy-Item (Join-Path $stage $name) $target -Force
    }
} finally {
    Remove-Item -LiteralPath $stage -Recurse -Force
}
Write-Host 'EcoBlend Architecture v0.5 instalado; prueba geometrica correcta.' -ForegroundColor Green
if ($Demo) {
    $env:ECOBLEND_BLENDER = 'D:\amazonlibro\blender 3d\blender.exe'
    $env:ECOBLEND_FREECAD = 'D:\freecad\programa instalado\bin\freecadcmd.exe'
    & py -3 (Join-Path $agent 'architecture_v05.py') --demo --engine both
    if ($LASTEXITCODE -ne 0) { throw 'Error de motor; consultar registros' }
    Start-Process 'http://127.0.0.1:8788/'
}
