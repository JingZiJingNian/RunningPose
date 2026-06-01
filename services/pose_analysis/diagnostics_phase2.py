from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np


def _safe_metric_value(metrics: Dict[str, Any], key: str) -> Optional[float]:
    item = metrics.get(key)
    if isinstance(item, dict):
        value = item.get("value")
        if value is None:
            return None
        try:
            fv = float(value)
            if np.isfinite(fv):
                return fv
        except Exception:
            return None
    return None


def _severity_from_ratio_and_excess(step_ratio: float, excess: float, low_thr: float, high_thr: float) -> str:
    if step_ratio >= 0.70 and excess >= high_thr:
        return "high"
    if step_ratio >= 0.40 and excess >= low_thr:
        return "medium"
    return "low"


def _top_supporting_steps(values: List[tuple], top_k: int = 8) -> List[int]:
    values = sorted(values, key=lambda x: x[1], reverse=True)
    out = []
    for step_idx, _ in values[:top_k]:
        try:
            out.append(int(step_idx))
        except Exception:
            continue
    return out


def _mean_of_side(step_records: List[Dict[str, Any]], side: str, key: str) -> Optional[float]:
    vals = []
    for rec in step_records:
        if rec.get("side") != side:
            continue
        v = rec.get(key)
        if v is None:
            continue
        try:
            fv = float(v)
        except Exception:
            continue
        if np.isfinite(fv):
            vals.append(fv)
    if not vals:
        return None
    return float(np.mean(vals))


def _relative_diff(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None:
        return None
    denom = max((abs(a) + abs(b)) / 2.0, 1e-6)
    return float(abs(a - b) / denom)


def _safe_issue(
    *,
    issue_type: str,
    severity: str,
    confidence: float,
    phase: str,
    message: str,
    suggestion: str,
    evidence: Dict[str, Any],
    step_ratio: Optional[float],
    supporting_step_indices: List[int],
) -> Dict[str, Any]:
    return {
        "type": str(issue_type),
        "severity": str(severity),
        "confidence": round(float(confidence), 3),
        "phase": str(phase),
        "message": str(message),
        "suggestion": str(suggestion),
        "evidence": evidence or {},
        "step_ratio": round(float(step_ratio), 4) if step_ratio is not None else None,
        "supporting_step_indices": [int(x) for x in supporting_step_indices],
    }


def diagnose_overstride(step_records: List[Dict[str, Any]], metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not step_records:
        return []

    osi_values = []
    supporting = []

    for rec in step_records:
        val = rec.get("overstride_index")
        if val is None:
            continue
        try:
            v = float(val)
        except Exception:
            continue
        if not np.isfinite(v):
            continue
        step_idx = int(rec.get("step_index", 0))
        osi_values.append((step_idx, v))
        if v > 0.30:
            supporting.append((step_idx, v))

    if len(osi_values) < 4:
        return []

    raw_vals = np.array([v for _, v in osi_values], dtype=float)
    mean_osi = float(np.mean(raw_vals))
    step_ratio = float(np.mean(raw_vals > 0.30))
    event_conf = float(metrics.get("event_summary", {}).get("event_confidence", 0.0))

    cadence = _safe_metric_value(metrics, "cadence")
    gct = _safe_metric_value(metrics, "ground_contact_time")

    aux_bonus = 0.0
    if cadence is not None and cadence < 160:
        aux_bonus += 0.08
    if gct is not None and gct > 280:
        aux_bonus += 0.08

    is_positive = (mean_osi > 0.30 and step_ratio >= 0.35) or (step_ratio >= 0.50)
    if not is_positive:
        return []

    confidence = min(
        1.0,
        0.65 * event_conf
        + 0.20 * step_ratio
        + 0.15 * min(max(mean_osi - 0.30, 0.0) / 0.12, 1.0)
        + aux_bonus,
    )

    severity = _severity_from_ratio_and_excess(step_ratio, max(mean_osi - 0.30, 0.0), 0.03, 0.08)

    return [_safe_issue(
        issue_type="overstride",
        severity=severity,
        confidence=confidence,
        phase="initial_contact",
        message=f"存在过度跨步倾向（步级均值 {mean_osi:.3f}，异常步占比 {step_ratio:.0%}）",
        suggestion="优先尝试提高步频、减少触地瞬间脚向身体前方的前伸距离，让落脚点更接近身体重心下方。",
        evidence={
            "overstride_index_mean": round(mean_osi, 4),
            "overstride_step_ratio": round(step_ratio, 4),
            "cadence_value": cadence,
            "ground_contact_time_value": gct,
            "event_confidence": round(event_conf, 4),
        },
        step_ratio=step_ratio,
        supporting_step_indices=_top_supporting_steps(supporting, top_k=8),
    )]


def diagnose_long_ground_contact(step_records: List[Dict[str, Any]], metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not step_records:
        return []

    stance_values = []
    supporting = []

    for rec in step_records:
        val = rec.get("stance_duration_ms")
        if val is None:
            continue
        try:
            v = float(val)
        except Exception:
            continue
        if not np.isfinite(v):
            continue
        step_idx = int(rec.get("step_index", 0))
        stance_values.append((step_idx, v))
        if v > 280:
            supporting.append((step_idx, v))

    if len(stance_values) < 4:
        return []

    raw_vals = np.array([v for _, v in stance_values], dtype=float)
    mean_stance = float(np.mean(raw_vals))
    p90_stance = float(np.percentile(raw_vals, 90))
    step_ratio = float(np.mean(raw_vals > 280))
    event_conf = float(metrics.get("event_summary", {}).get("event_confidence", 0.0))

    cadence = _safe_metric_value(metrics, "cadence")
    overstride = _safe_metric_value(metrics, "overstride_index")

    aux_bonus = 0.0
    if cadence is not None and cadence < 160:
        aux_bonus += 0.06
    if overstride is not None and overstride > 0.30:
        aux_bonus += 0.06

    is_positive = (mean_stance > 280 and step_ratio >= 0.30) or (p90_stance > 320 and step_ratio >= 0.25)
    if not is_positive:
        return []

    confidence = min(
        1.0,
        0.65 * event_conf
        + 0.20 * step_ratio
        + 0.15 * min(max(mean_stance - 280, 0.0) / 80.0, 1.0)
        + aux_bonus,
    )

    severity = _severity_from_ratio_and_excess(step_ratio, max(mean_stance - 280, 0.0), 15.0, 40.0)

    return [_safe_issue(
        issue_type="long_ground_contact",
        severity=severity,
        confidence=confidence,
        phase="stance",
        message=f"触地时间整体偏长（步级均值 {mean_stance:.1f} ms，异常步占比 {step_ratio:.0%}）",
        suggestion="建议结合步频与落脚位置一起优化，避免支撑期拖沓；可通过更轻快的步频和更紧凑的触地策略改善回弹效率。",
        evidence={
            "stance_mean_ms": round(mean_stance, 3),
            "stance_p90_ms": round(p90_stance, 3),
            "long_contact_step_ratio": round(step_ratio, 4),
            "cadence_value": cadence,
            "overstride_index_value": overstride,
            "event_confidence": round(event_conf, 4),
        },
        step_ratio=step_ratio,
        supporting_step_indices=_top_supporting_steps(supporting, top_k=8),
    )]


def diagnose_excessive_trunk_lean(step_records: List[Dict[str, Any]], metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not step_records:
        return []

    lean_values = []
    supporting = []

    for rec in step_records:
        mean_deg = rec.get("trunk_lean_mean_deg")
        if mean_deg is None:
            continue
        try:
            v = float(mean_deg)
        except Exception:
            continue
        if not np.isfinite(v):
            continue
        step_idx = int(rec.get("step_index", 0))
        lean_values.append((step_idx, v))
        if v > 15:
            supporting.append((step_idx, v))

    if len(lean_values) < 4:
        return []

    raw_vals = np.array([v for _, v in lean_values], dtype=float)
    mean_lean = float(np.mean(raw_vals))
    std_lean = float(np.std(raw_vals))
    step_ratio = float(np.mean(raw_vals > 15))
    event_conf = float(metrics.get("event_summary", {}).get("event_confidence", 0.0))

    overstride = _safe_metric_value(metrics, "overstride_index")

    aux_bonus = 0.0
    if overstride is not None and overstride > 0.30:
        aux_bonus += 0.05

    is_positive = (mean_lean > 15 and step_ratio >= 0.30) or (step_ratio >= 0.50)
    if not is_positive:
        return []

    confidence = min(
        1.0,
        0.70 * event_conf
        + 0.20 * step_ratio
        + 0.10 * min(max(mean_lean - 15, 0.0) / 8.0, 1.0)
        + aux_bonus,
    )

    severity = _severity_from_ratio_and_excess(step_ratio, max(mean_lean - 15, 0.0), 2.0, 5.0)

    return [_safe_issue(
        issue_type="excessive_trunk_lean",
        severity=severity,
        confidence=confidence,
        phase="global",
        message=f"躯干前倾整体偏大（步级均值 {mean_lean:.1f}°，异常步占比 {step_ratio:.0%}）",
        suggestion="注意区分“整体前倾”和“折腰式前倾”。建议增强核心支撑与髋部驱动，避免上身过早向前折叠。",
        evidence={
            "trunk_lean_mean_deg": round(mean_lean, 3),
            "trunk_lean_std_deg": round(std_lean, 3),
            "excessive_lean_step_ratio": round(step_ratio, 4),
            "overstride_index_value": overstride,
            "event_confidence": round(event_conf, 4),
        },
        step_ratio=step_ratio,
        supporting_step_indices=_top_supporting_steps(supporting, top_k=8),
    )]


def diagnose_excessive_vertical_oscillation(step_records: List[Dict[str, Any]], metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not step_records:
        return []

    vo_values = []
    supporting = []

    for rec in step_records:
        val = rec.get("vertical_oscillation_local")
        if val is None:
            continue
        try:
            v = float(val)
        except Exception:
            continue
        if not np.isfinite(v):
            continue
        step_idx = int(rec.get("step_index", 0))
        vo_values.append((step_idx, v))
        if v > 0.14:
            supporting.append((step_idx, v))

    if len(vo_values) < 4:
        return []

    raw_vals = np.array([v for _, v in vo_values], dtype=float)
    mean_vo = float(np.mean(raw_vals))
    step_ratio = float(np.mean(raw_vals > 0.14))
    event_conf = float(metrics.get("event_summary", {}).get("event_confidence", 0.0))

    cadence = _safe_metric_value(metrics, "cadence")
    gct = _safe_metric_value(metrics, "ground_contact_time")
    global_vo = _safe_metric_value(metrics, "vertical_oscillation_rel")

    aux_bonus = 0.0
    if cadence is not None and cadence < 160:
        aux_bonus += 0.05
    if gct is not None and gct > 280:
        aux_bonus += 0.05

    is_positive = (mean_vo > 0.14 and step_ratio >= 0.30) or (step_ratio >= 0.50)
    if not is_positive:
        return []

    confidence = min(
        1.0,
        0.65 * event_conf
        + 0.20 * step_ratio
        + 0.15 * min(max(mean_vo - 0.14, 0.0) / 0.08, 1.0)
        + aux_bonus,
    )

    severity = _severity_from_ratio_and_excess(step_ratio, max(mean_vo - 0.14, 0.0), 0.015, 0.04)

    return [_safe_issue(
        issue_type="excessive_vertical_oscillation",
        severity=severity,
        confidence=confidence,
        phase="global",
        message=f"垂直振幅偏大（步级均值 {mean_vo:.3f}，异常步占比 {step_ratio:.0%}）",
        suggestion="建议减少上下弹跳，优化向前推进效率；通常应结合步频和触地时间一起调整，而不是单独追求更低的起伏。",
        evidence={
            "vertical_oscillation_local_mean": round(mean_vo, 4),
            "vertical_oscillation_step_ratio": round(step_ratio, 4),
            "vertical_oscillation_global_value": global_vo,
            "cadence_value": cadence,
            "ground_contact_time_value": gct,
            "event_confidence": round(event_conf, 4),
        },
        step_ratio=step_ratio,
        supporting_step_indices=_top_supporting_steps(supporting, top_k=8),
    )]


def diagnose_low_cadence(step_records: List[Dict[str, Any]], metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    cadence = _safe_metric_value(metrics, "cadence")
    if cadence is None:
        return []

    inst_vals = []
    supporting = []

    for rec in step_records:
        val = rec.get("instant_cadence_spm")
        if val is None:
            continue
        try:
            v = float(val)
        except Exception:
            continue
        if not np.isfinite(v):
            continue
        step_idx = int(rec.get("step_index", 0))
        inst_vals.append((step_idx, v))
        if v < 160:
            supporting.append((step_idx, 160 - v))

    if len(inst_vals) < 4:
        return []

    raw_vals = np.array([v for _, v in inst_vals], dtype=float)
    step_ratio = float(np.mean(raw_vals < 160))
    mean_inst = float(np.mean(raw_vals))
    event_conf = float(metrics.get("event_summary", {}).get("event_confidence", 0.0))

    overstride = _safe_metric_value(metrics, "overstride_index")
    gct = _safe_metric_value(metrics, "ground_contact_time")

    aux_bonus = 0.0
    if overstride is not None and overstride > 0.30:
        aux_bonus += 0.06
    if gct is not None and gct > 280:
        aux_bonus += 0.06

    is_positive = (cadence < 160 and step_ratio >= 0.40) or (cadence < 155)
    if not is_positive:
        return []

    confidence = min(
        1.0,
        0.70 * event_conf
        + 0.15 * step_ratio
        + 0.15 * min(max(160 - cadence, 0.0) / 20.0, 1.0)
        + aux_bonus,
    )

    severity = _severity_from_ratio_and_excess(step_ratio, max(160 - cadence, 0.0), 3.0, 8.0)

    return [_safe_issue(
        issue_type="low_cadence",
        severity=severity,
        confidence=confidence,
        phase="global",
        message=f"步频整体偏低（摘要值 {cadence:.1f} spm，低步频步占比 {step_ratio:.0%}）",
        suggestion="建议优先通过小幅、渐进的方式提高步频，不要用刻意加速摆腿来硬拉节奏；更合理的是让落脚更轻、更紧凑。",
        evidence={
            "cadence_value": round(cadence, 3),
            "instant_cadence_mean": round(mean_inst, 3),
            "low_cadence_step_ratio": round(step_ratio, 4),
            "overstride_index_value": overstride,
            "ground_contact_time_value": gct,
            "event_confidence": round(event_conf, 4),
        },
        step_ratio=step_ratio,
        supporting_step_indices=_top_supporting_steps(supporting, top_k=8),
    )]


def diagnose_left_right_asymmetry(step_records: List[Dict[str, Any]], metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not step_records:
        return []

    left_n = sum(1 for r in step_records if r.get("side") == "L")
    right_n = sum(1 for r in step_records if r.get("side") == "R")
    if left_n < 2 or right_n < 2:
        return []

    left_stance = _mean_of_side(step_records, "L", "stance_duration_ms")
    right_stance = _mean_of_side(step_records, "R", "stance_duration_ms")

    left_overstride = _mean_of_side(step_records, "L", "overstride_index")
    right_overstride = _mean_of_side(step_records, "R", "overstride_index")

    left_trunk = _mean_of_side(step_records, "L", "trunk_lean_mean_deg")
    right_trunk = _mean_of_side(step_records, "R", "trunk_lean_mean_deg")

    stance_asym = _relative_diff(left_stance, right_stance)
    overstride_asym = _relative_diff(left_overstride, right_overstride)
    trunk_asym = _relative_diff(left_trunk, right_trunk)

    valid_asym = [v for v in [stance_asym, overstride_asym, trunk_asym] if v is not None]
    if not valid_asym:
        return []

    asym_score = float(np.mean(valid_asym))
    event_conf = float(metrics.get("event_summary", {}).get("event_confidence", 0.0))

    is_positive = asym_score > 0.12 or (stance_asym is not None and stance_asym > 0.15)
    if not is_positive:
        return []

    confidence = min(1.0, 0.75 * event_conf + 0.25 * min(asym_score / 0.30, 1.0))
    severity = "high" if asym_score > 0.25 else "medium" if asym_score > 0.16 else "low"

    supporting = []
    for rec in step_records:
        side = rec.get("side")
        score = 0.0

        if left_stance is not None and right_stance is not None:
            ref = left_stance if side == "L" else right_stance
            other = right_stance if side == "L" else left_stance
            score += abs(ref - other)

        if left_overstride is not None and right_overstride is not None:
            ref = left_overstride if side == "L" else right_overstride
            other = right_overstride if side == "L" else left_overstride
            score += abs(ref - other)

        if score > 0:
            supporting.append((int(rec.get("step_index", 0)), score))

    return [_safe_issue(
        issue_type="left_right_asymmetry",
        severity=severity,
        confidence=confidence,
        phase="global",
        message=f"左右侧动作存在不对称倾向（综合不对称度 {asym_score:.2f}）",
        suggestion="建议重点观察左右脚支撑时间、落脚位置和上身控制是否一致。若不对称持续存在，应优先排查单侧力量或稳定性差异。",
        evidence={
            "stance_asymmetry": round(stance_asym, 4) if stance_asym is not None else None,
            "overstride_asymmetry": round(overstride_asym, 4) if overstride_asym is not None else None,
            "trunk_asymmetry": round(trunk_asym, 4) if trunk_asym is not None else None,
            "left_stance_mean_ms": round(left_stance, 3) if left_stance is not None else None,
            "right_stance_mean_ms": round(right_stance, 3) if right_stance is not None else None,
            "left_overstride_mean": round(left_overstride, 4) if left_overstride is not None else None,
            "right_overstride_mean": round(right_overstride, 4) if right_overstride is not None else None,
            "event_confidence": round(event_conf, 4),
        },
        step_ratio=None,
        supporting_step_indices=_top_supporting_steps(supporting, top_k=8),
    )]


def diagnose_phase2_issues(step_records: List[Dict[str, Any]], metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    issues.extend(diagnose_overstride(step_records, metrics))
    issues.extend(diagnose_long_ground_contact(step_records, metrics))
    issues.extend(diagnose_excessive_trunk_lean(step_records, metrics))
    issues.extend(diagnose_excessive_vertical_oscillation(step_records, metrics))
    issues.extend(diagnose_low_cadence(step_records, metrics))
    issues.extend(diagnose_left_right_asymmetry(step_records, metrics))

    severity_rank = {"high": 3, "medium": 2, "low": 1}
    issues.sort(
        key=lambda x: (
            severity_rank.get(x.get("severity", "low"), 1),
            float(x.get("confidence", 0.0)),
        ),
        reverse=True,
    )
    return issues