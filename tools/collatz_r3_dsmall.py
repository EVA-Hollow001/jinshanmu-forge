# -*- coding: utf-8 -*-
"""
collatz_r3_dsmall.py
金山木攻坚 · Collatz · 第2轮铺路 · R3 —— 独立角度：|D| 小值穷尽
(DeepSeek 官方 V4 Pro 铺路工；不联网不查文献；全部数值来自本程序真实运行)

任务:
 1. 枚举 (m,A)（m>=5, A>=m, 先 m,A<=500）使 0 < D = 2^A - 3^m <= B；完整表 + 素因子分解（大整数精确）。
 2. 每个 (m,A) 跑 B-S 可行性检验：n1 = N/D 是否整数。
    N 枚举用 2-adic 逐位回溯剪枝：
      a_i = v2(3n_i+1)；n_i ≡ 1 mod 4 => a_i >= 2；n_i ≡ 3 mod 4 => a_i = 1。
      状态: (k, s, r, T, ND, N2, ip3, sl)
        k   已选步数;  s = s_k;  r = n1 mod 2^{s+1};
        T    = T_k = sum_{j=1..k} 3^{k-j} 2^{s_{j-1}} mod 2^{A+1};
        ND   = N_k mod D;  N2 = N_k mod 2^{A+1};  ip3 = 3^{-k} mod 2^{A+1}
      子代 a = a_{k+1} ∈ [1, A - s - (m-k-1)]:
        n_{k+1} ≡ rho_a mod 2^{a+1},  3*rho_a+1 ≡ 2^a (mod 2^{a+1})
        ==> n1 ≡ c = 3^{-(k+1)} (2^{s+a} - 3 T_k - 2^s) (mod 2^{s+a+1})
        闭包剪枝: (r2 * D) mod 2^{s+a} == (N_{k+1} * sign) mod 2^{s+a}
        sign = +1 正侧 (n1 = +N/D);  sign = -1 负侧 (n1 = -N/D)
    叶子 (k=m, s=A, ND==0): n1 = sign * (N/D) 精确整数, 需 n1 ≡ r (mod 2^{A+1});
    再验 E4: 恰周期（首次回到 n1 恰在第 m 步）、n1≠1、最小元、N 夹逼。
 3. 结构分析: D = 3^m (2^{m*delta} - 1), delta = A/m - log2(3)；收敛子对照；方向自检。
 4. 主结论: 对 D<=B 的全部层, 正侧无非平凡环; 负侧对照 (2,3) 与 (7,11)。
 5. 自检: 平凡环 (1,2); -5/-17 负侧复现; 暴力交叉验证; 抽样回放剪枝证书。

用法:
  python collatz_r3_dsmall.py                    # 默认: 正侧表 B1=1e9; B1b=1e18; 负侧 B=1e9; sweep [1e18..1e120]
  python collatz_r3_dsmall.py B1 [B1b] [Bneg] [B2 ...]
输出文件（脚本同目录）:
  table_B1.txt  table_B1b.txt  neg_side.txt  sweep_summary.txt  sweep_pairs_B<B2>.txt  certs.txt  structure.txt
"""
import sys, os, time, random, itertools
from math import gcd
from fractions import Fraction

try:
    from decimal import Decimal, getcontext
    getcontext().prec = 90
    _L2 = Decimal(2).ln(); _L3 = Decimal(3).ln()
    LOG23 = _L3 / _L2
    LOG23_SRC = "Decimal.ln, 90位精度"
except Exception:
    LOG23 = Decimal(485) / Decimal(306)
    LOG23_SRC = "收敛子 485/306 (误差<5e-6)"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MMAX = 500
AMAX = 500
OUTDIR = os.path.dirname(os.path.abspath(__file__))
random.seed(20240601)

# ================= 数论工具 =================
_MR_BASES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)

def is_prime_mr(n):
    """Miller-Rabin. n < 3.3e24 时确定；更大时"通过=大概率素数"(如实标注)。"""
    if n < 2:
        return False
    for p in _MR_BASES:
        if n % p == 0:
            return n == p
    d = n - 1; s = 0
    while d % 2 == 0:
        d //= 2; s += 1
    for a in _MR_BASES:
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True

def sieve(limit):
    bs = bytearray(b"\x01") * (limit + 1)
    bs[0:2] = b"\x00\x00"
    for i in range(2, int(limit ** 0.5) + 1):
        if bs[i]:
            bs[i * i::i] = b"\x00" * (((limit - i * i) // i) + 1)
    return [i for i in range(2, limit + 1) if bs[i]]

_PRIMES = sieve(10 ** 6)

def pollard_rho(n, max_iter=3000000):
    if n % 2 == 0:
        return 2
    if is_prime_mr(n):
        return n
    c = 1
    while True:
        x = y = 2; d = 1; it = 0
        while d == 1 and it < max_iter:
            x = (x * x + c) % n
            y = (y * y + c) % n
            y = (y * y + c) % n
            d = gcd(abs(x - y), n)
            it += 1
        if d != n and d != 1:
            return d
        c += 1
    return None

def factor_int(n):
    """完全分解。返回 {p: 指数}。rho 失败时大余因子如实原样标注。"""
    fac = {}
    if n == 1:
        return fac
    for p in _PRIMES:
        if p * p > n:
            break
        if n % p == 0:
            e = 0
            while n % p == 0:
                n //= p; e += 1
            fac[p] = e
    if n > 1:
        if is_prime_mr(n):
            fac[n] = fac.get(n, 0) + 1
        else:
            d = pollard_rho(n)
            if d and 1 < d < n:
                for k, v in factor_int(d).items():
                    fac[k] = fac.get(k, 0) + v
                for k, v in factor_int(n // d).items():
                    fac[k] = fac.get(k, 0) + v
            else:
                fac[n] = fac.get(n, 0) + 1  # 未分解的余因子（如实）
    return fac

def divisors_sorted(n):
    ds = [d for d in range(1, int(n ** 0.5) + 1) if n % d == 0]
    return sorted(set(ds + [n // d for d in ds]))

def algebraic_factors(A, m, D):
    """D = 2^A - 3^m = prod_{d|g} Phi_d(2^{A/g}, 3^{m/g}), g = gcd(A,m). 返回 {Phi: 重数}。"""
    g = gcd(A, m)
    if g == 1:
        return {D: 1}
    x = 1 << (A // g); y = 3 ** (m // g)
    phis = {}
    for d in divisors_sorted(g):
        v = x ** d - y ** d
        for d2 in divisors_sorted(d):
            if d2 < d:
                v //= phis[d2]
        phis[d] = v
    out = {}
    for d, v in phis.items():
        out[v] = out.get(v, 0) + 1
    prod = 1
    for v, e in out.items():
        prod *= v ** e
    assert prod == D, "代数因子乘积断言失败"
    return out

def fac_str(fd):
    return " * ".join((f"{p}^{e}" if e > 1 else f"{p}") for p, e in sorted(fd.items()))

def full_factorization(A, m, D):
    """代数因子先行, 再对每个 Phi 完全分解。"""
    fac = {}
    for phi, e in algebraic_factors(A, m, D).items():
        if phi == 1:
            continue
        sub = factor_int(phi)
        for p, ee in sub.items():
            fac[p] = fac.get(p, 0) + ee * e
    prod = 1
    for p, e in fac.items():
        prod *= p ** e
    if prod != D:
        fac[D] = 1  # 未完全分解（如实）
    return fac

# ================= B-S 2-adic 回溯 DFS =================
def solve_bs(m, A, D, sign, cert=None):
    """
    sign=+1 正侧 (D = 2^A - 3^m, n1 = +N/D)
    sign=-1 负侧 (D = 3^m - 2^A, n1 = -N/D)
    返回 (sols, nodes, children, trace): sols = [(a向量, n1, N)]
    """
    MOD2 = 1 << (A + 1)
    inv3 = pow(3, -1, MOD2)
    inv3a = [0] * (A + 2)
    for a in range(1, A + 2):
        inv3a[a] = pow(3, -1, 1 << (a + 1))
    pow3mod2 = [1] * m
    pow3modD = [1] * m
    for j in range(1, m):
        pow3mod2[j] = pow3mod2[j - 1] * 3 % MOD2
        pow3modD[j] = pow3modD[j - 1] * 3 % D
    pow2modD = [1] * (A + 1)
    for s in range(1, A + 1):
        pow2modD[s] = pow2modD[s - 1] * 2 % D
    sols = []
    nodes = 0; children = 0
    trace = [] if cert else None
    stack = [(0, 0, 1, 0, 0, 0, 1, [])]
    while stack:
        k, s, r, T, ND, N2, ip3, sl = stack.pop()
        nodes += 1
        if trace is not None:
            trace.append(("N", k, s, r, list(sl)))
        if k == m:
            if s == A and ND == 0:
                N = 0
                for j in range(m):
                    N += 3 ** (m - 1 - j) * (1 << (sl[j - 1] if j >= 1 else 0))
                x = N // D
                n1 = sign * x
                if n1 % MOD2 == r % MOD2:
                    sols.append((sl[:], n1, N))
                    if trace is not None:
                        trace.append(("L", n1, N, r))
            continue
        rem = m - k - 1
        maxa = A - s - rem
        if maxa < 1:
            continue
        ip3n = ip3 * inv3 % MOD2
        two_s = 1 << s
        threeT = 3 * T % MOD2
        T2 = (threeT + two_s) % MOD2
        p3m2 = pow3mod2[m - k - 1]
        p3mD = pow3modD[m - k - 1]
        p2sD = pow2modD[s]
        for a in range(1, maxa + 1):
            children += 1
            s2 = s + a
            m3 = 1 << (s2 + 1)
            # rho_a: 3*rho_a+1 ≡ 2^a (mod 2^{a+1}) 的剩余类（本轮 v2 恰为 a）
            rho = ((1 << a) - 1) * inv3a[a] % (1 << (a + 1))
            c = ip3n * (((1 << s2) - threeT - two_s) % m3) % m3
            assert c % (1 << (s + 1)) == r, "2-adic 相容性断言失败"
            r2 = c
            term2 = p3m2 * two_s % MOD2
            N2b = (N2 + term2) % MOD2
            NDb = (ND + p3mD * p2sD) % D
            m4 = 1 << s2
            lhs = r2 * D % m4
            rhs = N2b * sign % m4
            ok = (lhs == rhs)
            if trace is not None:
                trace.append(("C", k, a, s2, r2, lhs, rhs, m4, ok))
            if ok:
                stack.append((k + 1, s2, r2, T2, NDb, N2b, ip3n, sl + [s2]))
    return sols, nodes, children, trace

def verify_cycle(n1, sl, m, A, side):
    """对 B-S 解做 E4 检验：恰周期（首次回到 n1 恰第 m 步）、n1≠1（平凡性）、最小元、N 夹逼。
    返回 (status, path|None)。"""
    path = [n1]; n = n1
    for a in sl:
        t = 3 * n + 1
        if t % (1 << a):
            return ("div_fail", None)
        n = t >> a
        path.append(n)
    if path[-1] != n1:
        return ("no_close", None)
    for i in range(m):
        t = 3 * path[i] + 1
        if (t & -t) != (1 << sl[i]):
            return ("valuation_mismatch", None)
    N = sum(3 ** (m - 1 - j) * (1 << (sl[j - 1] if j >= 1 else 0)) for j in range(m))
    assert 3 ** m - 2 ** m <= N <= (1 << (A - m)) * (3 ** m - 2 ** m), "N 夹逼断言失败"
    first = m
    for i in range(1, m + 1):
        if path[i] == n1:
            first = i
            break
    if first != m:
        return ("subperiod", path)
    if side > 0:
        if n1 == 1:
            return ("trivial_cycle", path)
        if min(path[:-1]) != n1:
            return ("rotation_nonmin", path)
        return ("nontrivial_positive_cycle", path)
    else:
        if n1 == -1:
            return ("trivial_neg_cycle", path)
        if abs(n1) != min(abs(p) for p in path[:-1]):
            return ("rotation_nonmin_neg", path)
        return ("nontrivial_negative_cycle", path)

# ================= 暴力交叉验证 =================
def brute_bs(m, A, D):
    sols = []
    if A < m:
        return sols
    for combo in itertools.combinations(range(1, A), m - 1):
        s = [0] + list(combo) + [A]
        N = sum(3 ** (m - 1 - j) * (1 << s[j]) for j in range(m))
        if N % D == 0:
            sols.append((s[1:], N // D))
    return sols

# ================= 枚举 =================
def enum_positive(B, mmin=5, mmax=MMAX):
    res = []
    for m in range(mmin, mmax + 1):
        p3m = 3 ** m
        lo, hi = 1, AMAX + 2
        while lo < hi:
            mid = (lo + hi) // 2
            if (1 << mid) > p3m: hi = mid
            else: lo = mid + 1
        A_lo = lo
        lo, hi = 1, AMAX + 2
        while lo < hi:
            mid = (lo + hi) // 2
            if (1 << mid) <= p3m + B: lo = mid + 1
            else: hi = mid
        A_hi = lo - 1
        for A in range(max(A_lo, 1), min(A_hi, AMAX) + 1):
            D = (1 << A) - p3m
            if 0 < D <= B:
                res.append((m, A, D))
    return res

def enum_negative(B, mmax=MMAX):
    res = []
    for m in range(1, mmax + 1):
        p3m = 3 ** m
        lo, hi = 1, AMAX + 2
        while lo < hi:
            mid = (lo + hi) // 2
            if (1 << mid) >= p3m: hi = mid
            else: lo = mid + 1
        A_hi = lo - 1  # 最大 A 使 2^A < 3^m
        if A_hi < 1:
            continue
        lo, hi = 1, A_hi + 1
        while lo < hi:
            mid = (lo + hi) // 2
            if p3m - (1 << mid) <= B: hi = mid
            else: lo = mid + 1
        A_lo = lo
        for A in range(max(A_lo, 1), min(A_hi, AMAX) + 1):
            D = p3m - (1 << A)
            if 0 < D <= B:
                res.append((m, A, D))
    return res

# ================= 连分数 / 收敛子 =================
def cf_terms_log23(n):
    X = Fraction(3); Y = Fraction(2)
    ts = []
    for _ in range(n):
        t = 0; yp = Fraction(1)
        while yp * Y <= X:
            yp *= Y; t += 1
        ts.append(t)
        X, Y = Y, X / (Y ** t)
    return ts

def convergents(ts, maxq):
    h0, h1, k0, k1 = 0, 1, 1, 0
    out = []
    for t in ts:
        h2 = t * h1 + h0; k2 = t * k1 + k0
        if k2 > maxq:
            break
        out.append((h2, k2))
        h0, h1 = h1, h2; k0, k1 = k1, k2
    return out

# ================= 主流程 =================
def main():
    t0 = time.time()
    argv = sys.argv[1:]
    B1 = int(float(argv[0])) if len(argv) > 0 else 10 ** 9
    B1b = int(float(argv[1])) if len(argv) > 1 else 10 ** 18
    Bneg = int(float(argv[2])) if len(argv) > 2 else 10 ** 9
    SWEEP = [int(float(x)) for x in argv[3:]] if len(argv) > 3 else \
        [10 ** 18, 10 ** 30, 10 ** 60, 10 ** 90, 10 ** 100, 10 ** 120]
    BUDGET = 1200.0

    print(f"=== R3 |D| 小值穷尽 ===")
    print(f"MMAX={MMAX} AMAX={AMAX}  log2(3) 来源: {LOG23_SRC}")
    print(f"B1={B1}  B1b={B1b}  Bneg={Bneg}  SWEEP={SWEEP}  BUDGET={BUDGET}s\n", flush=True)

    # ---------- Phase A: 正侧完整表 B1 ----------
    ta = time.time()
    pairs = enum_positive(B1)
    print(f"=== Phase A: 正侧完整表 B={B1} ===  pairs={len(pairs)}  枚举耗时={time.time()-ta:.2f}s", flush=True)
    rows = []
    tot_nodes = tot_child = 0
    n_covers = 0; n_nontriv = 0; n_other = 0
    for (m, A, D) in pairs:
        fac = full_factorization(A, m, D)
        sols, nodes, child, _ = solve_bs(m, A, D, +1)
        tot_nodes += nodes; tot_child += child
        verdict = "-"
        for (av, n1, N) in sols:
            st, _ = verify_cycle(n1, av, m, A, +1)
            if st == "nontrivial_positive_cycle":
                verdict = "CYCLE!!"
                n_nontriv += 1
            elif st == "subperiod" and n1 == 1:
                if verdict == "-":
                    verdict = "cover(平凡环覆盖,E4排除)"
                n_covers += 1
            elif st == "trivial_cycle":
                verdict = "trivial(平凡环)"
            else:
                n_other += 1
        delta = Decimal(A) / Decimal(m) - LOG23
        mdelta = Decimal(m) * delta
        rows.append((m, A, D, fac, delta, mdelta, len(sols), verdict))
    print(f"{'m':>4} {'A':>4} {'D':>12}  {'factorization':<34} {'delta':>12} {'m*delta':>10} {'sols':>4}  verdict")
    for (m, A, D, fac, delta, mdelta, ns, vd) in rows:
        print(f"{m:>4} {A:>4} {D:>12}  {fac_str(fac):<34} {float(delta):>+12.6f} {float(mdelta):>10.6f} {ns:>4}  {vd}")
    print(f"Phase A 汇总: pairs={len(pairs)} nodes={tot_nodes} children={tot_child} "
          f"耗时={time.time()-ta:.2f}s  非平凡解={n_nontriv}  平凡覆盖={n_covers}  其他={n_other}\n", flush=True)
    with open(os.path.join(OUTDIR, "table_B1.txt"), "w", encoding="utf-8") as f:
        f.write(f"# 正侧完整表 B={B1}  (m,A) 使 0 < D = 2^A - 3^m <= B, m>=5, A>=m, m,A<=500\n")
        f.write("# m A D factorization delta(=A/m-log2(3)) m*delta B-S解数 verdict\n")
        for (m, A, D, fac, delta, mdelta, ns, vd) in rows:
            f.write(f"{m} {A} {D} {fac_str(fac)} {delta} {mdelta} {ns} {vd}\n")

    # ---------- Phase A0: m=1..4 正侧复验 ----------
    print("=== Phase A0: m=1..4 正侧复验 (B=B1) ===", flush=True)
    p014 = enum_positive(B1, mmin=1, mmax=4)
    found014 = []
    for (m, A, D) in p014:
        sols, _, _, _ = solve_bs(m, A, D, +1)
        for (av, n1, N) in sols:
            st, _ = verify_cycle(n1, av, m, A, +1)
            found014.append((m, A, D, av, n1, st))
    for (m, A, D, av, n1, st) in found014:
        print(f"  (m,A)=({m},{A}) D={D}: n1={n1} a={av} -> {st}")
    print(f"  m=1..4 共 {len(p014)} 对, 解 {len(found014)} 个（应只有 (1,2) 平凡 + (2,4) 覆盖）\n", flush=True)

    # ---------- Phase B: 负侧 Bneg ----------
    tb = time.time()
    npairs = enum_negative(Bneg)
    print(f"=== Phase B: 负侧 D' = 3^m - 2^A <= {Bneg} ===  pairs={len(npairs)}", flush=True)
    neg_sols = []
    tn = tc = 0
    for (m, A, D) in npairs:
        sols, nodes, child, _ = solve_bs(m, A, D, -1)
        tn += nodes; tc += child
        for (av, n1, N) in sols:
            st, _ = verify_cycle(n1, av, m, A, -1)
            neg_sols.append((m, A, D, av, n1, N, st))
    for (m, A, D, av, n1, N, st) in neg_sols:
        print(f"  (m,A)=({m},{A}) D'={D}: n1={n1} a={av} N={N} -> {st}")
    print(f"Phase B 汇总: pairs={len(npairs)} nodes={tn} children={tc} 耗时={time.time()-tb:.2f}s  解={len(neg_sols)}\n", flush=True)
    with open(os.path.join(OUTDIR, "neg_side.txt"), "w", encoding="utf-8") as f:
        f.write(f"# 负侧 D' = 3^m - 2^A <= {Bneg}\n# m A D' a-向量 n1 N status\n")
        for (m, A, D, av, n1, N, st) in neg_sols:
            f.write(f"{m} {A} {D} {av} {n1} {N} {st}\n")

    # ---------- Phase B1b: 正侧完整表 B1b（文件） ----------
    tb2 = time.time()
    pairs_b = enum_positive(B1b)
    print(f"=== Phase B1b: 正侧完整表 B={B1b}（含完全分解, 文件）===  pairs={len(pairs_b)}", flush=True)
    bn = bc = 0; bn_nontriv = 0; bn_cov = 0
    with open(os.path.join(OUTDIR, "table_B1b.txt"), "w", encoding="utf-8") as f:
        f.write(f"# 正侧完整表 B={B1b}\n# m A D factorization B-S解数 verdict\n")
        for (m, A, D) in pairs_b:
            fac = full_factorization(A, m, D)
            sols, nodes, child, _ = solve_bs(m, A, D, +1)
            bn += nodes; bc += child
            vd = "-"
            for (av, n1, N) in sols:
                st, _ = verify_cycle(n1, av, m, A, +1)
                if st == "nontrivial_positive_cycle":
                    vd = "CYCLE!!"; bn_nontriv += 1
                elif st == "subperiod" and n1 == 1:
                    vd = "cover"; bn_cov += 1
            f.write(f"{m} {A} {D} {fac_str(fac)} {len(sols)} {vd}\n")
    print(f"  nodes={bn} children={bc} 耗时={time.time()-tb2:.2f}s  非平凡={bn_nontriv}  覆盖={bn_cov}\n", flush=True)

    # ---------- Phase C: B2 sweep ----------
    print("=== Phase C: B2 sweep（正侧全 m∈[1,500] B-S 穷尽）===", flush=True)
    sweep_summary = []
    for B2 in SWEEP:
        if time.time() - t0 > BUDGET:
            print(f"  B={B2}: 跳过（预算 {BUDGET}s 用尽）", flush=True)
            continue
        t2 = time.time()
        pp = enum_positive(B2, mmin=1)
        sn = sc = 0; max_tree = (0, None); ntriv = 0; ncov = 0; nnon = 0
        non_sols = []
        with open(os.path.join(OUTDIR, f"sweep_pairs_B{B2}.txt"), "w", encoding="utf-8") as f:
            f.write(f"# sweep B={B2}: 全部 (m,A), 1<=m<=500, A<=500, 0 < 2^A - 3^m <= B\n# m A D B-S解数 verdict nodes\n")
            for (m, A, D) in pp:
                sols, nodes, child, _ = solve_bs(m, A, D, +1)
                sn += nodes; sc += child
                if nodes > max_tree[0]:
                    max_tree = (nodes, (m, A))
                vd = "-"
                for (av, n1, N) in sols:
                    st, _ = verify_cycle(n1, av, m, A, +1)
                    if st == "nontrivial_positive_cycle":
                        vd = "CYCLE!!"; nnon += 1
                        non_sols.append((m, A, D, av, n1, N))
                    elif st == "subperiod" and n1 == 1:
                        vd = "cover"; ncov += 1
                    elif st == "trivial_cycle":
                        vd = "trivial"; ntriv += 1
                f.write(f"{m} {A} {D} {len(sols)} {vd} {nodes}\n")
        dt = time.time() - t2
        sweep_summary.append((B2, len(pp), sn, sc, dt, max_tree, ntriv, ncov, nnon))
        print(f"  B={B2}: pairs={len(pp)} nodes={sn} children={sc} 耗时={dt:.2f}s "
              f"最大树={max_tree} 平凡={ntriv} 覆盖={ncov} 非平凡={nnon}", flush=True)
        for (m, A, D, av, n1, N) in non_sols:
            print(f"    !! 非平凡存活候选: (m,A)=({m},{A}) D={D} a={av} n1={n1} N={N}")
    with open(os.path.join(OUTDIR, "sweep_summary.txt"), "w", encoding="utf-8") as f:
        f.write("# B2 sweep 汇总: B pairs nodes children time(s) max_tree trivial covers nontrivial\n")
        for row in sweep_summary:
            f.write(f"{row[0]} {row[1]} {row[2]} {row[3]} {row[4]:.2f} {row[5]} {row[6]} {row[7]} {row[8]}\n")
    print("", flush=True)

    # ---------- Phase D: 自检与证书 ----------
    print("=== Phase D: 自检 ===", flush=True)
    checks = [
        (5, 8, 13, +1), (5, 10, 781, +1), (7, 12, 1909, +1), (12, 20, 517135, +1),
        (2, 3, 1, -1), (7, 11, 139, -1),
    ]
    for (m, A, D, sg) in checks:
        dfs_sols, _, _, _ = solve_bs(m, A, D, sg)
        br_sols = brute_bs(m, A, D)
        dfs_set = {(tuple(av), n1) for (av, n1, N) in dfs_sols}
        br_set = {(tuple(av), n1) for (av, n1) in br_sols}
        ok = (dfs_set == br_set)
        print(f"  暴力交叉验证 (m,A,D)=({m},{A},{D}) sign={sg:+d}: DFS={len(dfs_set)} 暴力={len(br_set)} {'PASS' if ok else 'FAIL'}")
        if not ok:
            print(f"    DFS 独有: {dfs_set - br_set}  暴力独有: {br_set - dfs_set}")
    print("  平凡环(1,2):", end=" ")
    s12, _, _, _ = solve_bs(1, 2, 1, +1)
    print([(av, n1) for (av, n1, N) in s12], flush=True)
    # 证书
    certpairs = [(1, 2, 1, +1, "平凡环(1,2)"), (5, 8, 13, +1, "(5,8) D=13 无解层"),
                 (5, 10, 781, +1, "(5,10) 平凡环5重覆盖"),
                 (2, 3, 1, -1, "负侧(2,3) -5环"), (7, 11, 139, -1, "负侧(7,11) -17环")]
    with open(os.path.join(OUTDIR, "certs.txt"), "w", encoding="utf-8") as f:
        for (m, A, D, sg, name) in certpairs:
            sols, nodes, child, trace = solve_bs(m, A, D, sg, cert=True)
            f.write(f"===== 剪枝证书: {name}  m={m} A={A} D={D} sign={sg:+d}  nodes={nodes} children={child} 解={len(sols)} =====\n")
            for rec in trace:
                if rec[0] == "N":
                    _, k, s, r, sl = rec
                    f.write(f"  node k={k} s={s}  n1 mod 2^{s+1} = {r}   (a-前缀={sl})\n")
                elif rec[0] == "C":
                    _, k, a, s2, r2, lhs, rhs, m4, ok = rec
                    f.write(f"    child a={a} (k={k}->{k+1}, s2={s2}): r2={r2}  "
                            f"(r2*D) mod 2^{s2} = {lhs}  vs  sign*N mod 2^{s2} = {rhs}  -> {'存活' if ok else '剪掉'}\n")
                elif rec[0] == "L":
                    _, n1, N, r = rec
                    f.write(f"  !! 叶子解: n1={n1}  N={N}  n1 mod 2^{A+1} = {n1 % (1 << (A+1))}  (需 == r={r})\n")
            for (av, n1, N) in sols:
                st, path = verify_cycle(n1, av, m, A, sg)
                f.write(f"  验证: a={av} n1={n1} N={N} -> {st}" + (f" path={path}" if path else "") + "\n")
            f.write("\n")
    print(f"  剪枝证书已写入 certs.txt（{len(certpairs)} 组）\n", flush=True)

    # ---------- Phase E: 结构分析 ----------
    print("=== Phase E: 结构分析 ===", flush=True)
    ts = cf_terms_log23(12)
    convs = convergents(ts, 500)
    print(f"  log2(3) 连分数项: {ts[:12]}")
    print(f"  收敛子 (q<=500): {convs}")
    for (p, q) in convs:
        orient = "上方(2^p>3^q)" if (1 << p) > 3 ** q else "下方(2^p<3^q)"
        print(f"    {p}/{q}: {orient}   |{p}/{q} - log2(3)| ≈ {abs(Decimal(p)/Decimal(q)-LOG23):.3e}")
    # D0 表
    d0 = []
    for m in range(5, MMAX + 1):
        p3m = 3 ** m
        A = p3m.bit_length()  # 2^A > 3^m 的最小 A
        d0.append((2 ** A - p3m, m, A))
    d0min_all = min(d0)
    d0min_21 = min(x for x in d0 if x[1] >= 21)
    print(f"  D0(m) = 2^ceil(m*log2 3) - 3^m:  min m∈[5,500] = {d0min_all[0]} (m={d0min_all[1]}, A={d0min_all[2]})")
    print(f"                                      min m∈[21,500] = {d0min_21[0]} (m={d0min_21[1]}, A={d0min_21[2]})")
    for m in (12, 19, 20, 21, 41, 53, 84, 210, 306, 485):
        p3m = 3 ** m
        A = p3m.bit_length()
        print(f"    D0({m}) = 2^{A} - 3^{m} = {2**A - p3m}")
    # 解析界（A>500 / m>500 排除）
    t501 = 0
    p = 1
    while p * 3 <= (1 << 501):
        p *= 3; t501 += 1
    boundA = (1 << 501) - p
    m501 = 501
    A501 = (3 ** 501).bit_length()
    boundM = (1 << A501) - 3 ** 501
    print(f"  A>500 排除界: 2^501 - 3^{t501} = {boundA}  (> 10^100 ? {boundA > 10**100})")
    print(f"  m>500 排除界: 2^{A501} - 3^501 = {boundM}  (> 10^100 ? {boundM > 10**100})")
    print(f"  通用下界: D >= (2/3)*2^A  (A>=501): (2/3)*2^501 = {(2 * (1 << 501)) // 3}  (> 10^100 ? {(2 * (1 << 501)) // 3 > 10**100})")
    # B1 表逐行恒等式/方向自检
    n_ident = 0; n_dir = 0; n_sand = 0; n_mono = 0
    prev = {}
    with open(os.path.join(OUTDIR, "structure.txt"), "w", encoding="utf-8") as f:
        f.write("# 结构分析: B1 表逐行恒等式 D = 3^m (2^{m*delta} - 1), 方向与夹逼自检\n")
        f.write("# m A D delta m*delta D_check_relerr lower_ok upper_ok nearest_conv conv_dist\n")
        for (m, A, D) in pairs:
            delta = Decimal(A) / Decimal(m) - LOG23
            mdelta = Decimal(m) * delta
            Dchk = Decimal(3) ** m * (Decimal(2) ** mdelta - 1)
            relerr = abs(Dchk - D) / D if D else Decimal(0)
            if relerr < Decimal(10) ** -70:
                n_ident += 1
            if delta > 0:
                n_dir += 1
            low = Decimal(3) ** m * mdelta * _L2
            up = low * (Decimal(2) ** mdelta)
            ok_low = (low <= D); ok_up = (D <= up)
            if ok_low and ok_up:
                n_sand += 1
            if m in prev:
                if prev[m] < D:
                    n_mono += 1
            prev[m] = D
            best = min(((abs(Decimal(A) / Decimal(m) - Decimal(p) / Decimal(q)), p, q) for (p, q) in convs))
            f.write(f"{m} {A} {D} {delta} {mdelta} {relerr} {int(ok_low)} {int(ok_up)} {best[1]}/{best[2]} {best[0]}\n")
    print(f"  逐行恒等式验证: {n_ident}/{len(pairs)} 通过 (Decimal 90位, relerr<1e-70)")
    print(f"  方向自检 (delta>0 即 D>0): {n_dir}/{len(pairs)} 通过; 同一 m 内 D 随 A 单调递增: {n_mono}/{len(pairs)-len(prev)} 通过")
    print(f"  夹逼 3^m*m*delta*ln2 <= D <= 3^m*m*delta*ln2*2^{m*delta}: {n_sand}/{len(pairs)} 通过")
    print(f"\n总耗时 = {time.time()-t0:.1f}s\n", flush=True)

if __name__ == "__main__":
    main()
