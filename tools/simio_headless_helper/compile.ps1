param(
    [string]$OutputDir = ".tmp\simio-headless-helper"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$outputPath = Join-Path $repoRoot $OutputDir
New-Item -ItemType Directory -Force -Path $outputPath | Out-Null

$roslynBase = "C:\Program Files\PowerShell\7"
Add-Type -Path (Join-Path $roslynBase "Microsoft.CodeAnalysis.dll")
Add-Type -Path (Join-Path $roslynBase "Microsoft.CodeAnalysis.CSharp.dll")

$sourcePath = Join-Path $PSScriptRoot "Program.cs"
$sourceText = [System.IO.File]::ReadAllText($sourcePath)
$syntaxTree = [Microsoft.CodeAnalysis.CSharp.CSharpSyntaxTree]::ParseText($sourceText)

$runtimeDir = "C:\Program Files\dotnet\shared\Microsoft.NETCore.App\10.0.9"
if (-not (Test-Path -LiteralPath $runtimeDir)) {
    throw "The .NET 10 runtime directory was not found: $runtimeDir"
}

$referenceNames = @(
    "System.Private.CoreLib.dll",
    "System.Runtime.dll",
    "System.Console.dll",
    "System.Collections.dll",
    "System.Linq.dll",
    "System.Reflection.dll",
    "System.IO.Compression.dll",
    "System.IO.Compression.ZipFile.dll",
    "System.Runtime.Loader.dll",
    "System.Text.Json.dll",
    "System.Private.Uri.dll",
    "netstandard.dll"
)
$references = foreach ($name in $referenceNames) {
    [Microsoft.CodeAnalysis.MetadataReference]::CreateFromFile((Join-Path $runtimeDir $name))
}

$compilation = [Microsoft.CodeAnalysis.CSharp.CSharpCompilation]::Create(
    "SimioHeadlessHelper",
    [Microsoft.CodeAnalysis.SyntaxTree[]]@($syntaxTree),
    [Microsoft.CodeAnalysis.MetadataReference[]]$references,
    [Microsoft.CodeAnalysis.CSharp.CSharpCompilationOptions]::new(
        [Microsoft.CodeAnalysis.OutputKind]::ConsoleApplication
    )
)

$dllPath = Join-Path $outputPath "SimioHeadlessHelper.dll"
$stream = [System.IO.File]::Open($dllPath, [System.IO.FileMode]::Create)
try {
    $emit = $compilation.Emit($stream)
}
finally {
    $stream.Dispose()
}
if (-not $emit.Success) {
    $messages = $emit.Diagnostics | ForEach-Object { $_.ToString() }
    throw ($messages -join [Environment]::NewLine)
}

$runtimeConfig = @{
    runtimeOptions = @{
        tfm = "net10.0"
        framework = @{
            name = "Microsoft.NETCore.App"
            version = "10.0.9"
        }
    }
} | ConvertTo-Json -Depth 5
Set-Content -LiteralPath (Join-Path $outputPath "SimioHeadlessHelper.runtimeconfig.json") -Value $runtimeConfig -Encoding UTF8

[pscustomobject]@{
    Status = "Compiled"
    HelperPath = $dllPath
    RuntimeConfigPath = Join-Path $outputPath "SimioHeadlessHelper.runtimeconfig.json"
} | ConvertTo-Json -Compress
