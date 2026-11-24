$ErrorActionPreference = 'Stop'
$root = 'D:\programas creados\conector-blender-freecad'
$agent = Join-Path $root 'agent'
$base = 'https://raw.githubusercontent.com/FUNDACIONECOPIENSAEVOLUTION/creador-3d-online/b4508d8ddd714a2a6c5e6c3cf044a44fd9a65ea8/direct'
$stage = Join-Path $agent ('update-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stage | Out-Null
try {
    $files = @('reality_painter_v07.py','painter_panel_v07.py','reality_v062.py','architecture_v05.py','agent_v04.py')
    foreach ($name in $files) { Invoke-WebRequest "$base/$name" -OutFile (Join-Path $stage $name) }
    $venv = Join-Path $root 'painter-env'
    if (!(Test-Path "$venv\Scripts\python.exe")) {
        py -3 -m venv $venv
        if ($LASTEXITCODE -ne 0) { throw 'Error creando entorno' }
    }
    $python = "$venv\Scripts\python.exe"
    & $python -m pip install 'Pillow==12.1.1'
    if ($LASTEXITCODE -ne 0) { throw 'Error instalando Pillow' }
    foreach ($name in $files) {
        & $python -m py_compile (Join-Path $stage $name)
        if ($LASTEXITCODE -ne 0) { throw "Error de sintaxis: $name" }
    }
    & $python (Join-Path $stage 'reality_painter_v07.py') --selftest
    if ($LASTEXITCODE -ne 0) { throw 'Error de rectificacion' }
    & $python (Join-Path $stage 'reality_v062.py') --selftest
    if ($LASTEXITCODE -ne 0) { throw 'Error de UV' }
    foreach ($name in $files) {
        $target = Join-Path $agent $name
        if (Test-Path $target) { Copy-Item $target "$target.v07.bak" -Force }
        Copy-Item (Join-Path $stage $name) $target -Force
    }
    $launcher = Join-Path $root 'EcoBlend-Painter.bat'
    @'
@echo off
cd /d "D:\programas creados\conector-blender-freecad\agent"
set "ECOBLEND_BLENDER=D:\amazonlibro\blender 3d\blender.exe"
"D:\programas creados\conector-blender-freecad\painter-env\Scripts\python.exe" painter_panel_v07.py
pause
'@ | Set-Content $launcher -Encoding ASCII
    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut(([Environment]::GetFolderPath('Desktop')+'\EcoBlend Reality Painter.lnk'))
    $link.TargetPath = $launcher
    $link.WorkingDirectory = $root
    $link.Save()
    Write-Host 'Reality Painter instalado. Pruebas locales superadas.' -ForegroundColor Green
    Start-Process $launcher
} finally { Remove-Item -LiteralPath $stage -Recurse -Force }
