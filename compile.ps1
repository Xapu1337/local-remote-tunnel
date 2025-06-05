$files = Get-ChildItem -Recurse -Filter *.py | ForEach-Object { $_.FullName }
python -m py_compile $files
