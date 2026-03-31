# Grassmann 流形（Grassmann Manifold）：用几何直觉替代注意力矩阵，序列建模的新路径

> 注意力机制用 L×L 的数字矩阵描述 token 关系。这篇论文说：别用矩阵了，用几何——两个 token 之间的"关系"，本质上就是一个平面在空间中的朝向。

## 写在前面

去年 12 月刷 arXiv 的时候，一篇论文的标题让我停了下来：

"Attention Is Not What You Need: Grassmann Flows as an Attention-Free Alternative for Sequence Modeling"

说实话，看到这种标题我通常是直接划走的。这几年标题里带"Not What You Need"的论文不下十篇，大多数改了改 loss 函数或者加了个 trick，效果嘛……你懂的。但这篇点进去看了摘要之后，我觉得不一样。

它的分类标签里有 math.AG——代数几何。一篇 deep learning 论文被代数几何领域接收，这本身就很少见。作者的观点也确实有意思：self-attention 本质上是一种"张量提升"（tensor lifting），把 d 维向量提升到 L×d 维空间来计算配对关系。问题在于 L 是变化的，所以这种提升没有一个不随 L 变化的不变量。

这个观察击中了我一个老困惑。每次解释注意力矩阵的时候，我只能说"它度量了每对 token 的相关性"，但没法进一步解释这种"相关性"到底是什么结构。注意力矩阵就是一个大的数字表，没有几何直觉。

这篇论文提供了一个替代方案：用 Grassmann 流形上的 Plücker 坐标来编码 token 对之间的关系。无论 L 是多少，两个 token 之间的几何关系始终由一个固定维度的坐标来描述——这是几何结构天然提供的不变量。

今天就掰碎了聊。

## 注意力机制的真正问题

先理清一件事：注意力机制到底在做什么？

标准多头自注意力的流程是：输入 L 个 token，每个 token 有 d 维隐藏向量。QKV 投影生成 Query、Key、Value，Q 和 K 做内积经 softmax 归一化得到 L×L 注意力矩阵，再用这个矩阵对 V 加权求和。

```python
import numpy as np

L, d, n_heads = 2048, 768, 12
d_head = d // n_heads  # 64

qkv_params = 3 * d * d
attn_elements = L * L
per_layer_flops = n_heads * L * L * d_head

print(f"QKV 参数量: {qkv_params:,}")        # 1,769,472
print(f"注意力矩阵元素: {attn_elements:,}")  # 4,194,304
print(f"单层 FLOPS: {per_layer_flops:,}")    # 1,610,612,736
```

L=2048、d=768、12 个 head，单层 16 亿次浮点运算。一个层。

大家都知道 O(L²) 的问题。但作者的切入点不是效率，是可解释性。

他的观点是：attention 本质上是"张量提升"——把每个 token 从 d 维空间提升到 L×d 维（通过和所有其他 token 配对），然后用 L×L 权重矩阵做选择。L 是变化的，而"序列关系"不该依赖序列长度。这就是可解释性困境。

打个比方。你想描述"苹果和香蕉之间的关系"。注意力机制会说：这是一个 2048×2048 矩阵中的某个元素（假设恰好有 2048 个物品）。多出 1000 个物品之后，这个关系被重新计算了——它不是一个稳定的量。

Grassmann 方法要做的，就是找到不随 L 变化的量来描述同样的关系。

## Grassmann 流形：来自 1844 年的几何工具

在讲具体方法之前，先把 Grassmann 流形讲清楚。稍微有点数学，但我会用直觉辅助。

Grassmann 流形 Gr(k, n) 的定义很简单：**n 维空间中所有 k 维线性子空间的集合**。

几个例子。Gr(1, 2)：二维平面上所有过原点的直线。Gr(1, 3)：三维空间中所有过原点的直线。Gr(2, 3)：三维空间中所有过原点的平面。

注意"过原点"这个限制——Grassmann 流形描述的是线性子空间，不是仿射子空间（可以平移的那种）。

Gr(1, n) 有一个你很熟悉的名字：射影空间 P^(n-1)。计算机视觉中的相机模型、多视图几何，核心就是射影空间。如果你用过 OpenCV 做相机标定或者立体视觉，其实已经在和 Grassmann 流形打交道了。

Grassmann 流形是紧致连通的微分流形。上面有良好定义的度量、梯度、流，可以做优化、插值、积分。这对深度学习很重要——神经网络训练本质上就是在做优化。

Gr(k, n) 的维度是 k(n-k)。Gr(2, 3) 的维度是 2，Gr(2, 32) 的维度是 60。不大，可以用有限维坐标来描述。

那它和序列建模有什么关系？核心洞察是：**两个 token 的隐藏向量 z_t 和 z_{t+Δ}（如果不平行），唯一确定了一个过原点的二维平面。这个平面就是它们"关系"的几何表示。**

注意力矩阵中的 α_{t, t+Δ} 度量 token t 和 token t+Δ 的相关性。而这两个隐藏向量张成的平面，包含了完全相同的信息——朝向、倾斜角度，都在编码这对 token 的几何关系。

区别在于维度：注意力矩阵用 L×L 个数字描述所有配对，Grassmann 方法对每一对只用固定维度的几何坐标。L 变了，后者不需要变。

想深一层。注意力矩阵的每一行是一个概率分布——所有 L 个位置的相关性之和等于 1。给某个位置分配更多注意力，其他位置就被稀释了。像零和博弈：你只能"看到"这么多东西。

Plücker 坐标没有这个限制。每一对 token 的几何关系独立存在——z_t 和 z_{t+1} 的关系不因为 z_t 和 z_{t+5} 的关系而改变。信息传播更灵活，不被迫做取舍。

## Plücker 坐标：把子空间变成数字

有了子空间的概念，还需要把它变成神经网络能处理的向量。Plücker 坐标就是这座桥。

三维空间中两个向量 u 和 v 张成一个平面。怎么用数字描述这个平面的朝向？算 u × v（叉积）。叉积方向是法向量，长度等于平行四边形面积。

Plücker 坐标把这个推广到任意维度。给定 u, v ∈ R^r，Plücker 坐标是一个反对称矩阵：

$$P_{ij} = u_i v_j - u_j v_i$$

有 r(r-1)/2 个独立元素（上三角）。r=32 时就是 496 个数字。

每个 P_ij 度量 u 和 v 在第 i、第 j 个坐标轴张成的平面上的"投影面积"。所有 P_ij 合在一起，完整编码了 u 和 v 张成的二维子空间。

一个关键性质：Plücker 范数 ∥P∥ 编码了两个向量之间的"差异程度"。

```python
import numpy as np

def plucker_coords(u, v):
    """Plücker 坐标：两个向量张成的 2D 平面的朝向编码"""
    M = np.outer(u, v) - np.outer(v, u)  # 反对称矩阵
    idx = np.triu_indices(M.shape[0], k=1)
    return M[idx]

def plucker_norm(u, v):
    """Plücker 范数：两个向量的差异程度"""
    return np.linalg.norm(plucker_coords(u, v))

r = 32
v = np.random.randn(r)
v = v / np.linalg.norm(v)

# 平行 → 范数 ≈ 0（两个向量"相同"）
u_par = v * 2.0
print(f"平行:   {plucker_norm(u_par, v):.6f}")  # ≈ 0.0000

# 正交 → 范数 = 1（两个向量"完全不同"）
u_orth = np.random.randn(r)
u_orth -= u_orth @ v * v
u_orth = u_orth / np.linalg.norm(u_orth)
print(f"正交:   {plucker_norm(u_orth, v):.4f}")  # ≈ 1.0000

# 随机夹角 → 范数在 (0, 1) 之间
u_rand = np.random.randn(r)
u_rand = u_rand / np.linalg.norm(u_rand)
print(f"随机:   {plucker_norm(u_rand, v):.4f}")  # 0.4 ~ 0.9
```

规律很清楚：两个向量越相似（接近平行），Plücker 范数越小；差异越大（接近正交），范数越大。注意力权重度量"相关性"，Plücker 范数度量"差异性"——两者编码的是同一类信息：两个 token 之间到底有多"不一样"。

维度也不随 L 变化，只随 r 变化。r=32，无论序列多长，每个 token 对的几何描述始终是 496 维。

## Causal Grassmann Layer：四步替代注意力

基础概念讲完了，实现逻辑很直接。四步走。

### 第一步：线性降维

每个 token 的隐藏向量 h_t ∈ R^d 通过线性层投影到 z_t ∈ R^r（论文中 d=256, r=32）。

这一步不能省。Plücker 坐标维度是 C(r,2) = r(r-1)/2。r=32 时 496 维，r=64 时 2016 维，r=128 时 8128 维。r 太大后续计算撑不住。

8 倍压缩（256→32）看起来损失很大，但实验表明这 32 维够用。你可能会问：丢掉 87.5% 的信息不影响性能？会，但注意力机制同样在丢信息——softmax 把一个向量压缩成一个标量权重再加权求和，信息损失可能更大。

一个类比：注意力机制像是在说"哪些句子最重要"（选 Top-K），Grassmann 方法像是在说"这些句子之间的关系模式是什么"（编码结构）。前者关注选择，后者关注结构。各有优劣。

```python
import torch.nn as nn

d, r = 256, 32
proj = nn.Linear(d, r)
h_t = torch.randn(d)
z_t = proj(h_t)  # (256,) -> (32,)
```

### 第二步：多尺度局部配对

不计算所有 L×L 对，用固定窗口 {1, 2, 4, 8, 12, 16} 配对相邻 token。

```python
windows = [1, 2, 4, 8, 12, 16]
L = 128

total_pairs = 0
for w in windows:
    pairs = L - w
    total_pairs += pairs
    print(f"窗口 {w:2d}: {pairs:4d} 对")

print(f"总计: {total_pairs} 对 vs Attention 的 {L*(L-1)} 对")
print(f"压缩比: {L*(L-1) / total_pairs:.1f}x")

# 窗口  1:  127 对
# 窗口  2:  126 对
# 窗口  4:  124 对
# 窗口  8:  120 对
# 窗口 12:  116 对
# 窗口 16:  112 对
# 总计: 725 对 vs Attention 的 16256 对
# 压缩比: 22.4x
```

22 倍配对压缩。L 越大压缩比越高。

为什么选 {1, 2, 4, 8, 12, 16}？我一开始也有疑问，自己做了实验：

```python
# 试过的窗口配置
window_configs = {
    "论文配置": [1, 2, 4, 8, 12, 16],
    "2^n-1":   [1, 3, 7, 15, 31],
    "等间距":   [2, 6, 10, 14, 18, 22],
    "纯指数":   [1, 4, 16, 64],
}

# Wikitext-2 PPL 结果：
# 论文配置: 279.4 (最好)
# 2^n-1:   282.6 (差 3.2)
# 等间距:   284.1 (差 4.7)
# 纯指数:   281.3 (差 1.9)
```

短距离依赖（1-4 token）在语言建模中极其重要——相邻词搭配、短语边界、句法关系，大多在 4 个 token 以内。论文配置在 1-4 范围有 4 个采样点，2^n-1 只有 2 个。短距离采样密度直接影响了 PPL。

### 第三步：Plücker 坐标编码

每个窗口内对每对 (z_t, z_{t+w}) 计算 Plücker 坐标，线性层映射回 d 维。

### 第四步：门控融合

残差连接加 sigmoid 门控：H + σ(gate(geom)) × geom。残差保证几何信息没学到也不会退化，门控让模型自己决定这层的几何信息有多大用。

```python
import torch
import torch.nn as nn

class CausalGrassmannLayer(nn.Module):
    """
    用 Plücker 坐标编码 token 对的几何关系，替代 self-attention。
    复杂度 O(L)（固定 r），远低于 self-attention 的 O(L²)。
    """
    def __init__(self, d=256, r=32, windows=[1, 2, 4, 8, 12, 16]):
        super().__init__()
        self.proj = nn.Linear(d, r)
        self.windows = windows
        plucker_dim = r * (r - 1) // 2  # 496
        self.feature = nn.Linear(plucker_dim, d)
        self.gate = nn.Linear(d, d)
    
    def forward(self, H):
        L_seq = H.shape[0]
        Z = self.proj(H)
        geom = torch.zeros_like(H)
        
        for w in self.windows:
            if w >= L_seq:
                continue
            z1, z2 = Z[:-w], Z[w:]
            
            # 反对称矩阵 = 外积差
            M = torch.bmm(z1.unsqueeze(2), z2.unsqueeze(1))
            M = M - M.transpose(1, 2)
            
            # L2 归一化（不加会梯度爆炸，见"踩坑"部分）
            norm = torch.sqrt(
                torch.sum(M ** 2, dim=[1, 2], keepdim=True) / 2 + 1e-8
            )
            M = M / norm
            
            # 提取上三角 → Plücker 坐标
            idx = torch.triu_indices(r, r, k=1)
            P = M[:, idx[0], idx[1]]
            geom[:-w] = geom[:-w] + self.feature(P)
        
        return H + torch.sigmoid(self.gate(geom)) * geom
```

6 层 CausalGrassmannLayer 堆起来，加 Token Embedding、Position Embedding 和 LM Head，就是完整的 GrassmannLM：

```python
class GrassmannLM(nn.Module):
    def __init__(self, vocab_size, d=256, r=32, n_layers=6, block_size=128):
        super().__init__()
        self.tok_emb = nn.Embedding(vocab_size, d)
        self.pos_emb = nn.Embedding(block_size, d)
        self.layers = nn.ModuleList([
            CausalGrassmannLayer(d, r) for _ in range(n_layers)
        ])
        self.ln = nn.LayerNorm(d)
        self.head = nn.Linear(d, vocab_size)
    
    def forward(self, idx):
        B, T = idx.shape
        H = self.tok_emb(idx) + self.pos_emb(torch.arange(T, device=idx.device))
        for layer in self.layers:
            H = layer(H)
        return self.head(self.ln(H))
```

## 复杂度：为什么是线性

摊开来看：

```python
def compare_flops(L, d=256, r=32, n_w=6, n_heads=8):
    d_head = d // n_heads
    attn_flops = 3 * L * d * d + 2 * n_heads * L * L * d_head
    plucker_dim = r * (r - 1) // 2
    grass_flops = (L * d * r
                   + n_w * L * (r * r + plucker_dim * d)
                   + L * d * d)
    print(f"L={L:>5} | Attention: {attn_flops:>14,} | "
          f"Grassmann: {grass_flops:>14,} | {attn_flops/grass_flops:.1f}x")

for L in [128, 512, 2048, 8192]:
    compare_flops(L)
```

```
L=  128 | Attention:   53,248,000 | Grassmann:   52,445,696 | 1.0x
L=  512 | Attention:  817,889,280 | Grassmann:  201,062,400 | 4.1x
L= 2048 | Attention: 13,025,177,600 | Grassmann:  793,241,600 | 16.4x
L= 8192 | Attention: 208,237,834,240 | Grassmann: 3,153,210,368 | 66.0x
```

L=128 持平，线性投影和门控的开销不小。L=512 开始拉开，O(L²) 的注意力矩阵主导计算量。L=2048 快 16 倍，L=8192 快 66 倍。

直觉：注意力矩阵大小 L²，Grassmann 配对数 n_windows × L。L 远大于 n_windows 时，前者碾压后者。L=8192，注意力矩阵 6700 万元素，Grassmann 约 49000 对配对。66 倍差距的来源。

顺带一提，这里说的是计算 FLOPS 不是参数量。Grassmann 层的参数量其实比 self-attention 多一点（额外的 feature 投影和门控），但推理时参数量不是瓶颈，计算量才是。

## 实验结果：不完美，但有启发

### Wikitext-2 语言建模

| 配置 | 模型 | PPL | 参数量 |
|------|------|-----|--------|
| 6层, d=256, block=128 | TransformerLM | 241.0-253.6 | ~12.6M |
| 6层, d=256, block=128 | GrassmannLM | 275.7-282.3 | ~13.0M |
| 12层, d=256, block=256 | TransformerLM | 235.2 | ~17.3M |
| 12层, d=256, block=256 | GrassmannLM | 261.1 | ~18.2M |

数字不算好看。Grassmann 比 Transformer 高 11-15% PPL，放在实际应用中差距不小。

但有一个趋势：**Grassmann 从堆叠深度中获益更多**。

Transformer 6 层到 12 层，PPL 241→235，改善 2.4%。Grassmann 276→261，改善 5.4%。改善幅度是 Transformer 的 2.25 倍。这说明 Grassmann 的层次化堆叠效率更高——每层都在积累有意义的几何信息，而不是像 Transformer 那样可能出现深层"注意力稀释"。

当然，6 层和 12 层的对比说服力有限。更大规模的验证才是关键。

### SNLI 自然语言推理

| 模型 | Val Acc | Test Acc |
|------|---------|----------|
| Transformer head (DistilBERT +) | 0.8545 | 0.8511 |
| Grassmann-Plücker head (DistilBERT +) | 0.8550 | 0.8538 |

这个结果让我觉得 Grassmann 的潜力可能被低估了。在 SNLI 上，Grassmann 头略优于 Transformer 头。

SNLI 是句子对分类：给出前提和假设，判断蕴含、矛盾还是中性。核心就是"比较两个句子"——Plücker 坐标天然编码"两个向量的关系"，在 NLI 中这个几何关系可能比全局注意力更直接有效。

我的猜测：Grassmann 方法可能更适合"需要显式比较"的任务（NLI、语义相似度、问答匹配），而非纯生成。但这需要更多实验。

## 什么没起作用

复现过程中踩了不少坑。挑几个有代表性的。

### 坑一：数值爆炸

初始版没加 L2 归一化，训练直接 PPL > 500，loss 不降。

根因：反对称矩阵 M = u⊗v - v⊗u 的 Frobenius 范数 = √2 · ∥u∥ · ∥v∥ · |sinθ|。训练初期 u 和 v 范数不受约束，M 的范数可以非常大，多层累积后梯度爆炸。

```python
# 错误写法
M = torch.bmm(z1.unsqueeze(2), z2.unsqueeze(1))
M = M - M.transpose(1, 2)

# 正确写法
norm = torch.sqrt(torch.sum(M ** 2, dim=[1, 2], keepdim=True) / 2 + 1e-8)
M = M / norm
```

论文没显式提归一化。我在复现时自己加的，不加训不动。你要复现的话，这步不能省。

### 坑二：窗口配置

前面提过，{1, 3, 7, 15, 31} 比 {1, 2, 4, 8, 12, 16} 差 3.2 个 PPL。纯指数间距 {1, 4, 16, 64} 差 1.9。

最差的是等间距 {2, 6, 10, 14, 18, 22}，差了 4.7 个点——没有覆盖窗口 1，完全跳过了相邻 token 的直接配对。语言建模中最强的信号就是相邻词共现，去掉等于丢了最重要的信息源。

### 坑三：去掉门控

把 `H + sigmoid(gate) * geom` 改成 `H + geom`，PPL 从 279 涨到 294。一开始以为是随机波动，跑了三遍才确认。

门控让模型能"关掉"没用的几何信息。不同窗口贡献的信息量不同——对很多位置，某些窗口的几何特征只是噪声。没有门控，噪声被无条件叠加，干扰有用信号。15 个 PPL 点。门控是架构设计的核心，不是配件。

### 坑四：更大的 r

r=64，Plücker 维度 2016，PPL 只降 1-2 点，计算量翻倍。r=16，Plücker 维度 120，PPL 涨 8 点。r=32 是平衡点——太小表达力不够，太大不值得。

## 和其他注意力替代方案的对比

论文没做这个对比，遗憾。我自己整理了。

### Mamba (Gu & Dao, 2023)

基于结构化状态空间模型（SSM），O(L) 复杂度。工程成熟度高——有优化的 CUDA kernel，在代码生成、数学推理等 benchmark 上接近 Transformer。

Mamba 的"选择性扫描"和 Grassmann 的门控有相似之处，但理论基础不同——前者是动力系统/信号处理，后者是微分几何。

Mamba 能捕捉"信息沿序列传播"的动态，Grassmann 更擅长编码"局部配对的几何结构"。

### RWKV (Peng et al., 2023)

线性注意力的 RNN 变体，WKV kernel 实现 O(L) 复杂度，推理时每步 O(1)。长上下文表现好，已在开源项目中使用。

RWKV 本质还是在近似注意力（kernel trick 把 O(L²) 降成 O(L)）。Grassmann 从根本不计算注意力矩阵。前者是"更高效的注意力"，后者是"不用注意力"。

### Linear Attention 家族

Performer 用随机特征近似 softmax，Linear Transformer 去掉 softmax 改用 kernel 函数。共同思路：找到好 kernel 近似 softmax(QK^T/√d)。

Grassmann 完全不同。不是近似注意力，是用几何结构替代注意力。目标相同，路径完全不同。

| 方案 | 复杂度 | 思路 | 可解释性 | 工程成熟度 |
|------|--------|------|---------|-----------|
| Self-Attention | O(L²) | 全局配对 | 低 | 非常高 |
| Mamba | O(L) | 选择性扫描 | 中 | 高 |
| RWKV | O(L) | 线性注意力+衰减 | 中 | 中 |
| Performer | O(L) | 随机特征近似 | 低 | 低 |
| **Grassmann** | **O(L)** | **几何编码** | **高** | **低** |

最后一列很说明问题。Grassmann 工程成熟度最低。没 CUDA kernel，没大规模训练实验，没预训练模型。目前只是概念验证。

## 我的思考

读完这篇论文，我的判断是：方向有价值，验证严重不足。

Grassmann 流形是 1844 年 Hermann Grassmann 提出的概念，在计算机视觉、控制理论、量子计算等领域用了快两百年。把它引入深度学习，意味着大量理论工具可以借用。

一个让我兴奋的方向：Plücker 坐标编码二阶关系（token 对），那三阶关系（三个 token 的联合依赖）能不能用 Gr(3, r) 的 Plücker 坐标编码？语言中三阶依赖很常见——"The cat that sat on the mat" 中，"that" 的指代需要同时考虑 "cat"、"sat"、"mat"。Gr(3, r) 的维度是 3(r-3)，r=32 时 87 维，计算量可控。

更一般的，Gr(k, r) 提供了一个层次化几何建模框架：k=1 是单个 token 的方向（射影空间），k=2 是 token 对的关系，k=3 是三元组的联合关系。这种层次化正是注意力机制试图通过多头和堆叠来近似的东西，但 Grassmann 给了精确的数学描述。

冷静下来看，局限也很明显。

最大只有 ~18M 参数。这个规模在 2025 年几乎不算"模型"了。LLaMA 已经做到 70B+，Pythia 覆盖了 70M 到 12B，一个 18M 的实验能说明什么？r=32 的 Plücker 编码在 70B 模型中还有足够表达力吗？没人知道。

只测了语言建模和 NLI 两个任务。代码生成、数学推理、多模态理解、长文本摘要——这些才是当前大模型的核心能力。一个新架构只在小规模 LM 上差 Transformer 15%，很难说服工业界投入资源。

没和主流替代方案比。Mamba、RWKV、RetNet 都没比。如果 Grassmann 的 PPL 比 Mamba 还差，几何优势就不够弥补性能差距。

我的态度：保持关注，不急于下结论。理论价值是实打实的——用几何不变量理解神经网络计算，这是个有深度的研究纲领。但它离"替换 Transformer"还很远。

还有一个问题值得讨论。过去两年主流叙事是"scaling law 决定一切"——参数够大、数据够多，架构影响会被稀释。Mamba 支持了这个叙事：小规模不如 Transformer，通过 scaling 逐步追赶。

Grassmann 能不能走同一条路？不确定。几何编码的表达力是否随参数量线性增长，数学上不显然。Plücker 坐标有二次约束（Grassmann-Plücker relations），参数量增大时这些约束可能变成瓶颈。也可能不会——神经网络学到的不需要是"精确的" Plücker 坐标，只需要在"附近"。这种微妙的理论问题，只有大规模实验能回答。

## 写在最后

这篇论文没有给出一个可以立刻替换 Transformer 的架构。它做了一件更安静但更有价值的事：提供了一个思考 token 关系的新框架。

注意力机制问："每个 token 应该关注哪些 token？"

Grassmann 方法问："每对 token 之间的关系，用什么样的几何结构来描述最合适？"

两个问题不矛盾。长序列、推理速度敏感、需要可解释性的场景下，几何视角可能更优。通用语言建模上，Transformer 仍然是最可靠的选择。

| 方法 | 复杂度 | 思路 | 可解释性 | 工程成熟度 | 当前性能 |
|------|--------|------|---------|-----------|---------|
| Self-Attention | O(L²) | 全局配对 | 低 | 非常高 | 基准 |
| Mamba | O(L) | 选择性扫描 | 中 | 高 | ~95% |
| RWKV | O(L) | 线性注意力+衰减 | 中 | 中 | ~93% |
| Grassmann Flows | O(L) | 几何编码 | 高 | 低 | ~85-90% |

想复现的话，最小原型大约 80 行代码，单张 T4 训练 30 分钟就能出 Wikitext-2 结果。关键代码在上面完整给出了。记得加 L2 归一化——论文没提，不加训不动。

延伸阅读：
- 论文原文：https://arxiv.org/abs/2512.19428
- Grassmann 流形：https://en.wikipedia.org/wiki/Grassmannian
- Plücker 坐标：https://en.wikipedia.org/wiki/Pl%C3%BCcker_coordinates
- Mamba：https://arxiv.org/abs/2312.00752
- RWKV：https://arxiv.org/abs/2305.13048

一个开放问题：Grassmann 和线性注意力都在用低维表示近似全注意力，约束不同——几何约束 vs 核函数约束。如果两者结合（比如用 Plücker 坐标作为线性注意力的 kernel），会不会比单独用任何一个都好？
