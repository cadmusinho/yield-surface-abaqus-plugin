# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import numpy as np
import os

ROUND_PRINT = 6
BASE_TOL_FACTOR_FACE = 1e-6
MATCH_TOLS = [1e-6, 5e-6, 1e-5, 5e-5, 1e-4, 5e-4, 1e-3]
OUTPUT_DIR_DEFAULT = r"C:\Temp\RVE_PBC"
STEP_NAME = "Step-PBC"
AMP_NAME = "AMP_SMOOTH_RAMP"

def repo_has(repo, key):
    try:
        return repo.has_key(key)
    except Exception:
        try:
            return key in repo.keys()
        except Exception:
            try:
                _ = repo[key]
                return True
            except Exception:
                return False

def repo_del(repo, key):
    if repo_has(repo, key):
        try:
            del repo[key]
            return True
        except Exception:
            try:
                repo.__delitem__(key)
                return True
            except Exception:
                return False
    return False

def get_current_model_name():
    if not mdb.models:
        raise RuntimeError("No models found in mdb.models - nothing to process.")
    if len(mdb.models) == 1:
        return list(mdb.models.keys())[0]
    try:
        vp = session.viewports[session.currentViewportName]
        disp = vp.displayedObject
        if hasattr(disp, "modelName"):
            return disp.modelName
    except Exception:
        pass
    return list(mdb.models.keys())[0]

def safe_mkdir(path):
    try:
        if path and not os.path.isdir(path):
            os.makedirs(path)
    except Exception:
        pass

def is_close(v, t, tol):
    return abs(float(v) - float(t)) <= float(tol)

def cleanup_previous(a, m):
    for nm in list(m.boundaryConditions.keys()):
        if nm.startswith("BC_") or nm.startswith("PBC_") or nm.startswith("FIX_"):
            repo_del(m.boundaryConditions, nm)

    for nm in list(m.constraints.keys()):
        if nm.startswith("PBC_") or nm.startswith("EQ_"):
            repo_del(m.constraints, nm)

    for sname in list(a.sets.keys()):
        if (sname.startswith("FACE_") or sname.startswith("NODE_") or
            sname.startswith("RP_") or sname.startswith("FIXED_") or
            sname.startswith("PBC_") or sname.startswith("EDGE_") or
            sname.startswith("CORNER_") or sname.startswith("MASTER_")):
            repo_del(a.sets, sname)

def make_set_nodes(a, instName, name, node_labels):
    repo_del(a.sets, name)
    a.SetFromNodeLabels(name=name, nodeLabels=((instName, node_labels),))
    return a.sets[name]

def make_rp_set(a, name, point):
    repo_del(a.sets, name)
    rp_feat = a.ReferencePoint(point=point)
    rp_id = rp_feat.id
    a.Set(name=name, referencePoints=(a.referencePoints[rp_id],))
    return a.sets[name]

def proj(axis, node):
    x, y, z = node.coordinates
    if axis == "X": return (y, z)
    if axis == "Y": return (x, z)
    return (x, y)

def pair_faces_unique(plus_nodes, minus_nodes, axis, Lmax, match_tols):
    if not plus_nodes or not minus_nodes:
        return [], {"pairs": 0, "unmatched_plus": len(plus_nodes), "unmatched_minus": len(minus_nodes),
                    "tol_rel": None, "plane_tol": None}

    arr_minus = np.array([proj(axis, n) for n in minus_nodes], dtype=float)

    best_pairs = []
    best_stats = None

    for tol_rel in match_tols:
        plane_tol = tol_rel * Lmax
        q = max(plane_tol, 1e-12)

        bucket = {}
        for j, pt in enumerate(arr_minus):
            key = (int(pt[0] / q), int(pt[1] / q))
            bucket.setdefault(key, []).append(j)

        used_minus = set()
        pairs = []
        unmatched_plus = 0

        plus_sorted = sorted(plus_nodes, key=lambda n: proj(axis, n))

        for np_ in plus_sorted:
            p0, p1 = proj(axis, np_)
            key = (int(p0 / q), int(p1 / q))

            cand = []
            for dxk in (-1, 0, 1):
                for dyk in (-1, 0, 1):
                    cand += bucket.get((key[0] + dxk, key[1] + dyk), [])

            best_j = None
            best_d2 = None
            for j in cand:
                if j in used_minus:
                    continue
                mpt = arr_minus[j]
                d0 = p0 - mpt[0]
                d1 = p1 - mpt[1]
                d2 = d0*d0 + d1*d1
                if d2 <= plane_tol*plane_tol:
                    if best_d2 is None or d2 < best_d2:
                        best_d2 = d2
                        best_j = j

            if best_j is None:
                unmatched_plus += 1
                continue

            used_minus.add(best_j)
            pairs.append((np_, minus_nodes[best_j]))

        unmatched_minus = len(minus_nodes) - len(used_minus)

        stats = {
            "tol_rel": tol_rel,
            "plane_tol": plane_tol,
            "pairs": len(pairs),
            "unmatched_plus": unmatched_plus,
            "unmatched_minus": unmatched_minus,
        }

        if best_stats is None:
            best_pairs, best_stats = pairs, stats
        else:
            if (stats["pairs"] > best_stats["pairs"]) or \
               (stats["pairs"] == best_stats["pairs"] and
                (stats["unmatched_plus"] + stats["unmatched_minus"]) <
                (best_stats["unmatched_plus"] + best_stats["unmatched_minus"])):
                best_pairs, best_stats = pairs, stats

        if stats["unmatched_plus"] == 0 and stats["unmatched_minus"] == 0:
            break

    return best_pairs, best_stats

def pair_edge_unique_1d(slaves, masters, axis_idx, Lmax, match_tols):
    if not slaves or not masters:
        return [], {"pairs": 0, "unmatched_slaves": len(slaves), "unmatched_masters": len(masters),
                    "tol_rel": None, "tol": None}

    masters_vals = np.array([n.coordinates[axis_idx] for n in masters], dtype=float)

    best_pairs = []
    best_stats = None

    for tol_rel in match_tols:
        tol = tol_rel * Lmax
        q = max(tol, 1e-12)

        bucket = {}
        for j, mv in enumerate(masters_vals):
            key = int(mv / q)
            bucket.setdefault(key, []).append(j)

        used = set()
        pairs = []
        unmatched = 0

        slaves_sorted = sorted(slaves, key=lambda n: n.coordinates[axis_idx])

        for s in slaves_sorted:
            sv = s.coordinates[axis_idx]
            key = int(sv / q)

            cand = bucket.get(key, []) + bucket.get(key-1, []) + bucket.get(key+1, [])

            best_j = None
            best_d = None
            for j in cand:
                if j in used:
                    continue
                d = abs(masters_vals[j] - sv)
                if d <= tol and (best_d is None or d < best_d):
                    best_d = d
                    best_j = j

            if best_j is None:
                unmatched += 1
                continue

            used.add(best_j)
            pairs.append((s, masters[best_j]))

        stats = {
            "tol_rel": tol_rel,
            "tol": tol,
            "pairs": len(pairs),
            "unmatched_slaves": unmatched,
            "unmatched_masters": len(masters) - len(used),
        }

        if best_stats is None:
            best_pairs, best_stats = pairs, stats
        else:
            if (stats["pairs"] > best_stats["pairs"]) or \
               (stats["pairs"] == best_stats["pairs"] and
                (stats["unmatched_slaves"] + stats["unmatched_masters"]) <
                (best_stats["unmatched_slaves"] + best_stats["unmatched_masters"])):
                best_pairs, best_stats = pairs, stats

        if stats["unmatched_slaves"] == 0 and stats["unmatched_masters"] == 0:
            break

    return best_pairs, best_stats


def pbc(path="", n_points=37, eps_max=0.1, num_intervals=100, time_period=1.0,
        max_num_inc=2000, initial_inc=0.01, min_inc=1e-12, max_inc=0.01, theta_max=360.0,
        theta_count=5, n_hydro=7,n_dev=3):

    import traceback
    try:
        N_POINTS = int(n_points)
        EPS_MAX = float(eps_max)
        NUM_INTERVALS = int(num_intervals)
        TIME_PERIOD = float(time_period)
        MAX_NUM_INC = int(max_num_inc)
        INITIAL_INC = float(initial_inc)
        MIN_INC = float(min_inc)
        MAX_INC = float(max_inc)
        THETA_MAX = float(theta_max)
        THETA_COUNT = int(theta_count)
        N_HYDRO = int(n_hydro)
        N_DEV = int(n_dev)

        if THETA_COUNT < 1:
            raise ValueError("theta_count must be >= 1")
        if N_HYDRO < 1 or N_DEV < 1:
            raise ValueError("n_hydro and n_dev must be >= 1")
        if MAX_INC <= 0 or INITIAL_INC <= 0 or TIME_PERIOD <= 0:
            raise ValueError("time_period/initial_inc/max_inc must be > 0")
        if MIN_INC <= 0:
            raise ValueError("min_inc must be > 0")
        if INITIAL_INC > MAX_INC:
            print("[WARN] initial_inc > max_inc, swapping values.")
            INITIAL_INC, MAX_INC = MAX_INC, INITIAL_INC

        OUTPUT_DIR = path if path else OUTPUT_DIR_DEFAULT
        safe_mkdir(OUTPUT_DIR)
        try:
            os.chdir(OUTPUT_DIR)
        except Exception:
            print("[WARN] Cannot access OUTPUT_DIR, proceeding in current directory.")

        model_name = get_current_model_name()
        m = mdb.models[model_name]
        a = m.rootAssembly
        a.regenerate()

        if repo_has(m.amplitudes, AMP_NAME):
            try:
                del m.amplitudes[AMP_NAME]
            except:
                pass

        m.SmoothStepAmplitude(
            name=AMP_NAME,
            timeSpan=STEP,
            data=((0.0, 0.0), (1.0, 1.0))
        )

        instName = list(a.instances.keys())[0]
        inst = a.instances[instName]
        nodes = inst.nodes

        IS_2D = True
        for n in nodes:
            if abs(n.coordinates[2]) > 1e-9:
                IS_2D = False
                break
        print("[INFO] Model:", model_name, "|", ("2D" if IS_2D else "3D"))

        # Bounding box
        xs = [n.coordinates[0] for n in nodes]
        ys = [n.coordinates[1] for n in nodes]
        zs = [n.coordinates[2] for n in nodes]

        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        if IS_2D:
            z0, z1 = 0.0, 0.0
        else:
            z0, z1 = min(zs), max(zs)

        Lx = x1 - x0
        Ly = y1 - y0
        Lz = (z1 - z0) if not IS_2D else 1.0
        Lmax = max(Lx, Ly, (Lz if not IS_2D else 0.0))

        EPS_FACE = BASE_TOL_FACTOR_FACE * Lmax
        print("[INFO] Lx=%.6g Ly=%.6g Lz=%.6g | EPS_FACE=%.3e" % (Lx, Ly, Lz, EPS_FACE))

        cleanup_previous(a, m)

        def flags(n):
            x, y, z = n.coordinates

            at_x0 = bool(is_close(x, x0, EPS_FACE))
            at_x1 = bool(is_close(x, x1, EPS_FACE))
            at_y0 = bool(is_close(y, y0, EPS_FACE))
            at_y1 = bool(is_close(y, y1, EPS_FACE))

            if IS_2D:
                at_z0 = False
                at_z1 = False
            else:
                at_z0 = bool(is_close(z, z0, EPS_FACE))
                at_z1 = bool(is_close(z, z1, EPS_FACE))

            hits = (1 if at_x0 else 0) + (1 if at_x1 else 0) + \
                   (1 if at_y0 else 0) + (1 if at_y1 else 0) + \
                   (1 if at_z0 else 0) + (1 if at_z1 else 0)

            return at_x0, at_x1, at_y0, at_y1, at_z0, at_z1, hits

        def is_corner_node(n):
            *_, hits = flags(n)
            return (hits >= 2) if IS_2D else (hits >= 3)

        def is_edge_node(n):
            if IS_2D:
                return False
            *_, hits = flags(n)
            return hits == 2

        def face_interior(axis, plus=True):
            out = []
            for n in nodes:
                at_x0, at_x1, at_y0, at_y1, at_z0, at_z1, hits = flags(n)

                if axis == "X":
                    on_face = at_x1 if plus else at_x0
                    if on_face and (not at_y0) and (not at_y1) and (not at_z0) and (not at_z1):
                        out.append(n)

                elif axis == "Y":
                    on_face = at_y1 if plus else at_y0
                    if on_face and (not at_x0) and (not at_x1) and (not at_z0) and (not at_z1):
                        out.append(n)

                elif axis == "Z" and (not IS_2D):
                    on_face = at_z1 if plus else at_z0
                    if on_face and (not at_x0) and (not at_x1) and (not at_y0) and (not at_y1):
                        out.append(n)
            return out

        def find_nearest(xc, yc, zc):
            if IS_2D:
                return min(nodes, key=lambda n: (n.coordinates[0]-xc)**2 + (n.coordinates[1]-yc)**2)
            return min(nodes, key=lambda n: (n.coordinates[0]-xc)**2 + (n.coordinates[1]-yc)**2 + (n.coordinates[2]-zc)**2)

        corners = {}
        corners[(0,0,0)] = find_nearest(x0, y0, z0)
        corners[(1,0,0)] = find_nearest(x1, y0, z0)
        corners[(0,1,0)] = find_nearest(x0, y1, z0)
        corners[(1,1,0)] = find_nearest(x1, y1, z0)
        if not IS_2D:
            corners[(0,0,1)] = find_nearest(x0, y0, z1)
            corners[(1,0,1)] = find_nearest(x1, y0, z1)
            corners[(0,1,1)] = find_nearest(x0, y1, z1)
            corners[(1,1,1)] = find_nearest(x1, y1, z1)

        master_corner = corners[(0,0,0)]

        face_Xm_int = face_interior("X", plus=False)
        face_Xp_int = face_interior("X", plus=True)
        face_Ym_int = face_interior("Y", plus=False)
        face_Yp_int = face_interior("Y", plus=True)
        face_Zm_int, face_Zp_int = [], []
        if not IS_2D:
            face_Zm_int = face_interior("Z", plus=False)
            face_Zp_int = face_interior("Z", plus=True)

        print("[INFO] Face-interior nodes:",
              "X-=%d X+=%d" % (len(face_Xm_int), len(face_Xp_int)),
              "Y-=%d Y+=%d" % (len(face_Ym_int), len(face_Yp_int)),
              ("Z-=%d Z+=%d" % (len(face_Zm_int), len(face_Zp_int)) if not IS_2D else ""))

        # Debug sety
        make_set_nodes(a, instName, "FACE_XMINUS_INT", [n.label for n in face_Xm_int])
        make_set_nodes(a, instName, "FACE_XPLUS_INT",  [n.label for n in face_Xp_int])
        make_set_nodes(a, instName, "FACE_YMINUS_INT", [n.label for n in face_Ym_int])
        make_set_nodes(a, instName, "FACE_YPLUS_INT",  [n.label for n in face_Yp_int])
        if not IS_2D:
            make_set_nodes(a, instName, "FACE_ZMINUS_INT", [n.label for n in face_Zm_int])
            make_set_nodes(a, instName, "FACE_ZPLUS_INT",  [n.label for n in face_Zp_int])

        pairsX, statX = pair_faces_unique(face_Xp_int, face_Xm_int, "X", Lmax, MATCH_TOLS)
        pairsY, statY = pair_faces_unique(face_Yp_int, face_Ym_int, "Y", Lmax, MATCH_TOLS)
        if not IS_2D:
            pairsZ, statZ = pair_faces_unique(face_Zp_int, face_Zm_int, "Z", Lmax, MATCH_TOLS)
        else:
            pairsZ, statZ = [], None

        def print_stat(axis, st):
            print("[PAIR]", axis,
                  "pairs=%d unmatched_plus=%d unmatched_minus=%d tol_rel=%s plane_tol=%.3e" %
                  (st["pairs"], st["unmatched_plus"], st["unmatched_minus"],
                   str(st["tol_rel"]), (st["plane_tol"] if st["plane_tol"] else 0.0)))

        print_stat("X_FACE", statX)
        print_stat("Y_FACE", statY)
        if not IS_2D:
            print_stat("Z_FACE", statZ)

        if statX["pairs"] == 0 or statY["pairs"] == 0 or (not IS_2D and statZ["pairs"] == 0):
            raise RuntimeError("FACE-interior pairing resulted in zero pairs - check tolerances or geometry/mesh.")

        edge_pairs = []

        if not IS_2D:
            ex = {'00': [], '10': [], '01': [], '11': []}
            ey = {'00': [], '10': [], '01': [], '11': []}
            ez = {'00': [], '10': [], '01': [], '11': []}

            for n in nodes:
                if not is_edge_node(n):
                    continue
                at_x0, at_x1, at_y0, at_y1, at_z0, at_z1, hits = flags(n)

                if (at_y0 or at_y1) and (at_z0 or at_z1):
                    key = ('1' if at_y1 else '0') + ('1' if at_z1 else '0')
                    ex[key].append(n)

                elif (at_x0 or at_x1) and (at_z0 or at_z1):
                    key = ('1' if at_x1 else '0') + ('1' if at_z1 else '0')
                    ey[key].append(n)

                elif (at_x0 or at_x1) and (at_y0 or at_y1):
                    key = ('1' if at_x1 else '0') + ('1' if at_y1 else '0')
                    ez[key].append(n)

            p_ex10, st_ex10 = pair_edge_unique_1d(ex['10'], ex['00'], 0, Lmax, MATCH_TOLS)
            p_ex01, st_ex01 = pair_edge_unique_1d(ex['01'], ex['00'], 0, Lmax, MATCH_TOLS)
            p_ex11, st_ex11 = pair_edge_unique_1d(ex['11'], ex['00'], 0, Lmax, MATCH_TOLS)

            p_ey10, st_ey10 = pair_edge_unique_1d(ey['10'], ey['00'], 1, Lmax, MATCH_TOLS)
            p_ey01, st_ey01 = pair_edge_unique_1d(ey['01'], ey['00'], 1, Lmax, MATCH_TOLS)
            p_ey11, st_ey11 = pair_edge_unique_1d(ey['11'], ey['00'], 1, Lmax, MATCH_TOLS)

            p_ez10, st_ez10 = pair_edge_unique_1d(ez['10'], ez['00'], 2, Lmax, MATCH_TOLS)
            p_ez01, st_ez01 = pair_edge_unique_1d(ez['01'], ez['00'], 2, Lmax, MATCH_TOLS)
            p_ez11, st_ez11 = pair_edge_unique_1d(ez['11'], ez['00'], 2, Lmax, MATCH_TOLS)

            edge_pairs += [("EX10", p_ex10), ("EX01", p_ex01), ("EX11", p_ex11)]
            edge_pairs += [("EY10", p_ey10), ("EY01", p_ey01), ("EY11", p_ey11)]
            edge_pairs += [("EZ10", p_ez10), ("EZ01", p_ez01), ("EZ11", p_ez11)]

            print("[PAIR] EDGES:",
                  "EX10=%d EX01=%d EX11=%d" % (len(p_ex10), len(p_ex01), len(p_ex11)),
                  "EY10=%d EY01=%d EY11=%d" % (len(p_ey10), len(p_ey01), len(p_ey11)),
                  "EZ10=%d EZ01=%d EZ11=%d" % (len(p_ez10), len(p_ez01), len(p_ez11)))

        corner_pairs = []
        for key, n in corners.items():
            if n.label == master_corner.label:
                continue
            corner_pairs.append((n, master_corner))

        print("[PAIR] CORNERS:", len(corner_pairs), "-> master", master_corner.label)

        cp = ((x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0)
        if IS_2D:
            make_rp_set(a, "RP_E11", (cp[0], cp[1], 0.0))
            make_rp_set(a, "RP_E22", (cp[0], cp[1], 0.0))
            make_rp_set(a, "RP_G12", (cp[0], cp[1], 0.0))
        else:
            make_rp_set(a, "RP_E11", cp)
            make_rp_set(a, "RP_E22", cp)
            make_rp_set(a, "RP_E33", cp)
            make_rp_set(a, "RP_G12", cp)
            make_rp_set(a, "RP_G13", cp)
            make_rp_set(a, "RP_G23", cp)

        node_set_cache = set()

        def get_node_set_name(label):
            return "NODE_%d" % label

        def ensure_node_set(node):
            sname = get_node_set_name(node.label)
            if sname in node_set_cache:
                return sname

            if repo_has(a.sets, sname):
                node_set_cache.add(sname)
                return sname

            a.SetFromNodeLabels(name=sname, nodeLabels=((instName, [node.label]),))
            node_set_cache.add(sname)
            return sname

        def eq(name, terms):
            repo_del(m.constraints, name)
            m.Equation(name=name, terms=terms)

        def apply_pbc_full(pairs, tag):
            for (np_, nm_) in pairs:
                dx = np_.coordinates[0] - nm_.coordinates[0]
                dy = np_.coordinates[1] - nm_.coordinates[1]
                dz = (np_.coordinates[2] - nm_.coordinates[2]) if not IS_2D else 0.0

                s_np = ensure_node_set(np_)
                s_nm = ensure_node_set(nm_)

                if IS_2D:
                    terms_u1 = (
                        ( 1.0, s_np, 1), (-1.0, s_nm, 1),
                        (-dx, "RP_E11", 1),
                        (-(dy * 0.5), "RP_G12", 1),
                    )
                    terms_u2 = (
                        ( 1.0, s_np, 2), (-1.0, s_nm, 2),
                        (-dy, "RP_E22", 1),
                        (-(dx * 0.5), "RP_G12", 1),
                    )
                    eq("PBC_%s_U1_%d_%d" % (tag, np_.label, nm_.label), terms_u1)
                    eq("PBC_%s_U2_%d_%d" % (tag, np_.label, nm_.label), terms_u2)
                else:
                    terms_u1 = (
                        ( 1.0, s_np, 1), (-1.0, s_nm, 1),
                        (-dx, "RP_E11", 1),
                        (-(dy * 0.5), "RP_G12", 1),
                        (-(dz * 0.5), "RP_G13", 1),
                    )
                    terms_u2 = (
                        ( 1.0, s_np, 2), (-1.0, s_nm, 2),
                        (-dy, "RP_E22", 1),
                        (-(dx * 0.5), "RP_G12", 1),
                        (-(dz * 0.5), "RP_G23", 1),
                    )
                    terms_u3 = (
                        ( 1.0, s_np, 3), (-1.0, s_nm, 3),
                        (-dz, "RP_E33", 1),
                        (-(dx * 0.5), "RP_G13", 1),
                        (-(dy * 0.5), "RP_G23", 1),
                    )
                    eq("PBC_%s_U1_%d_%d" % (tag, np_.label, nm_.label), terms_u1)
                    eq("PBC_%s_U2_%d_%d" % (tag, np_.label, nm_.label), terms_u2)
                    eq("PBC_%s_U3_%d_%d" % (tag, np_.label, nm_.label), terms_u3)

        apply_pbc_full(pairsX, "XF")
        apply_pbc_full(pairsY, "YF")
        if not IS_2D:
            apply_pbc_full(pairsZ, "ZF")

        if not IS_2D:
            for tag, plist in edge_pairs:
                if plist:
                    apply_pbc_full(plist, tag)

        if corner_pairs:
            apply_pbc_full(corner_pairs, "C")

        print("[INFO] PBC equations applied: FACE-interior + EDGES + CORNERS (no DOF duplicates).")

        make_set_nodes(a, instName, "MASTER_CORNER", [master_corner.label])

        repo_del(m.boundaryConditions, "BC_CORNER_FIX")

        if IS_2D:
            m.DisplacementBC(name="BC_CORNER_FIX", createStepName="Initial",
                             region=a.sets["MASTER_CORNER"], u1=0.0, u2=0.0)
        else:
            m.DisplacementBC(name="BC_CORNER_FIX", createStepName="Initial",
                             region=a.sets["MASTER_CORNER"], u1=0.0, u2=0.0, u3=0.0)

        for sname in list(m.steps.keys()):
            if sname != "Initial" and sname != STEP_NAME:
                if sname.startswith("Step-PBC"):
                    try:
                        del m.steps[sname]
                    except:
                        pass

        if STEP_NAME in m.steps:
            step = m.steps[STEP_NAME]
            step.setValues(
                timePeriod=TIME_PERIOD,
                maxNumInc=MAX_NUM_INC,
                initialInc=INITIAL_INC,
                minInc=MIN_INC,
                maxInc=MAX_INC,
                nlgeom=ON
            )

        else:
            step = m.StaticStep(
                name=STEP_NAME, previous="Initial",
                timePeriod=TIME_PERIOD,
                maxNumInc=MAX_NUM_INC,
                initialInc=INITIAL_INC,
                minInc=MIN_INC,
                maxInc=MAX_INC,
                nlgeom=ON
            )

        for rname in list(m.fieldOutputRequests.keys()):
            try: del m.fieldOutputRequests[rname]
            except: pass
        for rname in list(m.historyOutputRequests.keys()):
            try: del m.historyOutputRequests[rname]
            except: pass

        m.FieldOutputRequest(
            name="F-Output-1",
            createStepName=STEP_NAME,
            variables=("COORD", "U", "S", "PE", "PEEQ", "EVOL"),
            numIntervals=NUM_INTERVALS

        )

        def add_rp_hist(req_name, set_name):
            m.HistoryOutputRequest(
                name=req_name,
                createStepName=STEP_NAME,
                variables=("U1", "RF1"),
                region=a.sets[set_name],
                numIntervals=NUM_INTERVALS

            )

        m.HistoryOutputRequest(
            name="H_ALLPD",
            createStepName=STEP_NAME,
            variables=("ALLPD",),
            region=MODEL,
            numIntervals=NUM_INTERVALS
        )

        if IS_2D:
            add_rp_hist("H_RP_E11", "RP_E11")
            add_rp_hist("H_RP_E22", "RP_E22")
            add_rp_hist("H_RP_G12", "RP_G12")
        else:
            add_rp_hist("H_RP_E11", "RP_E11")
            add_rp_hist("H_RP_E22", "RP_E22")
            add_rp_hist("H_RP_E33", "RP_E33")
            add_rp_hist("H_RP_G12", "RP_G12")
            add_rp_hist("H_RP_G13", "RP_G13")
            add_rp_hist("H_RP_G23", "RP_G23")

        def apply_macro_bc(step_name, exx=0.0, eyy=0.0, ezz=0.0, g12=0.0, g13=0.0, g23=0.0):
            bc_names = []

            def _bc(bc_name, set_name, val):
                repo_del(m.boundaryConditions, bc_name)
                m.DisplacementBC(
                    name=bc_name,
                    createStepName=step_name,
                    region=a.sets[set_name],
                    u1=float(val),
                    amplitude=AMP_NAME,
                )

                bc_names.append(bc_name)

            if IS_2D:
                _bc("BC_E11", "RP_E11", exx)
                _bc("BC_E22", "RP_E22", eyy)
                _bc("BC_G12", "RP_G12", g12)
            else:
                _bc("BC_E11", "RP_E11", exx)
                _bc("BC_E22", "RP_E22", eyy)
                _bc("BC_E33", "RP_E33", ezz)
                _bc("BC_G12", "RP_G12", g12)
                _bc("BC_G13", "RP_G13", g13)
                _bc("BC_G23", "RP_G23", g23)

            return bc_names

        def clear_bcs(bc_names):
            for nm in bc_names:
                repo_del(m.boundaryConditions, nm)

        def generate_lode_directions(theta_vals_deg, eps_dev_vals, eps_hydro_vals):
            dirs = []
            for eps_h in eps_hydro_vals:
                for eps_dev in eps_dev_vals:
                    for th_deg in theta_vals_deg:
                        th = np.deg2rad(th_deg)
                        exx = float(eps_dev * np.cos(th) + eps_h)
                        eyy = float(eps_dev * np.cos(th - 2.0 * np.pi / 3.0) + eps_h)
                        ezz = float(eps_dev * np.cos(th + 2.0 * np.pi / 3.0) + eps_h)
                        dirs.append((exx, eyy, ezz))
            return dirs

        theta_vals = np.linspace(0.0, THETA_MAX, THETA_COUNT, endpoint=False)
        n_hydro = N_HYDRO
        n_dev = N_DEV

        h_max = 0.20 * EPS_MAX

        if n_hydro == 1:
            eps_hydro_vals = [0.0]
        else:
            eps_hydro_vals = np.linspace(-h_max, h_max, n_hydro)

        dev_min0 = 0.40 * EPS_MAX
        dev_max0 = 1.25 * EPS_MAX

        k_pos = 0.55
        k_neg = 0.10

        p = 1.8

        if n_dev == 1:
            t = np.array([1.0], dtype=float)
        else:
            t = np.linspace(0.0, 1.0, n_dev) ** p

        dirs = []
        for eps_h in eps_hydro_vals:
            r = abs(eps_h) / h_max if h_max > 0 else 0.0

            if eps_h > 0:
                scale = 1.0 + k_pos * (r ** 1.7)

                dev_min_boost = 0.15 * r
            elif eps_h < 0:
                scale = 1.0 + k_neg * (r ** 1.2)
                dev_min_boost = 0.00
            else:
                scale = 1.0
                dev_min_boost = 0.00

            scale = min(scale, 1.80)

            dev_min = dev_min0 * (scale * (1.0 + dev_min_boost))
            dev_max = dev_max0 * scale

            eps_dev_vals = (dev_min + (dev_max - dev_min) * t).tolist()

            dirs += generate_lode_directions(
                theta_vals_deg=theta_vals,
                eps_dev_vals=eps_dev_vals,
                eps_hydro_vals=[eps_h]
            )

        if IS_2D:
            shear_dirs = [
                (0.0, 0.0, 0.0, 0.50 * EPS_MAX),
                (0.0, 0.0, 0.0, 1.00 * EPS_MAX),
                (0.0, 0.0, 0.0, 1.50 * EPS_MAX),
            ]
        else:
            shear_dirs = [
                (0.0, 0.0, 0.0, 1.00 * EPS_MAX, 0.0, 0.0),
                (0.0, 0.0, 0.0, 0.0, 1.00 * EPS_MAX, 0.0),
                (0.0, 0.0, 0.0, 0.0, 0.0, 1.00 * EPS_MAX),
                (0.0, 0.0, 0.0, 0.80 * EPS_MAX, 0.80 * EPS_MAX, 0.80 * EPS_MAX),
            ]

        expected_total = len(dirs) + len(shear_dirs)
        digits = max(3, len(str(expected_total)))
        print("[INFO] Jobs to generate:", expected_total)

        job_counter = 0

        for (exx, eyy, ezz) in dirs:
            job_counter += 1
            bc_names = apply_macro_bc(STEP_NAME, exx=exx, eyy=eyy, ezz=ezz, g12=0.0, g13=0.0, g23=0.0)

            counter = str(job_counter).zfill(digits)
            job_name = "%s_%s" % (model_name, counter)

            repo_del(mdb.jobs, job_name)

            job = mdb.Job(name=job_name, model=model_name)
            print("[INP] Writing:", job_name)
            job.writeInput()

            clear_bcs(bc_names)

        for item in shear_dirs:
            job_counter += 1

            if IS_2D:
                exx, eyy, ezz, g12 = item
                bc_names = apply_macro_bc(STEP_NAME, exx=exx, eyy=eyy, g12=g12)
            else:
                exx, eyy, ezz, g12, g13, g23 = item
                bc_names = apply_macro_bc(STEP_NAME, exx=exx, eyy=eyy, ezz=ezz, g12=g12, g13=g13, g23=g23)

            counter = str(job_counter).zfill(digits)
            job_name = "%s_%s" % (model_name, counter)

            repo_del(mdb.jobs, job_name)

            job = mdb.Job(name=job_name, model=model_name)
            print("[INP] Writing:", job_name)
            job.writeInput()

            clear_bcs(bc_names)

        print("[INFO] DONE. INP files are in:", os.getcwd())
    except Exception:
        traceback.print_exc()
        raise
