![Banner](banner.png)

# codeintel-Unused-Import-Remover
Removes unused import statements from Python code to reduce code clutter and improve readability. - Focused on Tools for static code analysis, vulnerability scanning, and code quality assurance

## Install
`git clone https://github.com/ShadowGuardAI/codeintel-unused-import-remover`

## Usage
`./codeintel-unused-import-remover [params]`

## Parameters
- `-h`: Show help message and exit
- `--dry-run`: Perform a dry run without modifying the file.
- `--aggressive`: No description provided

## How a run changes your file
A run that is not a dry run rewrites the named file in place. Before it writes, it saves a backup copy next to the target with a `.bak` suffix (for example `app.py.bak`) and logs that path. If a backup with that name already exists, the run refuses to modify the file and exits 1, because that backup may be the only copy of an earlier original. Move or rename the old backup if you want to run the tool on that file again. The rewritten text is parsed before it is written, and a run whose file cannot be written exits 1. An import that shares a line with another statement, for example behind a semicolon, is skipped for safety and listed as skipped in the log.

## License
Copyright (c) ShadowGuardAI
