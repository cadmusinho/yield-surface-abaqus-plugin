from odbAccess import openOdb
from abaqusConstants import INTEGRATION_POINT
import os
import numpy as np
import csv


def find_results_homogenized_full_history(path="", **kwargs):
    RESULTS_DIR = r"C:"
    if path:
        RESULTS_DIR = os.path.normpath(path)

    print("[INFO] Using results directory:", RESULTS_DIR)

    STEP_NAME = "Step-PBC"
    CSV_SEPARATOR = ';'

    def homogenize_3d_frame(frame, odb):
        if not all(k in frame.fieldOutputs for k in ['S', 'PEEQ', 'EVOL']):
            print(f"[WARN] t={frame.frameValue:.4e}: Missing S/PEEQ/EVOL field outputs.")
            return None

        instance = None
        try:
            inst_key = list(odb.rootAssembly.instances.keys())[0]
            instance = odb.rootAssembly.instances[inst_key]
        except:
            instance = None

        def pick_region(odb, instance):
            if instance is not None:
                for name in [" ALL ELEMENTS", "ALL ELEMENTS", "EALL", "ALL_ELEMS"]:
                    if name in instance.elementSets:
                        return instance.elementSets[name]

                try:
                    any_name = list(instance.elementSets.keys())[0]
                    return instance.elementSets[any_name]
                except:
                    pass

            try:
                for name in [" ALL ELEMENTS", "ALL ELEMENTS", "EALL"]:
                    if name in odb.rootAssembly.elementSets:
                        return odb.rootAssembly.elementSets[name]
            except:
                pass

            return None

        def get_vals(frame, odb, field_name, instance):
            fo = frame.fieldOutputs[field_name]
            region = pick_region(odb, instance)

            if region is not None:
                try:
                    vals = fo.getSubset(region=region, position=INTEGRATION_POINT).values
                    if vals:
                        return vals, "IP+SET"
                except:
                    pass

            try:
                vals = fo.getSubset(position=INTEGRATION_POINT).values
                if vals:
                    return vals, "IP"
            except:
                pass

            if region is not None:
                try:
                    vals = fo.getSubset(region=region).values
                    if vals:
                        return vals, "AUTO+SET"
                except:
                    pass

            try:
                vals = fo.values
                if vals:
                    return vals, "VALUES"
            except:
                pass

            return [], "EMPTY"

        s_values, s_pos = get_vals(frame, odb, "S", instance)
        p_values, p_pos = get_vals(frame, odb, "PEEQ", instance)
        v_values, v_pos = get_vals(frame, odb, "EVOL", instance)

        use_ip = (s_pos.startswith("IP") and
                  p_pos.startswith("IP") and
                  v_pos.startswith("IP"))

        if not s_values or not p_values or not v_values:
            print(
                f"[WARN] t={frame.frameValue:.4e}: Empty data (S:{len(s_values)} PEEQ:{len(p_values)} EVOL:{len(v_values)}) | pos S={s_pos} P={p_pos} V={v_pos}")
            return None

        def key_of(val):
            el = getattr(val, "elementLabel", None)
            ip = getattr(val, "integrationPoint", None)

            if el is None:
                return None

            if use_ip and ip is not None:
                return (int(el), int(ip))
            else:
                return int(el)

        S_map, P_map, V_map = {}, {}, {}

        for sv in s_values:
            k = key_of(sv)
            if k is not None:
                S_map[k] = sv

        for pv in p_values:
            k = key_of(pv)
            if k is not None:
                P_map[k] = pv

        for vv in v_values:
            k = key_of(vv)
            if k is not None:
                V_map[k] = vv

        common = set(S_map) & set(P_map) & set(V_map)
        if not common:
            print(
                f"[WARN] t={frame.frameValue:.4e}: No common points found (mismatch). S={len(S_map)} P={len(P_map)} V={len(V_map)}")
            return None

        # --- sums for homogenization (EVOL-weighted) ---
        S_sum = np.zeros(6)
        mises_sum = 0.0
        peeq_sum = 0.0

        maxp_sum = 0.0
        midp_sum = 0.0
        minp_sum = 0.0

        total_evol = 0.0

        for k in common:
            sv = S_map[k]
            pv = P_map[k]
            vv = V_map[k]
            try:
                w = float(vv.data)
                sdata = np.array(sv.data, dtype=float)  # [S11,S22,S33,S12,S13,S23]

                S_sum += sdata * w
                mises_sum += float(getattr(sv, "mises")) * w
                peeq_sum += float(pv.data) * w

                # principal stresses from Abaqus if available, otherwise compute from tensor
                try:
                    maxp = float(getattr(sv, "maxPrincipal"))
                    midp = float(getattr(sv, "midPrincipal"))
                    minp = float(getattr(sv, "minPrincipal"))
                except:
                    S11, S22, S33, S12, S13, S23 = [float(x) for x in sdata]
                    Smat = np.array([
                        [S11, S12, S13],
                        [S12, S22, S23],
                        [S13, S23, S33],
                    ], dtype=float)
                    eig = np.linalg.eigvalsh(Smat)  # ascending: [min, mid, max]
                    minp, midp, maxp = float(eig[0]), float(eig[1]), float(eig[2])

                maxp_sum += maxp * w
                midp_sum += midp * w
                minp_sum += minp * w

                total_evol += w
            except:
                continue

        if total_evol <= 0.0:
            print(f"[WARN] t={frame.frameValue:.4e}: total_evol <= 0.")
            return None

        S_avg = S_sum / total_evol
        mises_avg = mises_sum / total_evol
        peeq_avg = peeq_sum / total_evol

        maxp_avg = maxp_sum / total_evol
        midp_avg = midp_sum / total_evol
        minp_avg = minp_sum / total_evol

        S11, S22, S33 = float(S_avg[0]), float(S_avg[1]), float(S_avg[2])

        # return order must match CSV header below
        return [mises_avg, S11, S22, S33, maxp_avg, midp_avg, minp_avg, peeq_avg]

    os.chdir(RESULTS_DIR)
    odb_files = [f for f in os.listdir('.') if f.lower().endswith('.odb')]
    odb_files.sort()

    print("[INFO] ODB files found:", odb_files)
    if not odb_files:
        print("[ERR] No ODB files found in the directory.")
        return

    for idx, odb_name in enumerate(odb_files):
        print(f"\n[INFO] Processing ODB {idx + 1}/{len(odb_files)}: {odb_name}")

        try:
            odb = openOdb(odb_name, readOnly=True)
        except Exception as e:
            print(f"[ERR] Could not open {odb_name}: {e}")
            continue

        if STEP_NAME not in odb.steps:
            print(f"[WARN] Step {STEP_NAME} not found in {odb_name}. Skipping.")
            odb.close()
            continue

        step = odb.steps[STEP_NAME]
        frames = step.frames or []
        if not frames:
            print("[WARN] No frames found in the step. Skipping.")
            odb.close()
            continue

        csv_name = odb_name[:-4] + "_homogenized_full.csv"
        header = [
            "frame", "time_step",
            "Mises", "S11", "S22", "S33",
            "MaxPrincipal", "MidPrincipal", "MinPrincipal",
            "PEEQ"
        ]

        output_data = []

        n = len(frames)
        print(f"[INFO] Frames in step: {n}")

        for i, frame in enumerate(frames):
            if i % (n // 10 + 1) == 0:
                print(f"[INFO] Progress: {i+1}/{n} ({(i+1)/n*100:.1f}%)")

            if not frame.fieldOutputs:
                continue

            res = homogenize_3d_frame(frame, odb)
            if res is None:
                continue

            row = [i, frame.frameValue] + res
            output_data.append(row)

        odb.close()

        if output_data:
            with open(csv_name, "w", newline="") as f:
                w = csv.writer(f, delimiter=CSV_SEPARATOR)
                w.writerow(header)
                for row in output_data:
                    w.writerow(["%.6e" % float(v) for v in row])
            print(f"[INFO] Saved {len(output_data)} frames to: {csv_name}")
        else:
            print("[WARN] No data to save (all frames were skipped).")

    print("\n[INFO] Full homogenization completed.")


find_results = find_results_homogenized_full_history
