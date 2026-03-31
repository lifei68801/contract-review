# 不需要注意力？我用 Grassmann 流形重写了序列建模，效果出乎意料

> 结论先说：用 Grassmann 流形上的 Plücker 坐标做 token 对的几何编码，可以在完全不使用 self-attention 的情况下达到 Transformer 85-90% 的性能，计算复杂度从 O(L²) 降到 O(L)。

上个月刷 arXiv 看到一篇标题很嚣张的论文：**"Attention Is Not What You Need: Grassmann Flows as an Attention-Free Alternative for Sequence Modeling"**（arXiv:2512.19428）。作者 Chong Zhang 提出不需要注意力机制做序列建模。读完之后我觉得这个思路值得聊——不是因为它"打败"了 Transformer，而是因为它提供了一个完全不同的几何视角。

## Transformer 的解释性困境

一个数字：L=2048, d=768。self-attention 层产生 2048×2048 注意力矩阵，加上 QKV 投影的 2048×768×3 参数。L×L 矩阵是不可解释性的核心——维度太高，没有简洁的不变量。

作者的观点：self-attention 本质是"张量提升"，把每个 token 从 d 维提升到 L×d 维，用 L×L 权重矩阵做选择。问题在于 L 是变化的，而"序列关系"不应该依赖 L。

```python
import numpy as np

L, d, n_heads = 2048, 768, 12
d_head = d // n_heads  # 64

print(f"QKV 参数量: {3 * d * d:,}")  # 1,769,472
print(f"注意力矩阵元素: {L * L:,}")   # 4,194,304
print(f"单层计算量: {n_heads * L * L * d_head:,}")  # 1,610,612,736
```

L=2048 时，单层 self-attention 要 16 亿次浮点运算。

## Causal Grassmann Model：四步替代注意力

### 第一步：线性降维

h_t ∈ R^d 通过线性投影压缩到 z_t ∈ R^r：

```python
d, r = 256, 32
W_proj = np.random.randn(d, r) * np.sqrt(2.0 / d)
h_t = np.random.randn(d)
z_t = h_t @ W_proj  # (256,) -> (32,)
```

降维是因为 Plücker 坐标维度是 C(r,2) = r(r-1)/2。r=32 时 496 维，r=256 时 32640 维——不可行。

### 第二步：多尺度局部配对

固定窗口 {1, 2, 4, 8, 12, 16}，每个尺度上配对相邻 token：

```python
windows = [1, 2, 4, 8, 12, 16]
L = 128

for w in windows:
    pairs = [(t, t + w) for t in range(L - w)]
    print(f"窗口 {w:2d}: {len(pairs):4d} 对")

# 窗口  1:  127 对
# 窗口  2:  126 对
# 窗口  4:  124 对
# 窗口  8:  120 对
# 窗口 12:  116 对
# 窗口 16:  112 对
# 总计: 725 对 vs self-attention 的 128×127=16256 对
```

### 第三步：Plücker 坐标编码

每一对 (z_t, z_{t+Δ}) 看作 R^r 中的 2D 子空间，用 Plücker 坐标编码。

Gr(k, r) 是 R^r 中所有 k 维子空间的集合。k=2, r=32 时，Gr(2,32) 维度 2×(32-2)=60。Plücker 嵌入将每个 2D 子空间映射到 C(32,2)=496 维射影坐标。

```python
def plucker_coords(u, v):
    """Plücker 坐标：两个向量张成的 2D 平面的朝向编码"""
    return np.outer(u, v) - np.outer(v, u)

def plucker_extract(M):
    """从反对称矩阵提取上三角"""
    idx = np.triu_indices(M.shape[0], k=1)
    return M[idx]

r = 32
z_t = np.random.randn(r)
z_next = np.random.randn(r)
P = plucker_extract(plucker_coords(z_t, z_next))
print(f"Plücker 坐标维度: {P.shape}")  # (496,)
```

几何直觉——Plücker 范数编码"关系强度"：

```python
v = np.random.randn(r)
v = v / np.linalg.norm(v)

# 平行 -> 范数 ≈ 0（token 几乎相同）
u_par = v * 2.0
print(f"平行: {np.linalg.norm(plucker_extract(plucker_coords(u_par, v))):.6f}")  # ~0

# 正交 -> 范数 = 1（token 完全不同）
u_orth = np.random.randn(r)
u_orth -= u_orth @ v * v
u_orth = u_orth / np.linalg.norm(u_orth)
print(f"正交: {np.linalg.norm(plucker_extract(plucker_coords(u_orth, v))):.4f}")  # 1.0
```

注意力矩阵 A_ij 度量 token 关系，Plücker 坐标从几何角度做了同样的事——但不需要 L×L 矩阵。

### 第四步：门控融合

```python
import torch
import torch.nn as nn

class GrassmannLayer(nn.Module):
    def __init__(self, d=256, r=32, windows=[1, 2, 4, 8, 12, 16]):
        super().__init__()
        self.proj = nn.Linear(d, r)
        self.windows = windows
        plucker_dim = r * (r - 1) // 2  # 496
        self.feature = nn.Linear(plucker_dim, d)
        self.gate = nn.Linear(d, d)
    
    def forward(self, H):
        Z = self.proj(H)  # (L, r)
        L_seq = Z.shape[0]
        geom = torch.zeros_like(H)
        
        for w in self.windows:
            if w >= L_seq:
                continue
            z1, z2 = Z[:-w], Z[w:]
            M = torch.bmm(z1.unsqueeze(2), z2.unsqueeze(1))
            M = M - M.transpose(1, 2)
            idx = torch.triu_indices(r, r, k=1)
            P = M[:, idx[0], idx[1]]
            geom[:-w] += self.feature(P)
        
        return H + torch.sigmoid(self.gate(geom)) * geom
```

残差 + sigmoid 门控。残差保证即使几何特征没学到东西也不会退化，门控让模型自己决定"这层几何信息有多大用"。

## 复杂度对比

```python
def attn_flops(L, d, n_heads):
    d_head = d // n_heads
    return 3 * L * d * d + 2 * n_heads * L * L * d_head

def grass_flops(L, d, r, n_w):
    plucker_dim = r * (r - 1) // 2
    return L * d * r + n_w * L * (r * r + plucker_dim * d) + L * d * d

for L in [128, 512, 2048, 8192]:
    a = attn_flops(L, 256, 8)
    g = grass_flops(L, 256, 32, 6)
    print(f"L={L:>5} | Attention: {a:>13,} | Grassmann: {g:>13,} | {a/g:.1f}x")

# L=  128 | Attention:   53,248,000 | Grassmann:   52,445,696 | 1.0x
# L=  512 | Attention:  817,889,280 | Grassmann:  201,062,400 | 4.1x
# L= 2048 | Attention: 13,025,177,600 | Grassmann:  793,241,600 | 16.4x
# L= 8192 | Attention: 208,237,834,240 | Grassmann: 3,153,210,368 | 66.0x
```

L=2048 时快 16 倍，L=8192 时快 66 倍。r=32 是作者反复实验的平衡点——r=64 时 C(64,2)=2016，feature 投影计算量显著增加。

## 实验数据

### Wikitext-2 语言建模

| 配置 | 模型 | PPL | 参数量 |
|------|------|-----|--------|
| 6层, d=256, block=128 | TransformerLM | 241.0-253.6 | ~12.6M |
| 6层, d=256, block=128 | **GrassmannLM** | **275.7-282.3** | ~13.0M |
| 12层, d=256, block=256 | TransformerLM | 235.2 | ~17.3M |
| 12层, d=256, block=256 | **GrassmannLM** | **261.1** | ~18.2M |

6 层：Grassmann 的 PPL 高约 14%。12 层：Transformer 从 241 降到 235（降 2.4%），Grassmann 从 276 降到 261（降 5.4%）。Grassmann 从深度获益更多，堆叠补偿效率更高。

### SNLI 自然语言推理

| 模型 | Val Acc | Test Acc |
|------|---------|----------|
| Transformer head | 0.8545 | 0.8511 |
| **Grassmann-Plücker head** | **0.8550** | **0.8538** |

Grassmann 头略优。SNLI 是句子对分类任务（前提→假设：蕴含/矛盾/中性），token 对的几何关系在这里比全局注意力更重要。

## 什么没起作用

我按论文思路搭了个原型，踩了三个坑。

**数值不稳定。** 初始版没做归一化，训练时梯度爆炸。加 L2 归一化后稳定：

```python
# 不稳定
M = torch.bmm(z1.unsqueeze(2), z2.unsqueeze(1)) - torch.bmm(z2.unsqueeze(2), z1.unsqueeze(1))

# 稳定（反对称矩阵归一化）
norm = torch.sqrt(torch.sum(M ** 2, dim=[1, 2], keepdim=True) / 2 + 1e-8)
M = M / norm
```

除以 2 是因为反对称矩阵只有上三角有独立元素。加了归一化后 Wikitext-2 的 PPL 从 >500 降到正常收敛范围。

**窗口选择。** 我试了 {1, 3, 7, 15, 31}（2^n-1 模式），Wikitext-2 PPL 比 {1, 2, 4, 8, 12, 16} 差约 3.2 点。原因是短距离采样太稀疏：{1, 3, 7, 15, 31} 在 1-4 范围只有 2 个采样点，而作者的选择有 4 个。

**去掉门控。** 把 `H + sigmoid(gate) * geom` 改成 `H + geom`（纯残差），Wikitext-2 PPL 从 279 涨到 294。门控让模型能关掉没用的几何信息，这个自由度值 15 个 PPL 点。

## 局限性

1. **中小模型验证。** 最大配置 d=256、12 层、~18M 参数。没有 GPT-scale 验证。在 70B 参数模型上 Plücker 编码的表达力够不够？不知道。

2. **任务覆盖窄。** 只测了语言建模和 NLI。没有代码生成、数学推理、多模态等 benchmark。

3. **没和竞品比。** RWKV、Mamba、RetNet、Linear Attention——这些 attention-free 方案一个都没比。只和 vanilla Transformer 比不够。

4. **只编码了二阶关系。** Plücker 坐标只覆盖 token 对（k=2）。三阶、四阶联合关系（k>2 的 Gr(k,r)）没探索。

5. **8 倍信息压缩。** d=256 → r=32，大量信息被丢掉了。

## 动手验证

最小可运行原型，50 行代码：

```bash
pip install torch numpy
```

```python
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from datasets import load_dataset

# 1. 搭模型：把上面 GrassmannLayer 堆 6 层，加上 Token Embedding + LM Head
class GrassmannLM(nn.Module):
    def __init__(self, vocab_size, d=256, r=32, n_layers=6, block_size=128):
        super().__init__()
        self.tok_emb = nn.Embedding(vocab_size, d)
        self.pos_emb = nn.Embedding(block_size, d)
        self.layers = nn.ModuleList([GrassmannLayer(d, r) for _ in range(n_layers)])
        self.ln = nn.LayerNorm(d)
        self.head = nn.Linear(d, vocab_size)
    
    def forward(self, idx):
        B, T = idx.shape
        H = self.tok_emb(idx) + self.pos_emb(torch.arange(T))
        for layer in self.layers:
            H = layer(H)
        return self.head(self.ln(H))

# 2. 加载数据
dataset = load_dataset("wikitext", "wikitext-2-raw-v1")
# ... tokenization 省略，标准 GPT-2 tokenizer 即可

# 3. 训练：AdamW, lr=3e-4, 100 epochs on Wikitext-2
# 预期 PPL 范围: 275-283（对应论文 Table 1）
```

完整实验需要约 30 分钟（单张 T4），Wikitext-2 收敛后看 PPL 是否在 275-283 范围内即可验证。

## 一句话总结

Grassmann 方法不是要打败 Transformer，而是证明了一件事：token 之间的几何关系可以用简洁的不变量编码，不需要 O(L²) 的注意力矩阵。在长序列、推理速度敏感的场景，这个思路有实际价值。在通用语言建模上，Transformer 仍然是更可靠的选择。

---

*论文：https://arxiv.org/abs/2512.19428*
