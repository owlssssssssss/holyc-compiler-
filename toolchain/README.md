# Toolchain directory

This folder is populated automatically when you run `install.ps1` or the first `hcc` compile.

It downloads **TinyCC 0.9.27** (Windows binaries + winapi headers) from the official Savannah mirror. These files are **not** stored in git because they are large, third-party, and LGPL-licensed.

After setup you should have:

```
toolchain/tcc/tcc/tcc.exe
toolchain/tcc/tcc/libtcc.dll
toolchain/tcc/winapi-full-for-0.9.27/...
```

If `hcc` complains about a missing compiler, run:

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```