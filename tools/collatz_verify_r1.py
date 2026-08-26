# Collatz round-1 verification: items 1-7 (pure ASCII output)
import math, random, itertools
from fractions import Fraction

LOG23 = math.log2(3.0)
LN2 = math.log(2.0)
EPS = 1.0/(15.0*LN2)          # C3 threshold 1/(15 ln2)
print("log2(3) = %.16f" % LOG23)
print("EPS = 1/(15 ln2) = %.10f" % EPS)

def v2(x):
    c = 0
    while x % 2 == 0:
        x //= 2; c += 1
    return c

# ---------- ITEM 1: C3 exclusion set, m=2..20 ----------
print("\n[1] C3 interval (log2 3, log2 3 + 1/(15 ln2)):")
for m in range(2, 21):
    lo = m*LOG23; hi = m*(LOG23+EPS)
    ps = [p for p in range(math.floor(lo)+1, math.floor(hi)+1) if lo < p < m*(LOG23+EPS)]
    deltas = [(p, p/m - LOG23) for p in ps]
    if deltas:
        pmin, dmin = min(deltas, key=lambda t: t[1])
        fr = Fraction(pmin, m)
        print("  m=%2d: %d candidates; min delta p/m=%d/%d=%s delta=%.6f" % (m, len(ps), pmin, m, fr, dmin))
    else:
        print("  m=%2d: NO candidates" % m)

# ---------- ITEM 2: C4 m=3 BS enumeration ----------
print("\n[2] C4: m=3, N=9+3*2^s1+2^s2, s1 in {1,2,3}, s2 in {s1+1..4}:")
vals = set()
for s1 in (1,2,3):
    for s2 in range(s1+1, 5):
        vals.add(9+3*(2**s1)+2**s2)
print("  N set =", sorted(vals))
print("  25 in set:", 25 in vals, " (expected False)")

# ---------- ITEM 3: C1 inequality random ----------
print("\n[3] C1: log2 prod(3+1/n_i)/m - log2 3 <= log2(1+1/(3 n1)) <= 1/(3 n1 ln2), 10^5 random:")
viol = 0
for _ in range(100000):
    m = random.randint(2, 12)
    n1 = random.randint(5, 10**6)
    ns = [n1] + [random.randint(n1, 10**7) for _ in range(m-1)]
    prod = 1.0
    for n in ns:
        prod *= (3.0 + 1.0/n)
    lhs = math.log2(prod)/m - LOG23
    mid = math.log2(1.0 + 1.0/(3.0*n1))
    rhs = 1.0/(3.0*n1*LN2)
    if not (lhs <= mid + 1e-15 and mid <= rhs + 1e-15):
        viol += 1
print("  violations:", viol, "(expected 0)")

# ---------- ITEM 4: B1 N bounds / n1 bounds ----------
print("\n[4] B1: 3^(m-1) <= N < 3^m*2^(A-2)/2 and n1 bounds (integer n1 only):")
violN = 0; int_cases = 0; violN1 = 0
random.seed(42)
for _ in range(100000):
    m = random.randint(2, 12)
    a = [1]*m
    for i in range(m):
        a[i] = random.choice([1,2,3,4])
    a[0] = 1
    if a[m-1] < 2:
        a[m-1] = random.choice([2,3,4])
    A = sum(a)
    s = [0]*m
    acc = 0
    for i in range(m):
        acc += a[i]; s[i] = acc
    N = sum(3**(m-1-i) * 2**s[i-1] for i in range(0, m))  # s_{-1}=0 via index trick below
    # careful: standard N = sum_{i=1..m} 3^{m-i} 2^{s_{i-1}}, s_0=0
    N = 0
    for i in range(1, m+1):
        N += 3**(m-i) * (1 if i-1 == 0 else 2**s[i-2])
    lb = 3**(m-1); ub = (3**m) * 2**(A-2) // 2
    if not (lb <= N < (3**m)*(2**(A-2))/2.0):
        violN += 1
    D = 2**A - 3**m
    if D > 0 and N % D == 0:
        int_cases += 1
        n1 = N // D
        lo_n1 = Fraction(3**(m-1), D)
        hi_n1 = (3**m) * (2**(A-3))
        if not (lo_n1 <= n1 < hi_n1):
            violN1 += 1
print("  N-bound violations:", violN, "(expected 0); integer n1 cases:", int_cases, "; n1-bound violations:", violN1)

# ---------- ITEM 5: B2 rigidity ----------
print("\n[5] B2: window delta in (0, 0.192645], per m at most one A; integer n1 => n1 < 3^m:")
W = math.log2(8.0/7.0)
print("  log2(8/7) = %.6f" % W)
bad_multi = 0; int_cases5 = 0; bad_n1_lt3m = 0
for m in range(2, 31):
    As = [A for A in range(math.floor(m*LOG23)+1, math.floor(m*(LOG23+W))+1)
          if m*LOG23 < A <= m*(LOG23+W)]
    if len(As) > 1:
        bad_multi += 1
        print("  m=%d has %d A's in window: %s" % (m, len(As), As))
    for A in As:
        def gen_vectors(m, A):
            # compositions of A into m parts >=1, a1=1, am>=2
            for mid in itertools.combinations(range(1, A), m-1):
                parts = [mid[0]] + [mid[i]-mid[i-1] for i in range(1, m-1)] + [A-mid[-1]]
                if parts[0] == 1 and parts[-1] >= 2:
                    yield parts
        if m <= 8:
            vecs = list(gen_vectors(m, A))
        else:
            vecs = []
            for _ in range(1000):
                mid = sorted(random.sample(range(1, A), m-1))
                parts = [mid[0]] + [mid[i]-mid[i-1] for i in range(1, m-1)] + [A-mid[-1]]
                if parts[0] == 1 and parts[-1] >= 2:
                    vecs.append(parts)
        D = 2**A - 3**m
        for a in vecs:
            s = [0]*m; acc=0
            for i in range(m): acc += a[i]; s[i] = acc
            N = sum(3**(m-i) * (1 if i==1 else 2**s[i-2]) for i in range(1, m+1))
            if D > 0 and N % D == 0:
                int_cases5 += 1
                n1 = N // D
                if not (n1 < 3**m):
                    bad_n1_lt3m += 1
print("  m with >1 A in window:", bad_multi, "; integer n1 cases:", int_cases5, "; violations of n1<3^m:", bad_n1_lt3m)

# ---------- ITEM 6: A4 mod3 law + B3 congruences ----------
print("\n[6] A4 mod3 law on random chains; B3 congruences on true cycles:")
viol6 = 0; chains = 0
random.seed(7)
for _ in range(10000):
    m = random.randint(2, 8)
    n1 = random.choice([x for x in range(1, 10**6) if x % 2 == 1])
    a = [1]*m
    for i in range(m): a[i] = random.choice([1,2,3])
    n = n1; ok = True
    ns = [n]
    for i in range(m):
        t = 3*n + 1
        d = v2(t)
        if d < a[i]: ok = False; break
        n = t // (2**a[i])
        ns.append(n)
    if not ok: continue
    chains += 1
    # law: n_i = (-1)^{a_{i-1}} mod 3 for i>=1
    for i in range(1, m+1):
        exp = (-1)**a[i-1]
        if ns[i] % 3 != exp % 3:
            viol6 += 1
print("  chains:", chains, "; mod3-law violations:", viol6, "(expected 0)")
# B3 on trivial cycle m=1,A=2,N=1
m,A,N,n1 = 1,2,1,1
check1 = (n1 * (2**A - 3**m)) % (2**A) == N % (2**A)
check2 = (n1 * (2**A)) % (3**m) == N % (3**m)
print("  B3 trivial cycle: n1*(2^A-3^m)=N mod 2^A:", check1, "; n1*2^A=N mod 3^m:", check2)
# negative cycles: n1*(3^m-2^A)=N; mod 2^A: n1*3^m=N; mod 3^m: -n1*2^A=N
for (m,A,a,N,n1) in [(2,3,[1,2],5,5),(7,11,[1,1,1,2,1,1,4],2363,17)]:
    c1 = (n1*(3**m)) % (2**A) == N % (2**A)
    c2 = (-n1*(2**A)) % (3**m) == N % (3**m)
    print("  neg cycle (m=%d,A=%d): n1*3^m=N mod 2^A: %s ; -n1*2^A=N mod 3^m: %s" % (m,A,c1,c2))

# ---------- ITEM 7: negative-side A bounds and C2 sandwich ----------
print("\n[7] Negative cycles: A bounds and C2 sandwich:")
for (m,A,a) in [(2,3,[1,2]),(7,11,[1,1,1,2,1,1,4])]:
    lbA = math.floor(m*LOG23)+1; ubA = 2*m-1
    s=[0]*m; acc=0
    for i in range(m): acc+=a[i]; s[i]=acc
    N = sum(3**(m-i) * (1 if i==1 else 2**s[i-2]) for i in range(1, m+1))
    okA = lbA <= A <= ubA
    okC2 = (3**m - 2**m) <= N <= 2**(A-m)*(3**m - 2**m)
    print("  m=%d A=%d: A-bound [%d,%d] ok=%s ; C2 sandwich ok=%s (N=%d, range=[%d,%d])"
          % (m, A, lbA, ubA, okA, okC2, N, 3**m-2**m, 2**(A-m)*(3**m-2**m)))

print("\nDONE")
