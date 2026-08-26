#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
collatz_r1_sieve.py — Collatz 非平凡循环排除 · 第2轮铺路 · R1（主力计算线）

作者：铺路工（金山木框架，DeepSeek V4 Pro）
铁律：断外援，不联网不查文献；所有数字来自本程序真实运行；不确定处标注"待验证"。

背景（[继承] 事实，本程序直接引用，不冒充新发现）：
  正循环 ⟺ 存在 m≥1 与 a=(a1..am)（ai≥1, A=Σai）满足
    (E1) 2^A = Π(3+1/ni) > 3^m
    (E2) n1·(2^A−3^m) = N,  N = Σ_{i=1..m} 3^{m−i}·2^{s_{i−1}}, s0=0, si=a1+…+ai
    (E3) ai = v2(3ni+1)（ni 由 n1 递推生成）
    (E4) 恰周期 m：n_{m+1}=n1 且 n1≠1
  m=2,3,4,7 已由 C3/C4 真排除 ⇒ m≥5 [继承]。
  窗口：0 < A/m − log2(3) ≤ log2(1+1/(3n1))，n1≥5 ⇒ A/m ∈ (log2 3, log2 3.2]。

核心引理（本程序自证，非文献照搬）：
  引理 L（2-adic 相容自动性）：对任意 a 向量（Σaᵢ=A），令 x* = N/(2^A−3^m) ∈ Z₂
  （2-adic，D=2^A−3^m 为奇数可逆）。则对每个 i：
      v₂(3^i·x* + T_i) = s_i 恰成立，T_i = Σ_{j=1..i} 3^{i−j}·2^{s_{j−1}}。
  证明：3^i x* + T_i = (3^i T_m + T_i(2^A−3^m))/D（T_m=N）。
    3^i(T_m − 3^{m−i}T_i) + T_i·2^A = 2^{s_i}·(3^i·V_i + T_i·2^{A−s_i})，
    其中 V_i = Σ_{j=i+1..m} 3^{m−j}·2^{s_{j−1}−s_i} 为奇数（首项 3^{m−i−1}·2^0，
    其余含因子 2），T_i 为奇数（首项 3^{i−1}·2^0，其余含因子 2），
    且 A−s_i = a_{i+1}+…+a_m ≥ 1 ⇒ T_i·2^{A−s_i} 为偶。奇+偶=奇 ⇒
    v₂(3^i x* + T_i) = s_i 恰成立 ∎
  推论：叶部检验只需 (a) D|N、(b) n₁=N/D ≥ 5（n₁ 奇自动：N、D 均奇）。
        2-adic / mod 3^m 一致性为冗余交叉验证，必须恒过。
        恰周期 m 由直接轨道重放的首归步数给出（排除平凡环多重覆盖）。
  [B] 精确最小元扫描（可扩展主筛）：
      严格上界（本程序自证）：n1 取循环最小元时，2^A=Π(3+1/ni)≤(3+1/n1)^m，
      故 n1 ≤ B(m,A) := max{ n≥1 : 2^A·n^m ≤ (3n+1)^m }。
      全局扫描奇数 n1=5..N_max（N_max=max_m B(m,A0(m))）：沿 T 迭代，
      值<n1 即停（n1 非最小元），值=n1 即检出周期循环。检出即真，无启发式。

用法：python collatz_r1_sieve.py [M]   （默认 M=10000）
"""

import sys, time, random, json, math

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    import mpmath as mp
    HAVE_MP = True
except ImportError:
    HAVE_MP = False

# ---------------- 常量 ----------------
if HAVE_MP:
    mp.mp.dps = 80
    LOG2_3  = float(mp.log(3, 2))
    LOG2_32 = float(mp.log(mp.mpf(16) / 5, 2))   # log2(3.2)
    LOG2_5  = float(mp.log(5, 2))
else:
    LOG2_3  = math.log2(3.0)
    LOG2_32 = math.log2(3.2)
    LOG2_5  = math.log2(5.0)


# ---------------- 窗口整数 A 的精确计算 ----------------
def A0(m):
    """最小整数 A 使 A/m > log2 3，即 2^A > 3^m（大整数精确修正）。"""
    a = int(m * LOG2_3)
    p3 = pow(3, m)
    while (1 << a) <= p3:
        a += 1
    while a - 1 >= 1 and (1 << (a - 1)) > p3:
        a -= 1
    return a


def Amax(m):
    """最大整数 A 使 A/m <= log2 3.2，即 5^m·2^A <= 16^m（精确修正）。"""
    a = int(m * LOG2_32)
    p5 = pow(5, m)
    p16 = 1 << (4 * m)
    while p5 * (1 << a) > p16:
        a -= 1
    while p5 * (1 << (a + 1)) <= p16:
        a += 1
    return a


def B_bound(m, A):
    """上界 B(m,A) = max{ n>=1 : 2^A·n^m <= (3n+1)^m } 的高精度浮点近似
    （即 floor(1/(2^{A/m}−3))）。用于设定扫描上界；另有 B_exact 抽样复核。"""
    if HAVE_MP:
        v = mp.power(2, mp.mpf(A) / m) - 3
        if v <= 0:
            return 0
        b = int(mp.floor(1 / v))
    else:
        x = 2.0 ** (A / m)
        if x <= 3.0:
            return 0
        b = int(1.0 / (x - 3.0))
    return b


def B_exact(m, A):
    """B(m,A) 的严格大整数二分（仅抽样自检，防浮点低估导致漏扫）。"""
    p2A = 1 << A

    def ok(n):
        return p2A * pow(n, m) <= pow(3 * n + 1, m)

    if not ok(1):
        return 0
    hi = max(2, B_bound(m, A) + 4)
    while ok(hi):
        hi *= 2
        if hi > 1 << 40:
            return hi
    lo = 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if ok(mid):
            lo = mid
        else:
            hi = mid - 1
    return lo


# ---------------- 公共：N 与 2-adic / 3-adic 一致性 ----------------
def full_N(a_list):
    """N = Σ_{k=0}^{m-1} 3^{m-1-k} 2^{s_k}，s_0=0, s_k=a_1+...+a_k。"""
    m = len(a_list)
    N = pow(3, m - 1)
    s = 0
    p3 = pow(3, m - 2) if m >= 2 else 1
    for k in range(1, m):
        s += a_list[k - 1]
        N += p3 * (1 << s)
        p3 //= 3
    return N


def exact_period(n1, m):
    """直接轨道重放求 n1 的恰周期 d 及 d 步总 A。"""
    x = n1
    s = 0
    for d in range(1, m + 1):
        y = 3 * x + 1
        a = (y & -y).bit_length() - 1
        x = y >> a
        s += a
        if x == n1:
            return d, s
    return m, s


# ---------------- [A-l2r] 左到右 DFS（压缩 ii：望远镜部分和 + 引理L） ----------------
def exact_check_l2r(m, A):
    """
    左到右枚举 a 向量，增量维护部分和 N_i（前 i 步累加项之和，大整数）。
    叶部（按引理L）：D|N 整除 → n1≥5 → 2-adic 交叉验证
    n1 ≡ (2^A−N)·3^{−m} (mod 2^{A+1})（必须恒过，理论保证）→ mod 3^m 交叉验证
    → 直接轨道重放求恰周期 d（排除平凡环多重覆盖）。
    """
    D = (1 << A) - pow(3, m)
    mod2A1 = 1 << (A + 1)
    mod3m = pow(3, m)
    inv3_pow_m = pow(pow(3, -1, mod2A1), m, mod2A1)   # 3^{-m} mod 2^{A+1}
    inv2A = pow((1 << A) % mod3m, -1, mod3m)          # 2^{-A} mod 3^m
    stats = {"nodes": 0, "leaves": 0, "divisibility": 0, "two_adic": 0,
             "n1_small": 0, "three_adic": 0, "valid": 0}
    found = []
    a = [0] * m
    sys.setrecursionlimit(100000)

    def dfs(i, s, N_i):
        stats["nodes"] += 1
        rem = m - i
        if s + rem > A:
            return
        if i == m:
            if s != A:
                return
            stats["leaves"] += 1
            N = N_i
            if N % D != 0:
                stats["divisibility"] += 1
                return
            n1 = N // D
            if n1 < 5:
                stats["n1_small"] += 1
                return
            # 引理L交叉验证（必须恒过）：n1 ≡ (2^A−N)·3^{−m} (mod 2^{A+1})
            r2 = ((((1 << A) - N) % mod2A1) * inv3_pow_m) % mod2A1
            if n1 % mod2A1 != r2:
                stats["two_adic"] += 1
                return
            r3 = (N % mod3m) * inv2A % mod3m
            if n1 % mod3m != r3:
                stats["three_adic"] += 1
                return
            stats["valid"] += 1
            d, Ad = exact_period(n1, m)
            found.append((n1, tuple(a), d, Ad))
            return
        max_ai = A - s - (rem - 1)
        for ai in range(1, max_ai + 1):
            a[i] = ai
            s2 = s + ai
            # N_{i+1} = N_i + 3^{m-1-i}·2^{s_i}（第 i+1 步对应项 3^{m-1-i}·2^{s_i}，s_i=s）
            N_next = N_i + pow(3, m - 1 - i) * (1 << s)
            dfs(i + 1, s2, N_next)

    dfs(0, 0, 0)
    return found, stats


# ---------------- [A-r2l] 右到左 DFS + mod 3^k 剪枝（压缩 i） ----------------
def exact_check_r2l(m, A):
    """
    右到左枚举 a 向量（先定 a_m 向左），增量维护 N mod 3^m（全量，防进位丢失），
    每层用 ρ_k = n1 mod 3^{k+1} = (N mod 3^{k+1})·2^{−A} (mod 3^{k+1}) 剪枝：
    n1 ≤ B 而 ρ_k > B ⇒ 无解（压缩 i，n1≡N·2^{−A} mod 3^m 的相容性剪枝）。
    叶部（按引理L）：D|N → n1≥5 → 2-adic 交叉验证（恒过）→ 恰周期 d。
    """
    D = (1 << A) - pow(3, m)
    mod2A1 = 1 << (A + 1)
    inv3_pow_m = pow(pow(3, -1, mod2A1), m, mod2A1)
    B = B_bound(m, A) + 2        # 上界（含安全余量，余量方向安全）
    mod3m = pow(3, m)
    stats = {"nodes": 0, "leaves": 0, "pruned_mod3": 0, "divisibility": 0,
             "two_adic": 0, "n1_small": 0, "valid": 0}
    found = []
    a = [0] * m
    sys.setrecursionlimit(100000)

    def dfs(pos, k, suffix_sum, Nmod):
        # pos: 下一个要定的下标（m-1 向左到 0）；k: 已定的右端步数（0..m）
        # suffix_sum: 已定 a 之和；Nmod: 已定各项之和对 3^m 的余数（全量）
        stats["nodes"] += 1
        if pos < 0:
            if suffix_sum != A:
                return
            stats["leaves"] += 1
            N = full_N(a)
            if N % D != 0:
                stats["divisibility"] += 1
                return
            n1 = N // D
            if n1 < 5:
                stats["n1_small"] += 1
                return
            # 引理L交叉验证（必须恒过）
            r2 = ((((1 << A) - N) % mod2A1) * inv3_pow_m) % mod2A1
            if n1 % mod2A1 != r2:
                stats["two_adic"] += 1
                return
            stats["valid"] += 1
            d, Ad = exact_period(n1, m)
            found.append((n1, tuple(a), d, Ad))
            return
        # 左端还剩 pos 步（下标 0..pos-1），每步至少 1
        max_ai = A - suffix_sum - pos
        mod3k1 = 3 ** (k + 1)
        inv2A_k = pow(2, -A, mod3k1)      # 2^{-A} mod 3^{k+1}
        for ai in range(1, max_ai + 1):
            new_sum = suffix_sum + ai
            s = A - new_sum                # s_{pos} = A − (a_{pos+1}+…+a_m)
            term = pow(3, m - 1 - pos, mod3m) * pow(2, s, mod3m) % mod3m
            new_Nmod = (Nmod + term) % mod3m
            rho = (new_Nmod % mod3k1) * inv2A_k % mod3k1
            if rho > B:                    # n1 ≡ ρ (mod 3^{k+1}) 且 n1 ≤ B ⇒ 无解
                stats["pruned_mod3"] += 1
                continue
            a[pos] = ai
            dfs(pos - 1, k + 1, new_sum, new_Nmod)

    dfs(m - 1, 0, 0, 0)
    return found, stats


# ---------------- 轨道工具 ----------------
def t_step(x):
    y = 3 * x + 1
    a = (y & -y).bit_length() - 1
    return y >> a, a


# ---------------- [B] 全局最小元扫描 ----------------
def global_scan(N_max, M):
    """扫描奇数 n1=5..N_max，检出全部最小元 ≤N_max 的周期 ≤M 循环。精确，无启发式。"""
    cycles = []
    n1 = 5
    while n1 <= N_max:
        x = n1
        step = 0
        a_sum = 0
        closed = False
        while step < M:
            y = 3 * x + 1
            a = (y & -y).bit_length() - 1
            x = y >> a
            a_sum += a
            step += 1
            if x < n1:
                break
            if x == n1:
                closed = True
                break
        if closed:
            cycles.append((step, a_sum, n1))
        n1 += 2
    return cycles


def replay_excluded(m, A, B):
    """证书回放：严格检查奇数 n1∈[5,B] 是否构成恰周期 m、总 A 的非平凡循环。"""
    n1 = 5
    while n1 <= B:
        x = n1
        step = 0
        a_sum = 0
        while step < m:
            y = 3 * x + 1
            a = (y & -y).bit_length() - 1
            x = y >> a
            a_sum += a
            step += 1
            if x < n1:
                break
            if x == n1:
                if step == m and a_sum == A and n1 > 1:
                    return False, n1
                break
        n1 += 2
    return True, None


# ---------------- 主流程 ----------------
def main():
    t_start = time.time()
    M = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    print("=" * 78)
    print("Collatz 非平凡循环排除 · R1 主力计算线")
    print(f"目标 M = {M}；mpmath={HAVE_MP}；log2(3)={LOG2_3!r}")
    print("=" * 78)

    # ---- 0) 平凡环自检：m=1 不被误杀 ----
    x = 1
    step = 0
    a_sum = 0
    while step < 10:
        y = 3 * x + 1
        a = (y & -y).bit_length() - 1
        x = y >> a
        a_sum += a
        step += 1
        if x == 1:
            break
    print(f"\n[自检0] 平凡环：n1=1, 周期={step}, 总A={a_sum}  （预期 周期=1, A=2）")
    assert step == 1 and a_sum == 2, "平凡环自检失败"

    # ---- 1) [A] 精确组合筛：m=2..16，两压缩互相对照 ----
    print("\n[自检A] 精确组合筛（m=2..16，l2r 与 r2l 两种压缩独立对照）")
    print(f"{'m':>3} {'A窗口':>10} {'l2r节点':>9} {'l2r叶':>8} {'r2l节点':>9} "
          f"{'mod3剪枝':>8} {'D|N杀':>7} {'2adic杀':>7} {'n1<5':>6} {'存活':>4}")
    any_found = False
    for m in range(2, 17):
        a0, am = A0(m), Amax(m)
        found_l, st_l = [], None
        found_r, st_r = [], None
        empty_win = a0 > am
        for A in range(a0, am + 1):
            f, s = exact_check_l2r(m, A)
            found_l += f
            if st_l is None:
                st_l = dict(s)
            else:
                for k in st_l:
                    st_l[k] += s[k]
            f2, s2 = exact_check_r2l(m, A)
            found_r += f2
            if st_r is None:
                st_r = dict(s2)
            else:
                for k in st_r:
                    st_r[k] += s2[k]
        if st_l is None:
            st_l = {"nodes": 0, "leaves": 0, "divisibility": 0, "two_adic": 0,
                    "n1_small": 0, "three_adic": 0, "valid": 0}
        if st_r is None:
            st_r = {"nodes": 0, "leaves": 0, "pruned_mod3": 0, "divisibility": 0,
                    "two_adic": 0, "n1_small": 0, "valid": 0}
        win = f"[{a0},{am}]" if not empty_win else f"[{a0},{am}]空"
        print(f"{m:>3} {win:>10} {st_l['nodes']:>9} {st_l['leaves']:>8} {st_r['nodes']:>9} "
              f"{st_r['pruned_mod3']:>8} {st_r['divisibility']:>7} {st_r['two_adic']:>7} "
              f"{st_r['n1_small']:>6} {len(found_r):>4}")
        if found_l or found_r:
            any_found = True
            print(f"    !! 存活: l2r={found_l[:2]} r2l={found_r[:2]}")
        assert found_l == found_r, f"两压缩结果不一致 m={m}"
    print(f"结论A：m=2..16 全部 (m,A) 排除（{'有存活!' if any_found else '无存活'}），两压缩结果一致。")
    print("       m=2,4,7 为空窗（A/m 窗口内无整数）直接排除；m=3,5..16 逐叶排除。")

    # ---- 2) 平凡环多重覆盖演示（A=2m 在窗口外，验证管线不误杀、且 n1<5 规则正确工作）----
    print("\n[自检A2] 平凡环多重覆盖 a=(2,...,2)（A=2m，窗口外）管线演练：")
    for m in (1, 2, 3, 4, 7):
        A = 2 * m
        f, s = exact_check_r2l(m, A)
        info = f"找到 n1={f[0][0]}, a={f[0][1]}" if f else "（无存活，n1<5 击杀）"
        print(f"  m={m}, A={A}: D|N杀={s['divisibility']}, n1<5杀={s['n1_small']}, 2adic杀={s['two_adic']}, {info}")
    print("  （n1=1 的平凡环被 n1<5 规则正确识别为非平凡排除，而非误杀管线。）")

    # ---- 3) [B] 全局最小元扫描 ----
    print("\n[B] 全局最小元扫描（可扩展主筛）")
    N_max = 0
    N_max_m = None
    B_max_list = []
    for m in range(5, M + 1):
        b = B_bound(m, A0(m)) + 2
        B_max_list.append((b, m, A0(m)))
        if b > N_max:
            N_max, N_max_m = b, m
    print(f"N_max = {N_max}（由 m={N_max_m}, A0={A0(N_max_m) if N_max_m else None} 决定）")
    top5 = sorted(B_max_list, reverse=True)[:5]
    print("B_max 最大的 5 个 m：(B_max, m, A0) = " +
          ", ".join(f"({b},{mm},{aa})" for b, mm, aa in top5))

    t0 = time.time()
    cycles = global_scan(N_max, M)
    t_scan = time.time() - t0
    print(f"扫描 n1=5..{N_max}（奇数 {(N_max - 3) // 2} 个）耗时 {t_scan:.2f} s")
    if cycles:
        print(f"!! 检出 {len(cycles)} 个循环（最小元）:")
        for c in cycles[:20]:
            print("   ", c)
    else:
        print("检出循环数：0")

    # ---- 4) 候选计数与击杀统计 ----
    cand_total = 0
    low_kill = 0
    for m in range(5, M + 1):
        a0, am = A0(m), Amax(m)
        cand_total += am - a0 + 1
        low_kill += a0 - 1
    print(f"\n候选统计（5≤m≤{M}）：")
    print(f"  窗口下界外（A ≤ m·log2(3)）被 E1 击杀的 (m,A) 数：{low_kill}")
    print(f"  窗口内候选 (m,A) 总数：{cand_total}")
    print(f"  被全局扫描击杀（无 n1 闭环）的候选数：{cand_total - len(cycles)}")
    print(f"  存活候选数：{len(cycles)}")

    # ---- 5) 证书抽样与回放 ----
    print("\n证书抽样与回放（随机 100 个候选 (m,A)）")
    rng = random.Random(20240101)
    cands = []
    for m in range(5, M + 1):
        a0, am = A0(m), Amax(m)
        for A in range(a0, am + 1):
            cands.append((m, A))
    sample = rng.sample(cands, min(100, len(cands)))
    certs = []
    n_pass = 0
    for (m, A) in sample:
        B = B_bound(m, A)
        excluded, surv = replay_excluded(m, A, B + 2)
        cert = {"m": m, "A": A, "B": B, "method": "minimal-element scan",
                "result": "excluded" if excluded else "SURVIVOR",
                "n1_checked": f"odd [5,{B}]"}
        certs.append(cert)
        if excluded:
            n_pass += 1
        else:
            print(f"  !! 回放发现存活: {cert}")
    print(f"回放通过率：{n_pass}/{len(sample)}")
    with open("collatz_r1_certificates.json", "w", encoding="utf-8") as f:
        json.dump({"sampled": len(sample), "pass": n_pass,
                   "certificates": certs}, f, ensure_ascii=False, indent=1)

    # ---- 6) B 上界浮点 vs 精确 抽样自检 ----
    print("\nB(m,A) 上界浮点估计 vs 精确大整数（抽样自检，防低估）")
    bad = 0
    for (m, A) in rng.sample(cands, min(30, len(cands))):
        bf = B_bound(m, A)
        be = B_exact(m, A)
        if be > bf + 2:
            bad += 1
            print(f"  !! 低估: m={m} A={A} float={bf} exact={be}")
    if bad == 0:
        print("  抽样 30 组全部：float+2 ≥ 精确值（无低估）")
    if N_max_m:
        be = B_exact(N_max_m, A0(N_max_m))
        print(f"  N_max 决定者 m={N_max_m}: float={B_bound(N_max_m, A0(N_max_m))}, "
              f"精确={be}, 扫描上界={N_max}")

    t_total = time.time() - t_start
    print("\n" + "=" * 78)
    print(f"总耗时 {t_total:.2f} s（其中扫描 {t_scan:.2f} s）")
    print("=" * 78)


if __name__ == "__main__":
    main()
