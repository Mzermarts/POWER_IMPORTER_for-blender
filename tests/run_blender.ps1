param([string]$Blender = 'C:\Program Files\Blender Foundation\Blender 5.0\blender.exe', [string]$Script = 'blender_smoke.py')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$isolationRoot = Join-Path $projectRoot ('test-artifacts\profile-' + [guid]::NewGuid().ToString('N'))
$settings = @{
    BLENDER_USER_RESOURCES = $isolationRoot
    BLENDER_USER_CONFIG = (Join-Path $isolationRoot 'config')
    BLENDER_USER_SCRIPTS = (Join-Path $isolationRoot 'scripts')
    BLENDER_USER_EXTENSIONS = (Join-Path $isolationRoot 'extensions')
    BLENDER_USER_DATAFILES = (Join-Path $isolationRoot 'datafiles')
}
$prior = @{}
try {
    foreach ($key in $settings.Keys) {
        $prior[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
        New-Item -ItemType Directory -Path $settings[$key] -Force | Out-Null
        [Environment]::SetEnvironmentVariable($key, $settings[$key], 'Process')
    }
    & $Blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python (Join-Path $PSScriptRoot $Script)
    if ($LASTEXITCODE -ne 0) { throw "Blender test failed: $LASTEXITCODE" }
} finally {
    foreach ($key in $prior.Keys) {
        [Environment]::SetEnvironmentVariable($key, $prior[$key], 'Process')
    }
}
