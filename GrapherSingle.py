import os
import re
import time
import subprocess
import numpy as np
import pandas as pd

DEFAULT_COLOR = "#1f77b4"

def _safe_filename(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[^\w\-\.]+", "_", s, flags=re.UNICODE)
    s = re.sub(r"_+", "_", s)
    return s.strip("_") or "model"

def _to_float(s) -> float:
    return float(str(s).strip().replace(",", "."))

def row_at_peeq(df, target, cols):
    time_col = None
    for tcol in ["time", "Time", "STEP_TIME", "StepTime", "frame", "Frame", "increment", "Increment"]:
        if tcol in df.columns:
            time_col = tcol
            break

    if time_col is not None:
        df = df.sort_values(time_col).reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)

    peeq_raw = df["PEEQ"].to_numpy(dtype=float)
    peeq = np.maximum.accumulate(peeq_raw)

    if np.nanmax(peeq) < target:
        return None

    i2 = int(np.searchsorted(peeq, target, side="left"))
    if i2 <= 0:
        out = {"PEEQ": float(target)}
        for c in cols:
            out[c] = float(df.loc[0, c])
        return pd.Series(out)

    i1 = i2 - 1
    r1 = df.iloc[i1]
    r2 = df.iloc[i2]

    p1 = float(peeq[i1])
    p2 = float(peeq[i2])

    if abs(p2 - p1) < 1e-12:
        out = {"PEEQ": float(target)}
        for c in cols:
            out[c] = float(r2[c])
        return pd.Series(out)

    w = (target - p1) / (p2 - p1)

    out = {"PEEQ": float(target)}
    for c in cols:
        out[c] = float(r1[c]) + w * (float(r2[c]) - float(r1[c]))
    return pd.Series(out)

def grapher_single(folder="", target_value="0.01", out_dir="",
                   title="Single graph", x_label="S11", y_label="S22", z_label="S33",
                   model_name="", **kwargs):

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    for k in ["folder", "target_value", "out_dir", "title", "x_label", "y_label", "z_label", "model_name"]:
        v = locals()[k]
        if hasattr(v, "getValue"):
            locals()[k] = v.getValue()

    folder = (folder or "").strip()
    out_dir = (out_dir or "").strip()
    model_name = (model_name or "").strip()

    if not folder or not os.path.isdir(folder):
        raise RuntimeError("The folder is empty or does not exist.")
    if not out_dir:
        raise RuntimeError("Output directory is empty — please provide an output directory.")

    target = _to_float(target_value)
    out_dir = os.path.normpath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    charts_dir = os.path.normpath(os.path.join(out_dir, "Charts"))
    os.makedirs(charts_dir, exist_ok=True)

    model_safe = _safe_filename(model_name or os.path.basename(folder.rstrip("\\/")) or "model")

    x, y, z = "S11", "S22", "S33"
    CSV_SEPARATOR = ";"

    csv_files = [f for f in os.listdir(folder) if f.endswith("_homogenized_full.csv")]
    if not csv_files:
        raise RuntimeError("No *_homogenized_full.csv files found in the folder.")

    rows = []
    for f in csv_files:
        fp = os.path.join(folder, f)
        try:
            df = pd.read_csv(fp, sep=CSV_SEPARATOR)

            needed = ["PEEQ", x, y, z]
            for c in needed:
                if c not in df.columns:
                    raise KeyError("Missing column %s" % c)
                df[c] = df[c].astype(str).str.replace(",", ".").astype(float)

            rr = row_at_peeq(df, float(target), [x, y, z])
            if rr is not None:
                rows.append(rr)

        except Exception as e:
            print(f"[WARN] {f}: {e}")

    if not rows:
        raise RuntimeError("No points found for target_value=%.6g" % float(target))

    sdf = pd.DataFrame(rows)[[x, y, z]].copy()

    t_tag = ("%.6f" % float(target)).rstrip("0").rstrip(".")
    t_tag = t_tag.replace(".", "p")

    out_csv_name = "%s__target_%s__%s_%s_%s.csv" % (model_safe, t_tag, x, y, z)
    out_csv_path = os.path.join(out_dir, out_csv_name)
    sdf.to_csv(out_csv_path, sep=";", index=False)

    config_path = os.path.join(BASE_DIR, "config_single.txt")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(charts_dir + "\n")
        f.write(out_csv_path + "\n")
        f.write((title or "Single graph") + "\n")
        f.write((x_label or "S11") + "\n")
        f.write((y_label or "S22") + "\n")
        f.write((z_label or "S33") + "\n")
        f.write(DEFAULT_COLOR + "\n")

    script_bas = os.path.join(BASE_DIR, "ScriptSingle.BAS")
    scripter_exe = os.environ.get("GRAPHER_PATH")

    if not scripter_exe or not os.path.exists(scripter_exe):
        raise FileNotFoundError("Scripter.exe not found. Set the GRAPHER_PATH environment variable to the full path of Scripter.exe.")
    if not os.path.exists(script_bas):
        raise FileNotFoundError(f"ScriptSingle.BAS doesn't exist: {script_bas}")

    result = subprocess.run(
        [scripter_exe, "-x", script_bas, "-h"],
        capture_output=True,
        text=True,
        cwd=BASE_DIR
    )
    print("STDOUT:\n", result.stdout)
    print("STDERR:\n", result.stderr)

    time.sleep(1)

    try:
        subprocess.call("taskkill /f /im grapher.exe", shell=True)
    except Exception as e:
        print("[WARN] Error closing grapher.exe:", e)

    print("[DONE] CSV:", out_csv_path)
    print("[DONE] Chart dir:", charts_dir)
    return out_csv_path
