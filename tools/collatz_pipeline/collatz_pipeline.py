# -*- coding: utf-8 -*-
"""
Collatz 预测-验证-对账管线（Prediction-Verification-Reconciliation Pipeline）
==============================================================================
核心思想：LLM 对 Collatz 区间行为先写"数值预测"，验证器（numba）跑真实值，
对账算偏差，偏差回灌校准下一轮。让 LLM 的"本体论意外"显式化、可量化。

用法：
  python collatz_pipeline.py --verify                 # 跑验证器，写 truths.json
  python collatz_pipeline.py --reconcile --round 1    # 读 predictions_round1.json 对账
  python collatz_pipeline.py --reconcile --round 2    # 读 predictions_round2.json 对账
  python collatz_pipeline.py --questions              # 打印问题集（给 LLM 用）

输出：
  truths.json                真实值
  report_roundN.json/md      偏差报告
  calibration.png            predicted vs actual 散点（含两轮对比）
"""
import json, os, sys, argparse
import numpy as np
import numba
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# 问题集：10 个跨量级区间（固定，可复现）
# ---------------------------------------------------------------------------

QUESTIONS = [
    {"id": 1, "lo": 999,       "hi": 2000,      "label": "1e3 附近"},
    {"id": 2, "lo": 27000,     "hi": 28000,     "label": "2.7e4（27 倍数带）"},
    {"id": 3, "lo": 99991,     "hi": 100010,    "label": "1e5 附近"},
    {"id": 4, "lo": 499999,    "hi": 500100,    "label": "5e5 附近"},
    {"id": 5, "lo": 999991,    "hi": 1000100,   "label": "1e6 附近"},
    {"id": 6, "lo": 4999999,   "hi": 5000100,   "label": "5e6 附近"},
    {"id": 7, "lo": 9999991,   "hi": 10000100,  "label": "1e7 附近"},
    {"id": 8, "lo": 63728120,  "hi": 63728135,  "label": "含记录保持者 63728127"},
    {"id": 9, "lo": 49999991,  "hi": 50000100,  "label": "5e7 附近"},
    {"id": 10,"lo": 99999991,  "hi": 100000100, "label": "1e8 附近"},
]

MAX_N = max(q["hi"] for q in QUESTIONS)  # 1.000001e8


# ---------------------------------------------------------------------------
# 验证器：numba 一次算到 MAX_N，按区间切片统计
# ---------------------------------------------------------------------------

@numba.njit
def compute_stopping_upto(N, max_chain):
    """返回 stop[0..N]，stop[n] = n 的停滞时间（到达 1 的步数），-1=未定义。"""
    stop = np.full(N + 1, -1, dtype=np.int64)
    stop[1] = 0
    chain = np.empty(max_chain, dtype=np.int64)
    for i in range(2, N + 1):
        if stop[i] != -1:
            continue
        n = i
        length = 0
        while True:
            if n <= N and stop[n] != -1:
                s = stop[n]
                break
            chain[length] = n
            length += 1
            if n % 2 == 0:
                n = n // 2
            else:
                n = 3 * n + 1
        for k in range(length - 1, -1, -1):
            s += 1
            x = chain[k]
            if x <= N:
                stop[x] = s
    return stop


def compute_truths():
    print(f"验证器: 计算 1..{MAX_N:,} 的停滞时间...", flush=True)
    stop = compute_stopping_upto(MAX_N, 5_000_000)
    truths = []
    for q in QUESTIONS:
        lo, hi = q["lo"], q["hi"]
        seg = stop[lo:hi + 1]
        truths.append({
            "id": q["id"],
            "lo": lo, "hi": hi,
            "max_stopping": int(seg.max()),
            "min_stopping": int(seg.min()),
            "mean_stopping": float(seg.mean()),
            "median_stopping": float(np.median(seg)),
            "argmax_n": int(lo + int(np.argmax(seg))),
            "all_reach_one": bool(np.all(seg >= 0)),
            "n_samples": int(hi - lo + 1),
        })
    with open(os.path.join(BASE, "truths.json"), "w", encoding="utf-8") as f:
        json.dump(truths, f, ensure_ascii=False, indent=2)
    print(f"真实值已写 truths.json（{len(truths)} 区间）", flush=True)
    for t in truths:
        print(f"  [{t['lo']:>10,}, {t['hi']:>10,}] max={t['max_stopping']:>4} (n={t['argmax_n']:,}) "
              f"mean={t['mean_stopping']:.1f} median={t['median_stopping']:.0f} all1={t['all_reach_one']}", flush=True)
    return truths


# ---------------------------------------------------------------------------
# 对账器：LLM 预测 vs 真实值
# ---------------------------------------------------------------------------

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def reconcile(round_no):
    preds_path = os.path.join(BASE, f"predictions_round{round_no}.json")
    truths_path = os.path.join(BASE, "truths.json")
    if not os.path.exists(preds_path):
        print(f"找不到 {preds_path} —— 先让 LLM 生成预测再对账")
        return
    preds = load_json(preds_path)
    truths = load_json(truths_path)
    if isinstance(preds, dict) and "predictions" in preds:
        preds = preds["predictions"]
    pmap = {p["id"]: p for p in preds}
    tmap = {t["id"]: t for t in truths}

    rows = []
    tot_max_err = 0.0
    tot_mean_err = 0.0
    n = 0
    for q in QUESTIONS:
        pid = q["id"]
        p = pmap.get(pid)
        t = tmap.get(pid)
        if p is None or t is None:
            continue
        # 预测字段兼容别名
        p_max = p.get("max_stopping", p.get("max_stopping_pred"))
        p_mean = p.get("mean_stopping", p.get("mean_stopping_pred"))
        p_all = p.get("all_reach_one", p.get("all_reach_one_pred", True))
        conf = p.get("confidence", "?")
        reason = p.get("reasoning", "")

        max_err = abs(p_max - t["max_stopping"]) / t["max_stopping"] * 100 if p_max is not None else None
        mean_err = abs(p_mean - t["mean_stopping"]) / t["mean_stopping"] * 100 if p_mean is not None else None
        all_ok = (p_all == t["all_reach_one"])
        if max_err is not None:
            tot_max_err += max_err
        if mean_err is not None:
            tot_mean_err += mean_err
        n += 1
        rows.append({
            "id": pid, "label": q["label"], "lo": q["lo"], "hi": q["hi"],
            "pred_max": p_max, "true_max": t["max_stopping"], "max_err_pct": max_err,
            "pred_mean": p_mean, "true_mean": t["mean_stopping"], "mean_err_pct": mean_err,
            "pred_all1": p_all, "true_all1": t["all_reach_one"], "all1_ok": all_ok,
            "confidence": conf, "reasoning": reason,
        })

    # 报告
    md_lines = [f"# Collatz 预测-验证对账 · Round {round_no}", ""]
    md_lines.append(f"| # | 区间 | 预测最大 | 实际最大 | 误差% | 预测均值 | 实际均值 | 误差% | 全到1 | 置信度 |")
    md_lines.append(f"|---|------|--------|--------|------|--------|--------|------|------|--------|")
    for r in rows:
        md_lines.append(
            f"| {r['id']} | {r['label']} | {r['pred_max']} | {r['true_max']} | "
            f"{r['max_err_pct']:.1f} | {r['pred_mean']:.0f} | {r['true_mean']:.1f} | "
            f"{r['mean_err_pct']:.1f} | {'✅' if r['all1_ok'] else '❌'} | {r['confidence']} |")
    n = max(n, 1)
    avg_max_err = tot_max_err / n
    avg_mean_err = tot_mean_err / n
    md_lines.append("")
    md_lines.append(f"**平均最大停滞误差: {avg_max_err:.1f}%**  |  **平均均值停滞误差: {avg_mean_err:.1f}%**")
    md_lines.append("")
    md_lines.append("## 打脸记录（高置信度但误差大）")
    for r in sorted(rows, key=lambda x: -(x["max_err_pct"] or 0))[:5]:
        if r["max_err_pct"] is not None and r["max_err_pct"] > 20:
            md_lines.append(f"- {r['label']}: 置信 {r['confidence']}，预测 {r['pred_max']} vs 实际 {r['true_max']}（偏 {r['max_err_pct']:.0f}%）")

    report_md = os.path.join(BASE, f"report_round{round_no}.md")
    report_json = os.path.join(BASE, f"report_round{round_no}.json")
    with open(report_md, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    with open(report_json, "w", encoding="utf-8") as f:
        json.dump({"round": round_no, "avg_max_err_pct": avg_max_err,
                   "avg_mean_err_pct": avg_mean_err, "rows": rows}, f, ensure_ascii=False, indent=2)
    print(f"对账完成: 平均最大停滞误差 {avg_max_err:.1f}% | 平均均值误差 {avg_mean_err:.1f}%")
    print(f"报告: {report_md} / {report_json}")
    for r in rows:
        flag = "" if (r["max_err_pct"] or 0) <= 20 else "  ⚠️"
        print(f"  [{r['id']:>2}] {r['label']:<12} pred_max={r['pred_max']} true_max={r['true_max']} "
              f"err={r['max_err_pct']:.0f}% conf={r['confidence']}{flag}")
    return rows


# ---------------------------------------------------------------------------
# 校准可视化：predicted vs actual（理想线 y=x）
# ---------------------------------------------------------------------------

def plot_calibration(rounds=(1, 2)):
    plt.figure(figsize=(7, 7))
    colors = {1: "#e74c3c", 2: "#2ecc71"}
    labels = {1: "Round 1 (intuition)", 2: "Round 2 (calibrated)"}
    for r in rounds:
        path = os.path.join(BASE, f"report_round{r}.json")
        if not os.path.exists(path):
            continue
        rep = load_json(path)
        xs = [row["true_max"] for row in rep["rows"]]
        ys = [row["pred_max"] for row in rep["rows"]]
        plt.scatter(xs, ys, c=colors.get(r, "#888"), alpha=0.7, s=60, label=labels.get(r, f"Round {r}"))
    lim = max([row["true_max"] for r in rounds
               if os.path.exists(os.path.join(BASE, f"report_round{r}.json"))
               for row in load_json(os.path.join(BASE, f"report_round{r}.json"))["rows"]] + [500])
    mx = max(lim, 1)
    plt.plot([0, mx], [0, mx], "k--", alpha=0.5, label="ideal y=x")
    plt.xscale("log"); plt.yscale("log")
    plt.xlabel("Actual max stopping time")
    plt.ylabel("LLM predicted max stopping time")
    plt.title("Collatz stopping-time prediction calibration")
    plt.legend()
    plt.grid(True, which="both", alpha=0.3)
    plt.tight_layout()
    out = os.path.join(BASE, "calibration.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"校准图: {out}")


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def print_questions():
    print("问题集（给 LLM 预测用）：对每个区间预测 max_stopping / mean_stopping / all_reach_one / confidence")
    for q in QUESTIONS:
        print(f'  {{"id": {q["id"]}, "lo": {q["lo"]}, "hi": {q["hi"]}}}  # {q["label"]}')


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--reconcile", type=int)
    ap.add_argument("--plot", action="store_true")
    ap.add_argument("--questions", action="store_true")
    args = ap.parse_args()

    if args.questions:
        print_questions()
    if args.verify:
        compute_truths()
    if args.reconcile:
        reconcile(args.reconcile)
    if args.plot:
        plot_calibration()
    if not (args.verify or args.reconcile or args.plot or args.questions):
        print(__doc__)
