import os
import re
import time
import subprocess
import numpy as np
import pandas as pd

DISTINCT_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
    "#e377c2", "#17becf", "#bcbd22", "#7f7f7f", "#4e79a7", "#f28e2b", "#59a14f",
    "#e15759", "#b07aa1", "#9c755f", "#76b7b2", "#edc948", "#af7aa1", "#2f4b7c"
]

def _safe_filename(s):
    s = (s or "").strip()
    s = re.sub(r"[^\w\-\.]+", "_", s, flags=re.UNICODE)
    s = re.sub(r"_+", "_", s)
    return s.strip("_") or "model"

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

def _parse_paths(path_str):
    raw_items = [p.strip().strip('"') for p in str(path_str).split(";") if p.strip()]
    items, seen = [], set()

    for it in raw_items:
        if "|" in it:
            folder, name = it.split("|", 1)
        else:
            folder = it
            name = os.path.basename(folder.rstrip("\\/")) or folder

        folder = (folder or "").strip()
        name = (name or "").strip()

        if folder and (folder, name) not in seen:
            seen.add((folder, name))
            items.append((folder, name))

    return items

def _ensure_float_list(v):
    vals = [x.strip() for x in str(v).split(";") if x.strip()]
    return [float(x.replace(",", ".")) for x in vals]

def grapher(path="", out_dir="", target_values="0.01",
            title="Chart", x_label="S11", y_label="S22", z_label="S33",
            **kwargs):

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    if hasattr(path, "getValue"):
        path = path.getValue()
    if hasattr(out_dir, "getValue"):
        out_dir = out_dir.getValue()
    if hasattr(target_values, "getValue"):
        target_values = target_values.getValue()
    if hasattr(title, "getValue"):
        title = title.getValue()
    if hasattr(x_label, "getValue"):
        x_label = x_label.getValue()
    if hasattr(y_label, "getValue"):
        y_label = y_label.getValue()
    if hasattr(z_label, "getValue"):
        z_label = z_label.getValue()

    items = _parse_paths(path)
    if not items:
        raise RuntimeError("No CSV directories provided (path).")

    out_dir = (out_dir or "").strip()
    if not out_dir:
        raise RuntimeError("Output directory is empty — please specify an Output directory.")

    out_dir = os.path.normpath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    charts_dir = os.path.normpath(os.path.join(out_dir, "Charts"))
    os.makedirs(charts_dir, exist_ok=True)

    targets = _ensure_float_list(target_values)
    if not targets:
        raise RuntimeError("Missing target_values.")

    x, y, z = "S11", "S22", "S33"
    CSV_SEPARATOR = ";"

    saved_csv_paths = []

    for folder, model_name in items:
        if not os.path.isdir(folder):
            print("[WARN] Directory does not exist:", folder)
            continue

        model_safe = _safe_filename(model_name or os.path.basename(folder.rstrip("\\/")) or "model")
        csv_files = [f for f in os.listdir(folder) if f.endswith("_homogenized_full.csv")]

        if not csv_files:
            print(f"[WARN] {model_safe}: missing *_homogenized_full.csv")
            continue

        for t_val in targets:
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

                    rr = row_at_peeq(df, float(t_val), [x, y, z])
                    if rr is not None:
                        rows.append(rr)

                except Exception as e:
                    print(f"[WARN] {model_safe} | {f}: {e}")
                    continue

            print("[INFO] %s | target=%.6g -> %d points" % (model_safe, float(t_val), len(rows)))
            if not rows:
                continue

            sdf = pd.DataFrame(rows)[[x, y, z]].copy()

            t_tag = ("%.6f" % float(t_val)).rstrip("0").rstrip(".")
            t_tag = t_tag.replace(".", "p")

            out_name = "%s__target_%s__%s_%s_%s.csv" % (model_safe, t_tag, x, y, z)
            out_path = os.path.join(out_dir, out_name)

            sdf.to_csv(out_path, sep=";", index=False)
            saved_csv_paths.append(out_path)
            print("[SAVE]", out_path, "(rows=%d)" % len(sdf))

    if not saved_csv_paths:
        print("[DONE] No data saved — no data available for the chart.")
        return 0

    all_csv = sorted([
        os.path.join(out_dir, f)
        for f in os.listdir(out_dir)
        if f.lower().endswith(".csv")
    ])
    n_series = len(all_csv)

    colors_for_series = [
        DISTINCT_COLORS[i % len(DISTINCT_COLORS)]
        for i in range(n_series)
    ]

    config_path = os.path.join(BASE_DIR, "config.txt")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(charts_dir + "\n")
        f.write(out_dir + "\n")
        f.write((title or "Chart") + "\n")
        f.write((x_label or "S11") + "\n")
        f.write((y_label or "S22") + "\n")
        f.write((z_label or "S33") + "\n")
        f.write(str(n_series) + "\n")
        for hx in colors_for_series:
            f.write(hx + "\n")

    script_bas = os.path.join(BASE_DIR, "Script.BAS")
    scripter_exe = os.environ.get("GRAPHER_PATH")

    if not scripter_exe or not os.path.exists(scripter_exe):
        raise FileNotFoundError("Scripter.exe not found. Set the GRAPHER_PATH environment variable to the full path of Scripter.exe.")
    if not os.path.exists(script_bas):
        raise FileNotFoundError(f"Script.BAS doesn't exist: {script_bas}")

    print("[RUN] Scripter:", scripter_exe)
    print("[RUN] BAS:", script_bas)
    print("[RUN] CSV dir:", out_dir)
    print("[RUN] Charts dir:", charts_dir)
    print("[RUN] Series:", n_series)

    try:
        result = subprocess.run(
            [scripter_exe, "-x", script_bas, "-h"],
            capture_output=True,
            text=True,
            cwd=BASE_DIR
        )
        print("STDOUT:\n", result.stdout)
        print("STDERR:\n", result.stderr)
        if result.returncode != 0:
            print("[WARN] Scripter return code:", result.returncode)
        else:
            print("[OK] BAS executed by Scripter.")
    except Exception as e:
        print("[ERR] Error executing Scripter.exe:", e)

    time.sleep(2)

    try:
        subprocess.call("taskkill /f /im grapher.exe", shell=True)
    except Exception as e:
        print("[WARN] Error closing grapher.exe:", e)

    try:
        if os.path.exists(config_path):
            os.remove(config_path)
    except Exception as e:
        print("[WARN] Cleanup:", e)

    print("[DONE] Charts located in:", charts_dir)
    return len(saved_csv_paths)
