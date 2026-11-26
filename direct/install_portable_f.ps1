$ErrorActionPreference = 'Stop'
$root = 'F:\EcoBlend-Studio'
$old = 'D:\programas creados\conector-blender-freecad'
if (!(Test-Path 'F:\')) { throw 'Conecte el disco F:' }
if ((Get-PSDrive F).Free -lt 15GB) { throw 'Se requieren al menos 15 GB libres' }
foreach ($d in @('Software','Downloads','Engine','Engine\agent','Projects','Cache','Logs','Backups')) { New-Item -ItemType Directory -Force "$root\$d" | Out-Null }
$env:TEMP="$root\Cache"; $env:TMP=$env:TEMP
$ProgressPreference='SilentlyContinue'
function Download($url,$file) {
    if (!(Test-Path $file)) {
        Invoke-WebRequest -UseBasicParsing $url -OutFile "$file.partial"
        Move-Item "$file.partial" $file
    }
}
$bz="$root\Downloads\blender-4.5.17-windows-x64.zip"
Download 'https://download.blender.org/release/Blender4.5/blender-4.5.17-windows-x64.zip' $bz
if (!(Get-ChildItem "$root\Software\Blender" -Filter blender.exe -Recurse -ErrorAction SilentlyContinue)) {
    Expand-Archive $bz "$root\Software\Blender" -Force
}
$blender = Get-ChildItem "$root\Software\Blender" -Filter blender.exe -Recurse | Select-Object -First 1
New-Item -ItemType Directory -Force (Join-Path $blender.DirectoryName 'portable') | Out-Null
& $blender.FullName --background --factory-startup --version
if ($LASTEXITCODE -ne 0) { throw 'Blender no supera prueba de version' }
$release=Invoke-RestMethod 'https://api.github.com/repos/FreeCAD/FreeCAD/releases/latest'
$asset=$release.assets | Where-Object { $_.name -match '(?i)windows.*x86[_-]64.*\.7z$|win.*x64.*\.7z$' } | Select-Object -First 1
if (!$asset) { throw 'No se encontro un paquete portable estable de FreeCAD. Consulte releases oficiales.' }
$fz=Join-Path "$root\Downloads" $asset.name
Download $asset.browser_download_url $fz
if (!(Get-ChildItem "$root\Software\FreeCAD" -Filter FreeCADCmd.exe -Recurse -ErrorAction SilentlyContinue)) {
    New-Item -ItemType Directory -Force "$root\Software\FreeCAD" | Out-Null
    & tar.exe -xf $fz -C "$root\Software\FreeCAD"
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo extraer FreeCAD con tar.exe; extraiga el .7z con 7-Zip y reintente.' }
}
$fc=Get-ChildItem "$root\Software\FreeCAD" -Filter FreeCADCmd.exe -Recurse | Select-Object -First 1
if (!$fc) { throw 'FreeCADCmd no encontrado' }
$base='https://raw.githubusercontent.com/FUNDACIONECOPIENSAEVOLUTION/creador-3d-online/94e9a54f275817d6488b213a9e6372908dd7d627/direct'
$agent="$root\Engine\agent"
foreach ($name in @('agent.py','agent_v04.py','panel_v031.py','gallery_v093.py','architecture_plus_v092.py','reality_v092.py','reality_painter_v092.py','painter_panel_v092.py','storage_v094.py','studio_launcher_portable.py','test_studio_v092.py')) {
    Invoke-WebRequest -UseBasicParsing "$base/$name" -OutFile "$agent\$name"
}
$python="$root\Engine\venv\Scripts\python.exe"
if (!(Test-Path $python)) {
    py -3 -m venv "$root\Engine\venv"
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear entorno Python' }
}
& $python -m pip install --no-cache-dir Pillow==12.1.1
if ($LASTEXITCODE -ne 0) { throw 'Pillow no instalado' }
& $python "$agent\storage_v094.py" --init $root
if ($LASTEXITCODE -ne 0) { throw 'Error almacenamiento' }
if (Test-Path "$old\projects") {
    & robocopy "$old\projects" "$root\Projects" /E /XC /XN /XO /XJ /R:1 /W:1
    if ($LASTEXITCODE -ge 8) { throw 'Error al copiar proyectos' }
}
$env:ECOBLEND_PROJECTS="$root\Projects"
$env:ECOBLEND_BLENDER=$blender.FullName
$env:ECOBLEND_FREECAD=$fc.FullName
& $python "$agent\test_studio_v092.py"
if ($LASTEXITCODE -ne 0) { throw 'Prueba integral no superada; conserve instalaciones anteriores' }
$bat="$root\EcoBlend-Studio.bat"
@'
@echo off
cd /d "F:\EcoBlend-Studio\Engine\agent"
"F:\EcoBlend-Studio\Engine\venv\Scripts\python.exe" studio_launcher_portable.py
pause
'@ | Set-Content $bat -Encoding ASCII
$shell=New-Object -ComObject WScript.Shell
$link=$shell.CreateShortcut(([Environment]::GetFolderPath('Desktop')+'\EcoBlend Studio F.lnk'))
$link.TargetPath=$bat
$link.WorkingDirectory=$root
$link.Save()
Write-Host 'ECOBLEND PORTABLE: prueba integral superada. Cierre los servidores anteriores antes de abrir el acceso directo.' -ForegroundColor Green
