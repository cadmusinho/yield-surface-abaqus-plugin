import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

DISTINCT_COLORS = ["#1f77b4","#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
                "#e377c2", "#17becf", "#bcbd22", "#7f7f7f", "#4e79a7", "#f28e2b", "#59a14f",
                   "#e15759", "#b07aa1", "#9c755f", "#76b7b2", "#edc948", "#af7aa1", "#2f4b7c"]

def _safe_filename(s: str) -> str:
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

def _pca_axis(points):
    center = points.mean(axis=0)
    X = points - center

    C = (X.T @ X) / max(len(points) - 1, 1)
    w, V = np.linalg.eigh(C)
    axis = V[:, np.argmax(w)]
    axis = axis / (np.linalg.norm(axis) + 1e-12)

    helper = np.array([1.0, 0.0, 0.0])
    if abs(np.dot(helper, axis)) > 0.9:
        helper = np.array([0.0, 1.0, 0.0])

    u = np.cross(axis, helper)
    u = u / (np.linalg.norm(u) + 1e-12)
    v = np.cross(axis, u)
    v = v / (np.linalg.norm(v) + 1e-12)

    t = X @ axis
    perp = X - np.outer(t, axis)
    return center, axis, u, v, t, perp

def _fit_circle_kasa(xy):
    x = xy[:, 0]
    y = xy[:, 1]
    A = np.column_stack([x, y, np.ones_like(x)])
    b = -(x**2 + y**2)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    a, bb, c = sol
    cx = -a / 2.0
    cy = -bb / 2.0
    r = np.sqrt(max(0.0, (cx**2 + cy**2) - c))
    return float(cx), float(cy), float(r)

def _set_axes_equal(ax):
    x_limits = ax.get_xlim3d()
    y_limits = ax.get_ylim3d()
    z_limits = ax.get_zlim3d()

    x_range = abs(x_limits[1] - x_limits[0])
    x_middle = np.mean(x_limits)
    y_range = abs(y_limits[1] - y_limits[0])
    y_middle = np.mean(y_limits)
    z_range = abs(z_limits[1] - z_limits[0])
    z_middle = np.mean(z_limits)

    plot_radius = 0.5 * max([x_range, y_range, z_range, 1e-9])
    ax.set_xlim3d([x_middle - plot_radius, x_middle + plot_radius])
    ax.set_ylim3d([y_middle - plot_radius, y_middle + plot_radius])
    ax.set_zlim3d([z_middle - plot_radius, z_middle + plot_radius])

def _draw_cylinder(ax, pts_xyz, label,
                   show_points=True,
                   show_axis=True,
                   cyl_alpha=0.22,
                   pts_alpha=0.55,
                   n_theta=80,
                   n_h=40,
                   min_points=12,
                   color=None):

    if pts_xyz is None or len(pts_xyz) < min_points:
        print("[WARN] %s: not enough points (%s) -> skipping cylinder" % (label, 0 if pts_xyz is None else len(pts_xyz)))
        return None

    center, axis, u, v, t, perp = _pca_axis(pts_xyz)

    x2 = perp @ u
    y2 = perp @ v
    xy = np.column_stack([x2, y2])

    cx2, cy2, r = _fit_circle_kasa(xy)
    if not np.isfinite(r) or r <= 0:
        print("[WARN] %s: invalid radius (r=%s) -> skipping cylinder" % (label, r))
        return None

    tmin, tmax = float(np.min(t)), float(np.max(t))
    if abs(tmax - tmin) < 1e-9:
        print("[WARN] %s: height ~0 -> skipping cylinder" % label)
        return None

    theta = np.linspace(0, 2*np.pi, n_theta)
    tt = np.linspace(tmin, tmax, n_h)
    Theta, T = np.meshgrid(theta, tt)

    Xc2 = cx2 + r * np.cos(Theta)
    Yc2 = cy2 + r * np.sin(Theta)

    X3 = center[0] + T * axis[0] + Xc2 * u[0] + Yc2 * v[0]
    Y3 = center[1] + T * axis[1] + Xc2 * u[1] + Yc2 * v[1]
    Z3 = center[2] + T * axis[2] + Xc2 * u[2] + Yc2 * v[2]

    if show_points:
        ax.scatter(pts_xyz[:, 0], pts_xyz[:, 1], pts_xyz[:, 2], s=12, alpha=pts_alpha, color=color)

    ax.plot_surface(X3, Y3, Z3, alpha=cyl_alpha, linewidth=0, color=color)

    if show_axis:
        p1 = center + tmin * axis
        p2 = center + tmax * axis
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]], linewidth=2, color=color)

    print("[INFO] %s: cylinder r=%.6g, height=%.6g" % (label, r, (tmax - tmin)))
    return r

def simple_graph(path="", target_values="0.01", x_label="", y_label="", z_label="",
                 show_points=True, show_axis=True):

    x, y, z = "S11", "S22", "S33"
    CSV_SEPARATOR = ";"

    SHOW_POINTS = bool(show_points)
    SHOW_AXIS = bool(show_axis)

    CYL_ALPHA = 0.22
    PTS_ALPHA = 0.55
    CYL_N_THETA = 80
    CYL_N_H = 40
    MIN_POINTS_FOR_CYL = 12

    raw_items = [p.strip().strip('"') for p in str(path).split(';') if p.strip()]
    items = []
    seen = set()
    for it in raw_items:
        if "|" in it:
            folder, name = it.split("|", 1)
        else:
            folder = it
            name = os.path.basename(folder.rstrip("\\/")) or folder

        folder = folder.strip()
        name = name.strip()

        if folder and (folder, name) not in seen:
            seen.add((folder, name))
            items.append((folder, name))

    if not items:
        raise RuntimeError("No CSV directories provided.")

    for folder, _ in items:
        if not os.path.isdir(folder):
            raise RuntimeError("Directory does not exist: %s" % folder)

    targets = [float(v) for v in str(target_values).split(";") if v.strip()]

    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection="3d")
    color_idx = 0
    legend_handles = []
    all_points_for_limits = []

    for folder, model_name in items:
        csv_files = [f for f in os.listdir(folder) if f.endswith("_homogenized_full.csv")]
        model_safe = (model_name or "").strip() or os.path.basename(folder.rstrip("\\/")) or "model"

        for t_val in targets:
            rows = []

            for f in csv_files:
                try:
                    df = pd.read_csv(os.path.join(folder, f), sep=CSV_SEPARATOR)

                    needed = ["PEEQ", x, y, z]
                    for c in needed:
                        if c not in df.columns:
                            raise KeyError("Missing column %s" % c)
                        df[c] = df[c].astype(str).str.replace(",", ".").astype(float)

                    rr = row_at_peeq(df, t_val, [x, y, z])
                    if rr is not None:
                        rows.append(rr)

                except Exception as e:
                    print("[WARN] %s | %s: %s" % (model_safe, f, e))
                    continue

            print("[INFO] %s | PEEQ=%.6g -> %d points" % (model_safe, t_val, len(rows)))
            if not rows:
                continue

            sdf = pd.DataFrame(rows)
            pts = sdf[[x, y, z]].to_numpy(dtype=float)

            label = "%s | PEEQ=%.4f" % (model_safe, t_val)

            color = DISTINCT_COLORS[color_idx % len(DISTINCT_COLORS)]
            color_idx += 1

            res = _draw_cylinder(
                ax,
                pts_xyz=pts,
                label=label,
                show_points=SHOW_POINTS,
                show_axis=SHOW_AXIS,
                cyl_alpha=CYL_ALPHA,
                pts_alpha=PTS_ALPHA,
                n_theta=CYL_N_THETA,
                n_h=CYL_N_H,
                min_points=MIN_POINTS_FOR_CYL,
                color=color
            )

            if res is not None:
                legend_handles.append(
                    Line2D(
                        [0], [0],
                        marker='o',
                        linestyle='None',
                        markersize=7,
                        markerfacecolor=color,
                        markeredgecolor=color,
                        label=label
                    )
                )
                all_points_for_limits.append(pts)

    ax.set_xlabel((x_label or "").strip() or x)
    ax.set_ylabel((y_label or "").strip() or y)
    ax.set_zlabel((z_label or "").strip() or z)

    if all_points_for_limits:
        P = np.vstack(all_points_for_limits)
        m = P.mean(axis=0)
        rr = max(P.max(axis=0) - P.min(axis=0)) / 2.0
        ax.set_xlim(m[0] - rr, m[0] + rr)
        ax.set_ylim(m[1] - rr, m[1] + rr)
        ax.set_zlim(m[2] - rr, m[2] + rr)
        _set_axes_equal(ax)

    if legend_handles:
        ax.legend(handles=legend_handles, loc="upper right", fontsize=9)

    ax.set_title("Cylinder shapes fitted to points (S11/S22/S33)")
    plt.tight_layout()
    plt.show()
