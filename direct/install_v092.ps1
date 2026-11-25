param([switch]$Demo)
$ErrorActionPreference = 'Stop'
$root = 'D:\programas creados\conector-blender-freecad'
$agent = Join-Path $root 'agent'
$python = "$root\painter-env\Scripts\python.exe"
if (!(Test-Path $python)) { throw 'Falta el entorno Painter previamente instalado.' }
$base = 'https://raw.githubusercontent.com/FUNDACIONECOPIENSAEVOLUTION/creador-3d-online/a075c36281fd0243210da873f2a5b2250d6783b7/direct'
$stage = Join-Path $agent ('update-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stage | Out-Null
try {
    $files = @('architecture_plus_v092.py','reality_v092.py','reality_painter_v092.py','painter_panel_v092.py','gallery_v092.py','studio_launcher_v092.py','test_studio_v092.py','agent_v04.py','panel_v031.py','agent.py')
    foreach ($name in $files) {
        Invoke-WebRequest "$base/$name" -OutFile (Join-Path $stage $name)
        & $python -m py_compile (Join-Path $stage $name)
        if ($LASTEXITCODE -ne 0) { throw "Error de sintaxis: $name" }
    }
    foreach ($name in @('architecture_plus_v092.py','reality_v092.py','reality_painter_v092.py')) {
        & $python (Join-Path $stage $name) --selftest
        if ($LASTEXITCODE -ne 0) { throw "Error en prueba: $name" }
    }
    foreach ($name in $files) {
        $target = Join-Path $agent $name
        if (Test-Path $target) { Copy-Item $target "$target.v092.bak" -Force }
        Copy-Item (Join-Path $stage $name) $target -Force
    }
} finally { Remove-Item -LiteralPath $stage -Recurse -Force }
$env:ECOBLEND_BLENDER = 'D:\amazonlibro\blender 3d\blender.exe'
$env:ECOBLEND_FREECAD = 'D:\freecad\programa instalado\bin\freecadcmd.exe'
if ($Demo) {
    & $python (Join-Path $agent 'test_studio_v092.py')
    if ($LASTEXITCODE -ne 0) { throw 'Prueba integral no superada. Consulte los registros.' }
}
$launcher = Join-Path $root 'EcoBlend-Studio-v092.bat'
@'
@echo off
cd /d "D:\programas creados\conector-blender-freecad\agent"
"D:\programas creados\conector-blender-freecad\painter-env\Scripts\python.exe" studio_launcher_v092.py
pause
'@ | Set-Content $launcher -Encoding ASCII
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut(([Environment]::GetFolderPath('Desktop')+'\EcoBlend Studio.lnk'))
$link.TargetPath = $launcher
$link.WorkingDirectory = $root
$link.Save()
Write-Host 'EcoBlend 0.9.2 instalado. Cierre servidores anteriores y abra EcoBlend Studio desde el escritorio.' -ForegroundColor Green
