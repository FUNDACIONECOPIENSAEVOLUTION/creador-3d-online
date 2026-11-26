$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$agent=Join-Path $root 'Engine\agent'
$python=Join-Path $root 'Software\Python\WPy64-313150\python\python.exe'
if (!(Test-Path $python)) { throw 'Python portable no encontrado' }
$env:TEMP=Join-Path $root 'Cache'; $env:TMP=$env:TEMP
$base='https://raw.githubusercontent.com/FUNDACIONECOPIENSAEVOLUTION/creador-3d-online/6fd79652cff43fdb93a52f7cc2643b4f7867c820/direct'
$vendor=Join-Path $root 'Engine\vendor\three'
$stage=Join-Path $root ('Cache\three-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force $stage | Out-Null
try {
    $archive=Join-Path $stage 'three.tgz'
    Invoke-WebRequest -UseBasicParsing 'https://registry.npmjs.org/three/-/three-0.160.0.tgz' -OutFile $archive
    & $python -c "import tarfile,sys; a=tarfile.open(sys.argv[1]); a.extractall(sys.argv[2],filter='data'); a.close()" $archive $stage
    if ($LASTEXITCODE -ne 0) { throw 'Error extrayendo Three.js' }
    foreach ($file in @('build\three.module.js','examples\jsm\controls\OrbitControls.js','examples\jsm\loaders\GLTFLoader.js','examples\jsm\utils\BufferGeometryUtils.js','LICENSE')) {
        if (!(Test-Path (Join-Path "$stage\package" $file))) { throw "Falta $file" }
    }
    foreach ($file in @('gallery_v096.py','studio_launcher_portable_v096.py')) {
        Invoke-WebRequest -UseBasicParsing "$base/$file" -OutFile "$stage\$file"
        & $python -W error::SyntaxWarning -m py_compile "$stage\$file"
        if ($LASTEXITCODE -ne 0) { throw "Error de sintaxis $file" }
    }
    New-Item -ItemType Directory -Force $vendor | Out-Null
    Copy-Item "$stage\package\build","$stage\package\examples","$stage\package\LICENSE" $vendor -Recurse -Force
    Copy-Item "$stage\gallery_v096.py","$stage\studio_launcher_portable_v096.py" $agent -Force
    Copy-Item "$root\EcoBlend-Studio.bat" "$root\Backups\EcoBlend-Studio-v095.bat" -Force
    $bat=Get-Content "$root\EcoBlend-Studio.bat" -Raw
    $bat.Replace('studio_launcher_portable_v095.py','studio_launcher_portable_v096.py') | Set-Content "$root\EcoBlend-Studio.bat" -Encoding ASCII
    Write-Host 'EcoBlend 0.9.6 preparado. Reinicie el lanzador para probar el visor local.' -ForegroundColor Green
} finally { Remove-Item -LiteralPath $stage -Recurse -Force }
