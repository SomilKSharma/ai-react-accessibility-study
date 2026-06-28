import numpy as np, pandas as pd, krippendorff
from scipy.stats import spearmanr, kendalltau
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
df = pd.read_csv(HERE / "ratings.csv")
raters = ["my_rating", "rater_2yr", "rater_6yr", "rater_10yr"]
labels = {"my_rating":"R1 (orig)","rater_2yr":"R2 (2yr)","rater_6yr":"R3 (6yr)","rater_10yr":"R4 (10yr)"}
R = df[raters].to_numpy().astype(float)        # 53 x 4
ast = df["ast_score"].to_numpy()
n = len(df)
rng = np.random.default_rng(20260625)

def boot_ci(stat_fn, B=2000):
    vals=[]
    for _ in range(B):
        idx = rng.integers(0, n, n)
        try: vals.append(stat_fn(idx))
        except Exception: pass
    vals=np.array([v for v in vals if v==v])
    return np.percentile(vals,2.5), np.percentile(vals,97.5)

# --- Krippendorff's alpha (ordinal), all 4 raters ---
# krippendorff expects reliability_data as raters x units
rel = R.T
alpha = krippendorff.alpha(reliability_data=rel, level_of_measurement="ordinal")
def alpha_boot(idx):
    return krippendorff.alpha(reliability_data=R[idx].T, level_of_measurement="ordinal")
a_lo, a_hi = boot_ci(alpha_boot)
print(f"Krippendorff's alpha (ordinal, 4 raters): {alpha:.3f}  95% CI [{a_lo:.3f}, {a_hi:.3f}]")

# --- pairwise quadratic-weighted Cohen's kappa ---
def weighted_kappa(a,b,maxc=5,minc=1):
    cats=list(range(minc,maxc+1)); k=len(cats)
    O=np.zeros((k,k))
    for x,y in zip(a,b): O[int(x)-minc,int(y)-minc]+=1
    O/=O.sum()
    r=O.sum(1); c=O.sum(0); E=np.outer(r,c)
    W=np.array([[((i-j)**2)/((k-1)**2) for j in range(k)] for i in range(k)])
    num=(W*O).sum(); den=(W*E).sum()
    return 1-num/den if den>0 else float('nan')
print("\nPairwise quadratic-weighted Cohen's kappa:")
kappas=[]
for x,y in combinations(raters,2):
    kw=weighted_kappa(df[x],df[y]); kappas.append(kw)
    print(f"  {labels[x]} vs {labels[y]}: {kw:.3f}")
print(f"  mean pairwise weighted kappa: {np.mean(kappas):.3f}")

# --- per-rater agreement with AST (Spearman, Kendall) ---
print("\nPer-rater criterion agreement with AST score:")
rhos=[]
for x in raters:
    rho,p=spearmanr(df[x],ast); tau,pt=kendalltau(df[x],ast); rhos.append(rho)
    print(f"  {labels[x]}: Spearman rho={rho:.3f} (p={p:.1e}), Kendall tau={tau:.3f}")
print(f"  per-rater rho range: [{min(rhos):.3f}, {max(rhos):.3f}]")

# --- pooled (mean-rating) agreement with AST ---
mean_rating=R.mean(1)
rho_m,p_m=spearmanr(mean_rating,ast); tau_m,_=kendalltau(mean_rating,ast)
def rho_boot(idx):
    return spearmanr(mean_rating[idx],ast[idx]).statistic
rm_lo,rm_hi=boot_ci(rho_boot)
print(f"\nPooled mean-rating vs AST: Spearman rho={rho_m:.3f} (p={p_m:.1e}) 95% CI [{rm_lo:.3f},{rm_hi:.3f}]; Kendall tau={tau_m:.3f}")

# --- band monotonicity (pooled mean rating by AST band) ---
bands=[(0.0,0.50),(0.50,0.70),(0.70,0.85),(0.85,0.95),(0.95,0.99),(0.99,1.001)]
print("\nBand monotonicity (pooled mean rating by AST band):")
prev=None; mono=True
for lo,hi in bands:
    m=(ast>=lo)&(ast<hi);
    if m.sum()==0: continue
    mr=mean_rating[m].mean()
    flag="" if prev is None or mr>=prev-1e-9 else "  <-- REVERSAL"
    if prev is not None and mr<prev-1e-9: mono=False
    print(f"  [{lo:.2f},{hi:.2f}): n={m.sum():2d}  mean_rating={mr:.2f}{flag}")
    prev=mr
print(f"  monotonic (no reversals): {mono}")

# --- exact agreement & adjacent agreement (descriptive) ---
exact=np.mean([len(set(row))==1 for row in R])
adjacent=np.mean([(row.max()-row.min())<=1 for row in R])
print(f"\nDescriptive: all-4-identical on {exact*100:.0f}% of items; within-1-point on {adjacent*100:.0f}% of items")
print(f"Mean per-item SD across raters: {R.std(1, ddof=1).mean():.3f}")
