from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
from functools import lru_cache
from html import escape
from pathlib import Path

import gradio as gr

ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"
SAMPLES = ROOT / "samples"
LEAN_PROJECT = ROOT / "mte_lean"
OCTAVE_BIN = ROOT / r"C:\Users\amral\AppData\Local\Programs\GNU Octave\Octave-11.3.0\mingw64\bin"
ELAN_BIN = Path.home() / ".elan" / "bin"
OUTPUTS.mkdir(parents=True, exist_ok=True)
SAMPLES.mkdir(parents=True, exist_ok=True)


DEMO_CONJECTURE = (
    "Beam bending: for a fixed geometry, stress is monotone in the applied moment M, "
    "subject to the sign and positivity assumptions used in the theorem."
)

HONESTY_TEXT = """
### Keep these claims separate
- Synthetic data is **not** an experiment.
- Finite checks are **not** a theorem.
- A declared formula is **not** neural discovery.
- A Lean proof does **not** validate the physical model.
"""

PROGRESS_STEPS = [
    {
        "key": "observe",
        "title": "Observe",
        "caption": "Plot what the formula does",
    },
    {
        "key": "test",
        "title": "Test",
        "caption": "Check the pattern in sample data",
    },
    {
        "key": "conjecture",
        "title": "Conjecture",
        "caption": "State the assumptions clearly",
    },
    {
        "key": "verify",
        "title": "Verify",
        "caption": "Lean checks the logic",
    },
    {
        "key": "stress_test",
        "title": "Stress test",
        "caption": "Remove an assumption and see what breaks",
    },
]

MATLAB_DEMO = r"""
M = linspace(0, 2000, 200);
beams = [0.03, 1.2e-4; 0.05, 9e-5; 0.07, 6e-5];
figure; hold on;
for k = 1:size(beams,1)
  c = beams(k,1);
  I = beams(k,2);
  sigma = (M .* c) ./ I;
  plot(M, sigma, 'LineWidth', 2);
end
xlabel('Bending moment M');
ylabel('Stress sigma');
title('Beam bending: sigma = M*c/I');
grid on;
legend('c=0.03, I=1.2e-4', 'c=0.05, I=9e-5', 'c=0.07, I=6e-5', 'Location', 'northwest');
saveas(gcf, fullfile('outputs', 'beam_stress.png'));
disp('Saved outputs/beam_stress.png');
""".strip()

PYTHON_DEMO = r"""
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import matplotlib.pyplot as plt

np.random.seed(0)
N = 400
M = np.random.uniform(0, 2000, N)
c = np.random.uniform(0.01, 1.0, N)
I = np.random.uniform(0.1, 5.0, N)
sigma = (M * c) / I + np.random.normal(scale=0.01, size=N)

df = pd.DataFrame({'M': M, 'c': c, 'I': I, 'sigma': sigma})
X = df[['M', 'c', 'I']].to_numpy()
y = df['sigma'].to_numpy()
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=1)

x_scaler = StandardScaler()
y_scaler = StandardScaler()
X_train_s = x_scaler.fit_transform(X_train)
X_test_s = x_scaler.transform(X_test)
y_train_s = y_scaler.fit_transform(y_train.reshape(-1, 1)).ravel()

model = MLPRegressor(hidden_layer_sizes=(64, 32, 16), max_iter=1000, random_state=1)
model.fit(X_train_s, y_train_s)

y_pred = y_scaler.inverse_transform(model.predict(X_test_s).reshape(-1, 1)).ravel()
rmse = mean_squared_error(y_test, y_pred) ** 0.5
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

M_sweep = np.linspace(0, 2000, 120)
fixed_c = 0.05
fixed_I = 9e-5
X_sweep = np.column_stack([M_sweep, np.full_like(M_sweep, fixed_c), np.full_like(M_sweep, fixed_I)])
X_sweep_s = x_scaler.transform(X_sweep)
y_sweep = y_scaler.inverse_transform(model.predict(X_sweep_s).reshape(-1, 1)).ravel()
diffs = np.diff(y_sweep)
support_fraction = float(np.mean(diffs >= -1e-9))

plt.figure(figsize=(6, 4))
plt.scatter(y_test, y_pred, s=12, alpha=0.65)
plt.xlabel('True sigma')
plt.ylabel('Predicted sigma')
plt.title('Prediction vs truth')
plt.grid(True)
plt.tight_layout()
plt.savefig('outputs/python_fit.png', dpi=160)
plt.close()

print(f'Test R2: {r2:.4f}')
print(f'RMSE: {rmse:.4f}')
print(f'MAE: {mae:.4f}')
print(f'Support fraction: {support_fraction:.2%}')
print('The fitted model supports a monotone trend in the sampled domain. This is NOT a proof.')
""".strip()

LEAN_GOOD = r"""
import Mathlib

example {M1 M2 c I : ℝ} (hM : M1 ≤ M2) (hc : 0 ≤ c) (hI : 0 < I) : (M1 * c) / I ≤ (M2 * c) / I := by
  have hmul : M1 * c ≤ M2 * c := by
    exact mul_le_mul_of_nonneg_right hM hc
  have hdiv : (M1 * c) / I ≤ (M2 * c) / I := by
    exact (div_le_div_iff_of_pos_right hI).2 hmul
  simpa [mul_comm, mul_left_comm, mul_assoc] using hdiv
""".strip()

LEAN_FALSE_PROOF = r"""
import Mathlib

example : ¬ (∀ M1 M2 c I : ℝ, M1 ≤ M2 → 0 < I → (M1 * c) / I ≤ (M2 * c) / I) := by
  intro h
  have h' := h 0 1 (-1) 1 (by linarith) (by positivity)
  norm_num at h'
""".strip()

LEAN_BAD_ATTEMPT = r"""
import Mathlib

example : ∀ M1 M2 c I : ℝ, M1 ≤ M2 → 0 < I → (M1 * c) / I ≤ (M2 * c) / I := by
  intro M1 M2 c I hM hI
  -- This claim is false when c < 0, so Lean should reject the next line.
  have hmul : M1 * c ≤ M2 * c := by
    exact mul_le_mul_of_nonneg_right hM ?_ 
  exact (div_le_div_iff_of_pos_right hI).2 hmul
""".strip()

LEAN_COUNTEREXAMPLE = r"""
example : ¬ (∀ n : Nat, n = 0) := by
  intro h
  have h1 : 1 = 0 := h 1
  simp at h1
""".strip()


def _step_state(progress: dict[str, bool | str], key: str) -> str:
    value = progress.get(key, False)
    if value == "fail":
        return "fail"
    if value is True:
        return "success"
    return "idle"


def _progress_bar(progress: dict[str, bool | str]) -> str:
    palette = {
        "success": "#2e7d32",
        "fail": "#c62828",
        "idle": "#9e9e9e",
    }
    blocks = []
    for step in PROGRESS_STEPS:
        state = _step_state(progress, step["key"])
        color = palette[state]
        blocks.append(
            f"""
            <div style='flex:1; min-width:150px; padding:10px 12px; border:1px solid {color}; border-radius:10px; background:{color}12;'>
              <div style='font-weight:700; color:{color}; margin-bottom:4px;'>{step['title']}</div>
              <div style='font-size:12px; line-height:1.25; color:var(--foreground);'>{step['caption']}</div>
            </div>
            """
        )
    return (
        "<div style='display:flex; gap:10px; flex-wrap:wrap; align-items:stretch; width:100%;'>"
        + "".join(blocks)
        + "</div>"
    )


def _status_line(ran_with: str, detail: str = "") -> str:
    head = f"Ran with: {ran_with}"
    return head if not detail else head + f"\n{detail}"


def _lean_meta(label: str, last_run: str = "") -> str:
    lean, lake = detect_lean_tools()
    version = "Lean installed" if lean else "Lean not installed"
    if lake:
        version += " | Lake available"
    lines = [f"Result: {label}"]
    if last_run:
        lines.append(f"Last run: {last_run}")
    lines.append(version)
    return "\n".join(lines)


def _lean_output_html(label: str, stdout: str = "", stderr: str = "", accepted_note: str = "Verify OK") -> str:
    if label == "Lean accepted":
        body = (stdout or "Lean accepted the theorem.").strip()
        return (
            "<div style='display:grid; gap:6px;'>"
            f"<div><strong>Result:</strong> {escape(label)}</div>"
            f"<div><strong>Last run:</strong> {escape(accepted_note)}</div>"
            f"<div>{escape(body)}</div>"
            "</div>"
        )

    message = "Lean refused because the assumption 0 <= c was removed, so the claim cannot be proven."
    details = _sanitize_lean_details(stdout or stderr)
    return (
        "<div style='display:grid; gap:8px;'>"
        f"<div>{escape(message)}</div>"
        "<details><summary>Technical details</summary>"
        f"<pre style='white-space:pre-wrap; margin:8px 0 0 0;'>{escape(details)}</pre>"
        "</details>"
        "</div>"
    )


def _sanitize_lean_details(text: str) -> str:
    cleaned = re.sub(r"(?m)^[A-Za-z]:\\.*?\.lean:\d+:\d+:\s*", "", text or "")
    cleaned = re.sub(r"(?m)^.*?tmp[^\n]*?\.lean:\d+:\d+:\s*", "", cleaned)
    return cleaned.strip()


def _stress_box() -> str:
    return (
        "Lean accepted a proof that the stronger claim is FALSE.\n"
        "That is a good outcome for learning because it shows the prover can reject a missing assumption and tell us what breaks."
    )


def _ensure_demo_files() -> None:
    (SAMPLES / "sample_matlab.m").write_text(MATLAB_DEMO + "\n", encoding="utf-8")
    (SAMPLES / "sample_python.py").write_text(PYTHON_DEMO + "\n", encoding="utf-8")
    (SAMPLES / "sample_lean.lean").write_text(LEAN_GOOD + "\n", encoding="utf-8")
    (SAMPLES / "sample_lean_false.lean").write_text(LEAN_COUNTEREXAMPLE + "\n", encoding="utf-8")


_ensure_demo_files()


def _maybe_add_path(folder: Path) -> None:
    folder_str = str(folder)
    current = os.environ.get("PATH", "")
    if folder_str not in current:
        os.environ["PATH"] = folder_str + os.pathsep + current


_maybe_add_path(OCTAVE_BIN)
_maybe_add_path(ELAN_BIN)


def detect_matlab_engine() -> str | None:
    try:
        if importlib.util.find_spec("matlab.engine") is not None:
            import matlab.engine  # type: ignore

            return "MATLAB Engine"
    except Exception:
        pass
    return None


def detect_octave() -> str | None:
    candidates = [
        shutil.which("octave-cli"),
        shutil.which("octave-cli.exe"),
        str(OCTAVE_BIN / "octave-cli.exe"),
        str(OCTAVE_BIN / "octave-cli"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


def detect_lean_tools() -> tuple[str | None, str | None]:
    lean = shutil.which("lean") or str(ELAN_BIN / "lean.exe") if (ELAN_BIN / "lean.exe").exists() else None
    lake = shutil.which("lake") or str(ELAN_BIN / "lake.exe") if (ELAN_BIN / "lake.exe").exists() else None
    if lean and not Path(lean).exists():
        lean = None
    if lake and not Path(lake).exists():
        lake = None
    return lean, lake


def ensure_lake_project() -> Path:
    lakefile = LEAN_PROJECT / "lakefile.toml"
    if lakefile.exists():
        return LEAN_PROJECT
    raise FileNotFoundError(f"Lean project not found at {LEAN_PROJECT}")


def run_subprocess(program: str, args: list[str], cwd: Path, timeout_s: int = 120) -> tuple[int, str, str]:
    result = subprocess.run(
        [program, *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    return result.returncode, result.stdout, result.stderr


def run_matlab_or_octave(code: str) -> tuple[str, str, str]:
    engine = detect_matlab_engine()
    if engine:
        try:
            import matlab.engine  # type: ignore

            eng = matlab.engine.start_matlab()
            eng.cd(str(ROOT).replace("\\", "/"), nargout=0)
            out = eng.evalc(code)
            return "MATLAB Engine", out, ""
        except Exception as exc:
            return "MATLAB Engine", "", f"MATLAB Engine failed: {exc}"

    octave = detect_octave()
    if octave:
        temp = tempfile.NamedTemporaryFile("w", suffix=".m", delete=False, encoding="utf-8", dir=str(ROOT))
        try:
            temp.write(code)
            temp.close()
            rc, out, err = run_subprocess(
                octave,
                ["--quiet", "--no-gui", temp.name],
                cwd=ROOT,
                timeout_s=180,
            )
            return "GNU Octave", out, err + (f"\n(exit code {rc})" if rc else "")
        finally:
            Path(temp.name).unlink(missing_ok=True)

    return "Not installed", "", "MATLAB Engine not installed and octave-cli not found on PATH."


def run_python_stage(code: str) -> tuple[str, str, str]:
    temp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8", dir=str(ROOT))
    try:
        temp.write(code)
        temp.close()
        rc, out, err = run_subprocess(sys.executable, [temp.name], cwd=ROOT, timeout_s=180)
        return "Python", out, err + (f"\n(exit code {rc})" if rc else "")
    finally:
        Path(temp.name).unlink(missing_ok=True)


@lru_cache(maxsize=32)
def run_lean_stage(code: str) -> tuple[str, str, str]:
    lean, lake = detect_lean_tools()
    if not lean:
        return "Lean not installed", "", "Lean not installed."
    if not LEAN_PROJECT.exists():
        return "Lean not installed", "", f"Lean project not found at {LEAN_PROJECT}"
    temp = tempfile.NamedTemporaryFile("w", suffix=".lean", delete=False, encoding="utf-8", dir=str(LEAN_PROJECT))
    try:
        temp.write(code)
        temp.close()
        if lake:
            rc, out, err = run_subprocess(lake, ["env", "lean", temp.name], cwd=LEAN_PROJECT, timeout_s=600)
        else:
            rc, out, err = run_subprocess(lean, [temp.name], cwd=LEAN_PROJECT, timeout_s=600)
        label = "Lean accepted" if rc == 0 else "Lean rejected"
        return label, out, err + (f"\n(exit code {rc})" if rc else "")
    finally:
        Path(temp.name).unlink(missing_ok=True)


def build_demo_codes() -> tuple[str, str, str, str]:
    conjecture = DEMO_CONJECTURE
    return conjecture, MATLAB_DEMO, PYTHON_DEMO, LEAN_GOOD


def _format_run(label: str, stdout: str, stderr: str) -> str:
    tail = ""
    if stderr:
        tail = "\n" + stderr
    return f"Ran with: {label}\n\n{stdout}{tail}".strip()


def run_all(conjecture: str, matlab_code: str, python_code: str, lean_code: str):
    progress = {"observe": False, "test": False, "conjecture": bool(conjecture.strip()), "verify": False, "stress_test": False}
    matlab_runner, matlab_out, matlab_err = run_matlab_or_octave(matlab_code)
    progress["observe"] = matlab_runner != "Not installed"
    python_runner, python_out, python_err = run_python_stage(python_code)
    progress["test"] = not python_err or "Traceback" not in python_err
    lean_runner, lean_out, lean_err = run_lean_stage(lean_code)
    progress["verify"] = lean_runner.startswith("Lean accepted")
    progress_text = _progress_bar(progress)
    matlab_meta = _status_line(matlab_runner)
    lean_meta = _lean_meta(lean_runner if progress["verify"] else "Lean rejected", "Verify OK" if progress["verify"] else "Verify failed")
    matlab_text = matlab_out or matlab_err
    python_text = python_out or python_err
    lean_text = _lean_output_html(lean_runner, lean_out, lean_err, "Verify OK")
    return matlab_meta, matlab_text, python_text, lean_meta, lean_text, "", "", progress_text, str(OUTPUTS / "beam_stress.png"), str(OUTPUTS / "python_fit.png")


def run_stress_test():
    progress = {"observe": True, "test": True, "conjecture": True, "verify": True, "stress_test": True}
    proof_label, proof_out, proof_err = run_lean_stage(LEAN_COUNTEREXAMPLE)
    bad_label, bad_out, bad_err = run_lean_stage(LEAN_BAD_ATTEMPT)
    stress_meta = _lean_meta(proof_label, "Verify OK, Stress test OK" if proof_label == "Lean accepted" else "Verify OK, Stress test failed")
    stress_text = (
        "<div style='display:grid; gap:12px;'>"
        f"<div><strong>{escape(_stress_box().splitlines()[0])}</strong><div>{escape(_stress_box().splitlines()[1])}</div></div>"
        f"<div><strong>Direct attempt</strong>{_lean_output_html(bad_label, bad_out, bad_err, 'Stress test OK')}</div>"
        "</div>"
    )
    lean_meta = _lean_meta("Lean accepted", "Verify OK, Stress test OK")
    return lean_meta, stress_meta, stress_text, _progress_bar(progress)


def run_matlab_button(code: str):
    label, out, err = run_matlab_or_octave(code)
    return _status_line(label), out or err


def run_python_button(code: str):
    label, out, err = run_python_stage(code)
    _ = label
    return out or err


def run_lean_button(code: str):
    label, out, err = run_lean_stage(code)
    last_run = "Verify OK" if label == "Lean accepted" else "Verify failed"
    return _lean_meta(label, last_run), _lean_output_html(label, out, err, "Verify OK")


def load_demo():
    conjecture, matlab, py, lean = build_demo_codes()
    return conjecture, matlab, py, lean, _progress_bar({})


def update_progress(conjecture: str, matlab_out: str, python_out: str, lean_out: str, stress_out: str = "") -> str:
    progress = {
        "observe": bool(matlab_out.strip()),
        "test": bool(python_out.strip()),
        "conjecture": bool(conjecture.strip()),
        "verify": lean_out.startswith("Result: Lean accepted") or "Lean accepted the theorem" in lean_out,
        "stress_test": bool(stress_out.strip()),
    }
    return _progress_bar(progress)


with gr.Blocks(title="MTE interface") as demo:
    gr.Markdown(
        "# MTE interface\n"
        "This app shows how a formula can be checked step by step.\n"
        "For students and teachers: it keeps the code, the test, and the proof separate.\n"
        "AI suggests; Lean checks; every claim stays separate."
    )
    conjecture = gr.Textbox(label="Problem / conjecture", lines=3, value=DEMO_CONJECTURE)
    with gr.Row():
        btn_load = gr.Button("Load demo")
        btn_all = gr.Button("Run all", variant="primary")
        btn_matlab = gr.Button("Run MATLAB")
        btn_python = gr.Button("Run Python")
        btn_lean = gr.Button("Run Lean")
        btn_stress = gr.Button("Stress test")
    progress = gr.HTML(_progress_bar({}))
    gr.Markdown(HONESTY_TEXT)
    with gr.Row():
        matlab_code = gr.Textbox(label="MATLAB code", lines=18, value=MATLAB_DEMO)
        python_code = gr.Textbox(label="Python code", lines=18, value=PYTHON_DEMO)
        lean_code = gr.Textbox(label="Lean code", lines=18, value=LEAN_GOOD)
    matlab_meta = gr.Markdown(_status_line("not run yet"))
    lean_meta = gr.Markdown(_lean_meta("idle"))
    with gr.Row():
        matlab_out = gr.Textbox(label="MATLAB output", lines=10)
        python_out = gr.Textbox(label="Python output", lines=10)
        lean_out = gr.HTML("<div>Not run yet</div>")
    with gr.Row():
        matlab_plot = gr.Image(label="MATLAB plot", type="filepath")
        python_plot = gr.Image(label="Python plot", type="filepath")
    stress_meta = gr.Markdown("Result: not run yet\nLast run: not run")
    stress_out = gr.HTML("")

    btn_load.click(
        fn=load_demo,
        outputs=[conjecture, matlab_code, python_code, lean_code, progress],
    )

    btn_matlab.click(
        fn=run_matlab_button,
        inputs=[matlab_code],
        outputs=[matlab_meta, matlab_out],
    )

    btn_python.click(
        fn=run_python_button,
        inputs=[python_code],
        outputs=[python_out],
    )

    btn_lean.click(
        fn=run_lean_button,
        inputs=[lean_code],
        outputs=[lean_meta, lean_out],
    )

    btn_all.click(
        fn=run_all,
        inputs=[conjecture, matlab_code, python_code, lean_code],
        outputs=[matlab_meta, matlab_out, python_out, lean_meta, lean_out, stress_meta, stress_out, progress, matlab_plot, python_plot],
    )

    btn_stress.click(
        fn=run_stress_test,
        outputs=[lean_meta, stress_meta, stress_out, progress],
    )

if __name__ == "__main__":
    # NALI_SHARE=1 creates a public link (share=True) for reviewers.
    share = os.environ.get("NALI_SHARE", "0").lower() in {"1", "true", "yes"}
    demo.launch(
        server_name="0.0.0.0" if share else "127.0.0.1",
        server_port=7860,
        share=share,
    )
