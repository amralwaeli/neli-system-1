# System 1 MTE interface

## What this is
A Windows-native Gradio app for the MTE demo. It has:
- one problem/conjecture box
- three code boxes: MATLAB, Python, Lean
- three output boxes, one per code box
- a progress strip and a short honesty panel

## How to set up
Open PowerShell in this folder:

```powershell
cd $env:USERPROFILE\nali_deliverables\system1_mte
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## How to run
```powershell
cd $env:USERPROFILE\nali_deliverables\system1_mte
.\.venv\Scripts\python app.py
```
Then open http://127.0.0.1:7860 in your browser.

## What it tries to use
1. MATLAB Engine if installed
2. octave-cli.exe if installed
3. Otherwise it shows a clear message that MATLAB/Octave is not available

Lean runs locally using the Lean toolchain installed by elan.

## Tests
```powershell
cd $env:USERPROFILE\nali_deliverables\system1_mte
.\.venv\Scripts\python -m pytest -q
```

## Files
- app.py: Gradio app
- requirements.txt: pinned Python packages
- tests/: small smoke tests
- samples/: demo code for MATLAB, Python, Lean
