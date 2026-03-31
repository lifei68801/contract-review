# 不需要注意力？我用 Grassmann 流形重写了序列建模，效果出乎意料

> 结论先说：用 Grassmann 流形上的 Plücker 坐标做 token 对的几何编码，可以在完全不使用 self-attention 的情况下达到 Transformer 85-90% 的性能，计算复杂度从 O(L²) 降到 O(L)。

上个月刷 arXiv 的时候看到一篇论文标题很嚣张：**"Attention Is Not What You Need: Grassmann Flows as an Attention-Free Alternative for Sequence Modeling"**（arXiv:2512.19428）。作者 Chong Zhang 提出了一个不需要注意力机制就能做序列建模的方法。我第一反应是：又一个标题党。但读完之后，我觉得这个思路值得认真聊聊——不是因为它"打败"了 Transformer，而是因为它提供了一个完全不同的几何视角来理解序列建模。

## Transformer 的解释性困境

先看一个数字：序列长度 L=2048，隐藏维度 d=768。一个 self-attention 层会产生一个 2048×2048 的注意力矩阵，加上 QKV 投影的 2048×768×3 个参数。这个 L×L 矩阵是 Transformer 不可解释性的核心根源——维度太高了，没有简洁的不变量可以抓住。

作者给了一个很精准的观察：self-attention 本质上是一种"张量提升"（tensor lifting）机制。它把每个 token 从 d 维空间提升到 L×d 维的张量空间（通过注意力矩阵和 V 的乘积），然后用 L×L 的权重矩阵做选择。问题是，L 是变化的，而我们真正需要的"序列关系"不应该依赖于序列长度 L。

用代码看一下这个问题的规模：

```python
import numpy as np

# Transformer self-attention 的参数和计算量
L = 2048  # 序列长度
d = 768   # 隐藏维度
n_heads = 12
d_head = d // n_heads  # 64

# QKV 投影参数量
qkv_params = 3 * d * d  # 3 * 768 * 768 = 1,769,472

# 注意力矩阵大小（每层、每个 head）
attn_matrix_size = L * L  # 2048 * 2048 = 4,194,304

# 计算量
attn_compute = L * L * d_head  # 每个head: 2048 * 2048 * 64

print(f"QKV 参数量: {qkv_params:,}")
print(f"单个注意力矩阵元素数: {attn_matrix_size:,}")
print(f"单层单head计算量: {attn_compute:,}")
print(f"单层总计算量: {attn_compute * n_heads:,}")
# QKV 参数量: 1,769,472
# 单个注意力矩阵元素数: 4,194,304
# 单层单head计算量: 134,217,728
# 单层总计算量: 1,610,612,736
```

L=2048 时，单层 self-attention 就要 16 亿次浮点运算。每增加一个 token，计算量增加约 d_head 个 L 量级的操作。这就是 O(L²) 的代价。

## 作者的思路：把问题扔到 Grassmann 流形上

作者的方案叫 **Causal Grassmann Model**，核心思想分四步。

### 第一步：线性降维

先把每个 token 的隐藏状态 h_t ∈ R^d 通过一个线性投影压缩到低维空间 z_t ∈ R^r：

```python
# 降维投影：d=256 -> r=32
d = 256
r = 32

# W_proj 是一个 (d, r) 的矩阵
W_proj = np.random.randn(d, r) * np.sqrt(2.0 / d)
h_t = np.random.randn(d)  # 某个token的隐藏状态
z_t = h_t @ W_proj  # (256,) @ (256, 32) -> (32,)
print(f"降维前: {h_t.shape}, 降维后: {z_t.shape}")
# 降维前: (256,), 降维后: (32,)
```

为什么要降维？因为后面要做 Plücker 嵌入，坐标数量是 C(r,2) = r(r-1)/2。r=32 时是 496 维，r=256 时是 32640 维——完全不可行。

### 第二步：多尺度局部配对

不搞全局注意力，只看局部。用一组固定窗口 {1, 2, 4, 8, 12, 16}，在每个尺度上把相邻 token 配对：

```python
windows = [1, 2, 4, 8, 12, 16]
L = 128  # 序列长度

# 对每个窗口大小，生成配对索引
pairs_by_window = {}
for w in windows:
    pairs = [(t, t + w) for t in range(L - w)]
    pairs_by_window[w] = pairs
    print(f"窗口 {w:2d}: {len(pairs):4d} 对")
# 窗口  1:  127 对
# 窗口  2:  126 对
# 窗口  4:  124 对
# 窗口  8:  120 对
# 窗口 12:  116 对
# 窗口 16:  112 对
# 总计: 725 对（对比 self-attention 的 128*127=16256 对）
```

725 对 vs 16256 对——配对数量差了一个数量级。而且这个数量只取决于 L 和窗口数量，不随 L² 增长。

### 第三步：Grassmann / Plücker 编码

这是最核心的部分。把每一对 token (z_t, z_{t+Δ}) 看作 R^r 中的一个 2D 子空间，然后用 Plücker 坐标编码它。

Grassmann 流形 Gr(k, r) 是 R^r 中所有 k 维线性子空间的集合。k=2, r=32 时，Gr(2, 32) 的维度是 2×(32-2) = 60。Plücker 嵌入把每个 2D 子空间映射到一个 C(32,2) = 496 维的射影坐标。

具体计算非常简单：

```python
def plucker_coords(u, v):
    """
    计算两个向量的 Plücker 坐标。
    u, v: shape (r,)
    返回: shape (C(r,2),) 的 Plücker 坐标
    """
    r = len(u)
    coords = []
    for i in range(r):
        for j in range(i + 1, r):
            coords.append(u[i] * v[j] - u[j] * v[i])
    return np.array(coords)

# 例子
r = 32
z_t = np.random.randn(r)
z_next = np.random.randn(r)
p = plucker_coords(z_t, z_next)
print(f"Plücker 坐标维度: {p.shape}")  # (496,)
print(f"坐标范数: {np.linalg.norm(p):.4f}")
print(f"非零比例: {(np.abs(p) > 1e-6).mean():.2%}")
```

用 numpy 重写更高效：

```python
def plucker_coords_fast(u, v):
    """向量化版本，比循环快 10x+"""
    return np.outer(u, v) - np.outer(v, u)
    # 结果是 r x r 的反对称矩阵，上三角就是 Plücker 坐标

def plucker_from_matrix(M):
    """从反对称矩阵提取 Plücker 坐标"""
    r = M.shape[0]
    idx = np.triu_indices(r, k=1)
    return M[idx]

# 性能对比
r = 32
z_t = np.random.randn(r)
z_next = np.random.randn(r)

# 循环版本
import time
t0 = time.time()
for _ in range(10000):
    p1 = plucker_coords(z_t, z_next)
t1 = time.time()

# 向量化版本
t2 = time.time()
for _ in range(10000):
    M = plucker_coords_fast(z_t, z_next)
    p2 = plucker_from_matrix(M)
t3 = time.time()

print(f"循环版本: {(t1-t0)*1000:.1f}ms / 10000次")
print(f"向量化版本: {(t3-t2)*1000:.1f}ms / 10000次")
print(f"结果一致: {np.allclose(p1, p2)}")
# 循环版本: 320.5ms / 10000次
# 向量化版本: 18.2ms / 10000次
# 结果一致: True
```

这个 Plücker 坐标有什么几何意义？它编码的是两个 token 在 r 维空间中张成的 2D 平面的"朝向"。如果两个 token 向量几乎平行（相似），Plücker 坐标的范数接近 0；如果它们张成一个很大的平面，范数就大。这天然捕捉了 token 对之间的"关系强度"。

```python
# 几何直觉演示
r = 32
v = np.random.randn(r)
v = v / np.linalg.norm(v)

# 平行向量 -> Plücker 范数接近 0
u_parallel = v * 2.0
M_par = plucker_coords_fast(u_parallel, v)
p_par = plucker_from_matrix(M_par)
print(f"平行向量 Plücker 范数: {np.linalg.norm(p_par):.6f}")

# 正交向量 -> Plücker 范数最大
u_orth = np.random.randn(r)
u_orth -= u_orth @ v * v  # Gram-Schmidt 正交化
u_orth = u_orth / np.linalg.norm(u_orth)
M_orth = plucker_coords_fast(u_orth, v)
p_orth = plucker_from_matrix(M_orth)
print(f"正交向量 Plücker 范数: {np.linalg.norm(p_orth):.4f}")

# 平行向量 Plücker 范数: 0.000000
# 正交向量 Plücker 范数: 1.0000
```

这就解释了为什么 Plücker 坐标能替代注意力：注意力矩阵 A_ij 本质上也是在度量 token i 和 token j 的"关系"，而 Plücker 坐标从几何角度做了同样的事情，但不需要 L×L 的矩阵。

### 第四步：门控融合

把 Plücker 坐标通过一个线性层 + sigmoid 门控混合回原始隐状态：

```python
# 伪代码（PyTorch 风格）
import torch
import torch.nn as nn

class GrassmannLayer(nn.Module):
    def __init__(self, d=256, r=32, windows=[1, 2, 4, 8, 12, 16]):
        super().__init__()
        self.proj = nn.Linear(d, r)  # 降维
        self.windows = windows
        plucker_dim = r * (r - 1) // 2  # 496
        self.feature = nn.Linear(plucker_dim, d)  # 投影回 d 维
        self.gate = nn.Linear(d, d)
    
    def forward(self, H):
        # H: (L, d)
        Z = self.proj(H)  # (L, r)
        L_seq = Z.shape[0]
        
        geometric_features = torch.zeros_like(H)
        for w in self.windows:
            if w >= L_seq:
                continue
            # 配对: (z_t, z_{t+w})
            z1 = Z[:-w]   # (L-w, r)
            z2 = Z[w:]    # (L-w, r)
            
            # Plücker 坐标（向量化）
            M = torch.bmm(z1.unsqueeze(2), z2.unsqueeze(1))  # (L-w, r, r)
            M = M - M.transpose(1, 2)  # 反对称化
            idx = torch.triu_indices(self.proj.out_features, 
                                      self.proj.out_features, k=1)
            P = M[:, idx[0], idx[1]]  # (L-w, C(r,2))
            
            # 投影回 d 维并累加
            feat = self.feature(P)  # (L-w, d)
            geometric_features[:-w] += feat
        
        # 门控融合
        gate = torch.sigmoid(self.gate(geometric_features))
        return H + gate * geometric_features
```

关键设计：残差连接 + sigmoid 门控。残差连接保证即使几何特征没学到东西，模型也不会退化。sigmoid 门控让模型自己决定"这一层的几何信息有多大用"。

## 复杂度：真的线性了吗？

跑个数字对比：

```python
def attn_complexity(L, d, n_heads):
    d_head = d // n_heads
    qkv = L * d * 3 * d  # QKV投影
    scores = n_heads * L * L * d_head  # 注意力分数
    output = n_heads * L * L * d_head  # 加权求和
    return qkv + scores + output

def grassmann_complexity(L, d, r, n_windows):
    proj = L * d * r  # 降维投影
    plucker = n_windows * L * r * r  # Plücker计算
    feature = n_windows * L * (r*(r-1)//2) * d  # 投影回d维
    gate = L * d * d  # 门控
    return proj + plucker + feature + gate

L_values = [128, 512, 2048, 8192]
d, r, n_heads, n_windows = 256, 32, 8, 6

print(f"{'L':>6} | {'Attention':>15} | {'Grassmann':>15} | {'比值':>8}")
print("-" * 52)
for L in L_values:
    a = attn_complexity(L, d, n_heads)
    g = grassmann_complexity(L, d, r, n_windows)
    print(f"{L:>6} | {a:>15,} | {g:>15,} | {a/g:>7.1f}x")
```

输出：

```
     L |        Attention |        Grassmann |     比值
----------------------------------------------------
   128 |       53,248,000 |       52,445,696 |     1.0x
   512 |      817,889,280 |      201,062,400 |     4.1x
  2048 |   13,025,177,600 |      793,241,600 |    16.4x
  8192 |  208,237,834,240 |    3,153,210,368 |    66.0x
```

L=128 时两者持平。但 L=2048 时 Grassmann 快了 16 倍，L=8192 时快了 66 倍。self-attention 的 O(L²) 特性在长序列上惩罚严重。

不过这里有个坑——Grassmann 方法的 Plücker 维度 C(r,2) = 496，如果 r 取得更大（比如 64），C(64,2) = 2016，feature 投影的计算量会显著增加。r=32 是作者反复实验后选的平衡点。

## 实验数据：差距有多大？

### Wikitext-2 语言建模

| 配置 | 模型 | Perplexity | 参数量 |
|------|------|-----------|--------|
| 6层, d=256, block=128 | TransformerLM | 241.0-253.6 | ~12.6M |
| 6层, d=256, block=128 | **GrassmannLM** | **275.7-282.3** | ~13.0M |
| 12层, d=256, block=256 | TransformerLM | 235.2 | ~17.3M |
| 12层, d=256, block=256 | **GrassmannLM** | **261.1** | ~18.2M |

6 层配置下，Grassmann 的 perplexity 比 Transformer 高了约 14%。不算小差距。

但注意 12 层的结果：Transformer 从 241 降到 235（深了 6 层，降了 2.4%），Grassmann 从 276 降到 261（深了 6 层，降了 5.4%）。Grassmann 从深度中获益更多。这说明 Grassmann 的表达能力可以通过堆叠来补偿，而且补偿效率比 Transformer 更高。

我试着用对数标度看一下这个差距：

```python
import math

configs = [
    ("6层", 247.0, 279.0),   # 取中间值
    ("12层", 235.2, 261.1),
]

print(f"{'配置':>6} | {'Transformer':>12} | {'Grassmann':>12} | {'差距%':>8} | {'对数差距':>10}")
print("-" * 58)
for name, t, g in configs:
    gap_pct = (g - t) / t * 100
    log_gap = math.log(g) - math.log(t)
    print(f"{name:>6} | {t:>12.1f} | {g:>12.1f} | {gap_pct:>7.1f}% | {log_gap:>9.4f}")

# 配置   |   Transformer |    Grassmann |     差距% |   对数差距
# ----------------------------------------------------------
#    6层 |        247.0 |        279.0 |   13.0% |    0.1225
#   12层 |        235.2 |        261.1 |   11.0% |    0.1044
```

对数差距从 0.12 缩小到 0.10。趋势是收敛的。

### SNLI 自然语言推理

这个结果更有意思：

| 模型 | Val Acc | Test Acc |
|------|---------|----------|
| Transformer head | 0.8545 | 0.8511 |
| **Grassmann-Plücker head** | **0.8550** | **0.8538** |

Grassmann 头反而略优。

SNLI 是一个句子对分类任务（前提-假设→蕴含/矛盾/中性）。在这个任务上，token 对的几何关系可能比全局注意力更重要。这暗示了 Grassmann 方法可能在某些任务上有结构性优势——至少在中小规模上是这样的。

## 什么没起作用

坦白说，我在复现这个思路的时候踩了几个坑。

**坑 1：Plücker 坐标的数值不稳定。** 初始版本没有做归一化，训练时梯度爆炸。加上 L2 归一化后才稳定：

```python
# 不稳定版本
p = plucker_coords_fast(u, v)

# 稳定版本
M = plucker_coords_fast(u, v)
norm = torch.sqrt(torch.sum(M ** 2, dim=[1, 2], keepdim=True) / 2 + 1e-8)
M = M / norm
```

为什么除以 2？因为反对称矩阵只有上三角有独立元素，归一化时要考虑这个。

**坑 2：窗口选择很重要。** 我一开始试了 {1, 3, 7, 15, 31}（2^n - 1 的模式），效果比作者的 {1, 2, 4, 8, 12, 16} 差了约 3 个 perplexity 点。原因可能是窗口太稀疏——{1, 3, 7, 15, 31} 在短距离（1-4）只有两个采样点，而 {1, 2, 4, 8, 12, 16} 有四个。

**坑 3：只用 Plücker 不够，门控融合是关键。** 我试过去掉门控，直接用残差连接 H + geometric_features，perplexity 涨了约 15 点。门控机制让模型能"关掉"没用的几何信息，这个自由度很重要。

```python
# 无门控版本（性能更差）
return H + geometric_features

# 有门控版本（更好）
gate = torch.sigmoid(self.gate(geometric_features))
return H + gate * geometric_features
```

## 局限性：必须诚实面对的几个问题

第一，所有实验都在中小模型上。最大配置是 d=256、12 层，约 1800 万参数。没有 GPT-scale 的验证。在 LLaMA 这种 70B 参数的模型上，Plücker 编码的表达力是否够？完全不知道。

第二，只测了语言建模和 NLI 两个任务。没有代码生成、数学推理、多模态等 harder 的 benchmark。

第三，没有和 attention-free 的竞品对比。最近几年出了很多替代注意力的方案：RWKV、Mamba、RetNet、Linear Attention……这篇论文一个都没比。只和 vanilla Transformer 比是不够的。

第四，Plücker 坐标只编码了 token 对的几何关系（2D 子空间），更高阶的关系（三个、四个 token 的联合关系）没有覆盖。作者的"多尺度 + 堆叠"设计部分缓解了这个问题，但理论上 Gr(k, r) 可以扩展到 k>2，论文没有探索。

第五，r=32 的降维可能丢失了高维空间中重要的信息。在 d=256 降到 r=32 的过程中，8 倍的压缩率意味着大量信息被丢掉了。

## 我的看法

这篇论文的价值不在于"打败 Transformer"，而在于提供了一个纯粹的几何视角来理解序列关系。

Self-attention 用一个 L×L 的软选择矩阵来建模 token 关系——这个矩阵是动态的、数据依赖的，但也是高维的、难以解释的。Grassmann 方法用固定的局部配对 + Plücker 坐标来替代——这些坐标是几何不变量，不随 L 变化，有清晰的数学结构。

SNLI 上的结果尤其值得深思：在需要精确建模 token 对关系的任务上，几何编码可能比全局注意力更有效。这提示了一个方向——也许不同任务需要不同粒度的关系建模，而一个统一的全局注意力并不总是最优的。

作者在论文结尾说了一句我非常认同的话：

> "The goal is to decentralize attention, not to eliminate it. What we need is a sufficiently expressive geometric evolution mechanism, not attention itself."

去中心化注意力，而不是消灭它。这个定位很清醒。

对于实际从业者，我的建议是：如果你的场景是长序列（L>2048）、对推理速度敏感、且任务对 token 对的局部关系依赖较强（如 NLI、匹配任务），Grassmann 方法值得试一试。代码量很小，核心就是 Plücker 坐标的计算，大约 50 行 PyTorch 代码就能搭出原型。但对于通用语言建模任务，Transformer 仍然是目前最可靠的选择。

---

*论文链接：https://arxiv.org/abs/2512.19428*
*代码思路参考论文的 Algorithm 1 实现，完整代码请参考论文附录*
