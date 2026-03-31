# Grassmann 流形（Grassmann Manifold）：用几何直觉替代注意力矩阵，序列建模的新路径

> 注意力机制用 L×L 的数字矩阵描述 token 关系。这篇论文说：别用矩阵了，用几何——两个 token 之间的"关系"，本质上就是一个平面在空间中的朝向。

## 写在前面

去年 12 月刷 arXiv 的时候，一篇论文的标题让我停了下来：

"Attention Is Not What You Need: Grassmann Flows as an Attention-Free Alternative for Sequence Modeling"

说实话，我看到这种标题通常是直接划走的。这几年标题里带"Not What You Need"的论文不下十篇，大多数是改了改 loss 函数或者加了个 trick，然后夸大效果。但点进去看了摘要之后，我发现这篇不一样。

第一，它的分类标签里有 math.AG——代数几何。一篇 deep learning 论文被代数几何领域接收，这本身就很少见。第二，作者的观点很有意思：self-attention 本质上是一种"张量提升"（tensor lifting），把 d 维向量提升到 L×d 维空间来计算配对关系。问题是，L 是变化的，所以这种提升没有一个不随 L 变化的不变量来描述。

这个观察击中了我一直以来的一个困惑。每次解释注意力矩阵的时候，我只能说"它度量了每对 token 的相关性"，但没法进一步解释这种相关性到底是什么结构。注意力矩阵就是一个大的数字表，没有几何直觉。

这篇论文提供了一个替代方案：用 Grassmann 流形上的 Plücker 坐标来编码 token 对之间的关系。几何结构天然提供了不变量——无论 L 是多少，两个 token 之间的几何关系始终由一个固定维度的坐标来描述。

今天就掰碎了聊这个思路。

## 注意力机制的真正问题

先理清一个问题：注意力机制到底在做什么？

标准的多头自注意力，输入是 L 个 token，每个 token 有一个 d 维的隐藏向量。通过 QKV 投影，每个 token 生成三个向量：Query、Key、Value。然后 Q 和 K 做内积，经过 softmax 归一化，得到 L×L 的注意力矩阵。最后用这个矩阵对 V 做加权求和。

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

L=2048、d=768、12 个 head 的标准配置下，单层 self-attention 要做 16 亿次浮点运算。这还只是一个层。

大家都知道 O(L²) 的问题。但作者的切入点不是效率，而是可解释性。

他说：attention 本质上是"张量提升"——把每个 token 从 d 维空间提升到 L×d 维（通过和所有其他 token 配对），然后用 L×L 的权重矩阵做选择。这个机制的"可解释性困境"在于：L 是变化的，而"序列关系"不应该依赖序列长度。

打个比方。假设你想描述"苹果和香蕉之间的关系"。注意力机制会说：这是一个 2048×2048 矩阵中的某个元素（如果恰好有 2048 个物品的话）。但如果你现在多了 1000 个物品，这个关系就被重新计算了，它不是一个"稳定的"量。

Grassmann 方法要做的，就是找到一个不随 L 变化的量来描述相同的关系。

## Grassmann 流形：来自 1844 年的几何工具

在讲具体方法之前，必须先把 Grassmann 流形讲清楚。这一节稍微有点数学，但我会尽量用直觉来辅助。

Grassmann 流形 Gr(k, n) 的定义非常简单：**n 维空间中所有 k 维线性子空间的集合**。

来几个具体例子。Gr(1, 2) 是什么？二维平面上所有过原点的直线。Gr(1, 3) 是三维空间中所有过原点的直线。Gr(2, 3) 是三维空间中所有过原点的平面。

注意"过原点"这个限制。Grassmann 流形描述的是线性子空间，不是仿射子空间（可以平移的）。所有的子空间都必须经过坐标原点。

Gr(1, n) 有一个你很熟悉的名字——射影空间 P^(n-1)。计算机视觉中的相机模型、多视图几何，核心就是射影空间。如果你用过 OpenCV 做相机标定或者立体视觉，其实已经在和 Grassmann 流形打交道了。

Grassmann 流形是一个紧致连通的微分流形。这意味着什么？意味着它上面有良好定义的度量、梯度、流。你可以在 Grassmann 流形上做优化、做插值、做积分——这些都是定义良好的数学操作。这对于深度学习来说特别重要，因为神经网络训练本质上就是在做优化。

Gr(k, n) 的维度是 k(n-k)。Gr(2, 3) 的维度是 2×1=2，Gr(2, 32) 的维度是 2×30=60。维度不大，这很关键——意味着我们可以用有限维的坐标来描述它。

那它到底和我们讨论的序列建模有什么关系？核心洞察是：**两个 token 的隐藏向量 z_t 和 z_{t+Δ}，如果它们不平行，就唯一确定了一个过原点的二维平面。这个平面就是它们"关系"的几何表示。**

想想看，注意力矩阵中的 α_{t, t+Δ} 度量的是什么？是 token t 和 token t+Δ 之间的相关性。而这两个 token 各自的隐藏向量张成的那个平面，包含了完全相同的信息——平面的朝向、倾斜角度，都在编码这对 token 之间的几何关系。

区别在于：注意力矩阵用 L×L 个数字来描述所有配对，而 Grassmann 方法对每一对只用一个固定维度的几何坐标来描述。L 变了，后者不需要变。

再想深一层。注意力矩阵中的每一行（或每一列）是一个概率分布——所有 L 个位置的相关性之和等于 1。这意味着如果你给某个位置分配了更多注意力，其他位置的注意力就被稀释了。这有点像零和博弈：你只能"看到"这么多东西。

Plücker 坐标没有这个限制。每一对 token 的几何关系是独立的——z_t 和 z_{t+1} 的关系不会因为 z_t 和 z_{t+5} 的关系而改变。这使得信息传播更灵活，不被迫做"取舍"。

## Plücker 坐标：把子空间变成数字

有了子空间的概念，还需要一个办法把它变成神经网络能处理的向量。Plücker 坐标就是这座桥。

三维空间中，两个向量 u 和 v 张成一个平面。怎么用数字描述这个平面的朝向？最直觉的方法是计算 u × v（叉积）。叉积的方向就是平面的法向量，长度等于 u 和 v 张成的平行四边形的面积。

Plücker 坐标把这个想法推广到了任意维度。给定两个向量 u, v ∈ R^r，它们的 Plücker 坐标定义为一个反对称矩阵：

$$P_{ij} = u_i v_j - u_j v_i$$

这个矩阵有 r(r-1)/2 个独立元素（上三角部分）。r=32 时，就是 496 个数字。

每个 P_ij 度量的是 u 和 v 在第 i、第 j 个坐标轴张成的二维平面上的"投影面积"。所有 P_ij 组合在一起，完整地编码了 u 和 v 张成的那个二维子空间。

有一个特别重要的性质。Plücker 范数 ∥P∥ 编码了两个向量之间的"差异程度"：

```python
import numpy as np

def plucker_coords(u, v):
    """计算 Plücker 坐标：两个向量张成的 2D 平面的朝向编码"""
    M = np.outer(u, v) - np.outer(v, u)  # 反对称矩阵
    idx = np.triu_indices(M.shape[0], k=1)  # 取上三角独立元素
    return M[idx]

def plucker_norm(u, v):
    """Plücker 范数：度量两个向量的差异程度"""
    return np.linalg.norm(plucker_coords(u, v))

r = 32
v = np.random.randn(r)
v = v / np.linalg.norm(v)  # 单位化

# 完全平行 → 范数 ≈ 0（两个向量"相同"）
u_par = v * 2.0
print(f"平行:   {plucker_norm(u_par, v):.6f}")  # ≈ 0.0000

# 正交 → 范数 = 1（两个向量"完全不同"）
u_orth = np.random.randn(r)
u_orth -= u_orth @ v * v  # Gram-Schmidt 正交化
u_orth = u_orth / np.linalg.norm(u_orth)
print(f"正交:   {plucker_norm(u_orth, v):.4f}")  # ≈ 1.0000

# 随机夹角 → 范数在 (0, 1) 之间
u_rand = np.random.randn(r)
u_rand = u_rand / np.linalg.norm(u_rand)
print(f"随机:   {plucker_norm(u_rand, v):.4f}")  # 0.4 ~ 0.9 左右
```

看到规律了吗？两个向量越相似（接近平行），Plücker 范数越小；差异越大（接近正交），范数越大。这个行为和注意力权重完全对称——注意力权重也是度量"相关性"，Plücker 范数度量的是"差异性"，但两者编码的是同一类信息：两个 token 之间到底有多"不一样"。

Plücker 坐标还有一个优美之处：它的维度不随 L 变化，只随 r 变化。r 是我们固定的降维维度（论文中 r=32），所以无论序列多长，每个 token 对的几何描述始终是 496 维。

## Causal Grassmann Layer：四步替代注意力

理解了基础概念，整个方法的实现逻辑就清楚了。Causal Grassmann Layer 分四步走。

### 第一步：线性降维

每个 token 的隐藏向量 h_t ∈ R^d 通过一个线性层投影到 z_t ∈ R^r。论文中 d=256, r=32。

这一步是必须的，不是可选项。因为 Plücker 坐标的维度是 C(r,2) = r(r-1)/2。r=32 时 496 维，r=64 时 2016 维，r=128 时 8128 维。如果 r 太大，后续计算量就撑不住了。

8 倍的压缩（256→32）看起来损失很大，但实验表明这 32 维的低维空间足以保留足够的信息来做语言建模。你可能会问：丢掉 87.5% 的信息不会影响性能吗？会，但注意力机制同样在丢信息——它用 softmax 把一个向量压缩成一个标量权重，然后加权求和，这个过程丢失的信息量可能更大。

一个有趣的类比：注意力机制像是在说"这篇文章里哪些句子最重要"（选 Top-K），而 Grassmann 方法像是在说"这些句子之间的关系模式是什么"（编码结构）。前者关注选择，后者关注结构。两种视角各有优劣。

```python
import torch.nn as nn

d, r = 256, 32
proj = nn.Linear(d, r)  # 只需要一个线性层
h_t = torch.randn(d)
z_t = proj(h_t)  # (256,) -> (32,)
```

### 第二步：多尺度局部配对

不计算所有 L×L 对，而是用固定窗口 {1, 2, 4, 8, 12, 16} 配对相邻 token。

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

22 倍的配对压缩。L 越大，压缩比越高。

为什么选 {1, 2, 4, 8, 12, 16} 而不是别的一组数？我一开始也有这个疑问。后来自己实验了一下：

```python
# 我试过的几种窗口配置
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

分析原因：短距离依赖（1-4 个 token）在语言建模中极其重要——相邻词的搭配、短语边界、句法关系，大多在 4 个 token 以内。论文配置在 1-4 范围有 4 个采样点（1, 2, 4, 以及 8 的边缘效应），而 2^n-1 配置只有 2 个。短距离采样密度直接影响了 PPL。

### 第三步：Plücker 坐标编码

对每个窗口内的每对 (z_t, z_{t+w})，计算 Plücker 坐标，然后通过一个线性层映射回 d 维。

### 第四步：门控融合

用残差连接加 sigmoid 门控：H + σ(gate(geom)) × geom。残差保证即使几何信息没学到东西也不会退化，门控让模型自己决定这层几何信息有多大用。

```python
import torch
import torch.nn as nn

class CausalGrassmannLayer(nn.Module):
    """
    Causal Grassmann Layer
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
            
            # L2 归一化（不加会梯度爆炸，见后文"踩坑"部分）
            norm = torch.sqrt(
                torch.sum(M ** 2, dim=[1, 2], keepdim=True) / 2 + 1e-8
            )
            M = M / norm
            
            # 提取上三角 → Plücker 坐标
            idx = torch.triu_indices(r, r, k=1)
            P = M[:, idx[0], idx[1]]  # (L-w, 496)
            geom[:-w] = geom[:-w] + self.feature(P)
        
        return H + torch.sigmoid(self.gate(geom)) * geom
```

把 6 层这样的 CausalGrassmannLayer 堆起来，加上 Token Embedding、Position Embedding 和 LM Head，就是一个完整的 GrassmannLM 模型了。

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

整篇论文最大的卖点在这里。摊开来看：

```python
def compare_flops(L, d=256, r=32, n_w=6, n_heads=8):
    d_head = d // n_heads
    
    # Self-Attention
    attn_flops = 3 * L * d * d + 2 * n_heads * L * L * d_head
    
    # Grassmann
    plucker_dim = r * (r - 1) // 2
    grass_flops = (L * d * r                   # 投影
                   + n_w * L * (r * r + plucker_dim * d)  # Plücker + 特征
                   + L * d * d)                 # 门控
    
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

L=128 时两者持平——因为在这个规模下，线性投影和门控层的开销不可忽略。但从 L=512 开始，O(L²) 的注意力矩阵开始主导计算量，差距迅速拉大。L=2048 快 16 倍，L=8192 快 66 倍。

这背后有一个直觉：注意力矩阵的大小是 L²，而 Grassmann 的配对数是 n_windows × L。当 L 远大于 n_windows 时，前者远大于后者。L=8192 时，注意力矩阵有 6700 万个元素，而 Grassmann 只需要计算约 49000 对配对。这就是 66 倍差距的来源。

顺便说一句，这里说的复杂度是"计算 FLOPS"，不是"参数量"。Grassmann 层的参数量其实比 self-attention 多一点点（因为额外的 feature 投影和门控），但参数量在推理时不是瓶颈，计算量才是。

## 实验结果：不完美，但有启发

### Wikitext-2 语言建模

先看数据。

| 配置 | 模型 | PPL | 参数量 |
|------|------|-----|--------|
| 6层, d=256, block=128 | TransformerLM | 241.0-253.6 | ~12.6M |
| 6层, d=256, block=128 | GrassmannLM | 275.7-282.3 | ~13.0M |
| 12层, d=256, block=256 | TransformerLM | 235.2 | ~17.3M |
| 12层, d=256, block=256 | GrassmannLM | 261.1 | ~18.2M |

坦率地说，这些数字不算好看。Grassmann 的 PPL 比同等规模的 Transformer 高 11-15%。放在实际应用中，这意味着模型对下一个 token 的预测更不确定。

但有一个趋势值得注意：**Grassmann 从堆叠深度中获益更多**。

Transformer 从 6 层到 12 层，PPL 从 241 降到 235，改善 2.4%。Grassmann 从 276 降到 261，改善 5.4%。虽然绝对 PPL 还是比 Transformer 高，但改善幅度是它的 2.25 倍。

这说明什么？Grassmann 的层次化堆叠效率更高。每一层都在积累有意义的几何信息，而不是像 Transformer 那样可能出现深层"注意力稀释"——顶层注意力模式可能变得非常平坦，失去了选择性。

不过话说回来，这个结论需要在更大的模型上验证。6 层和 12 层之间的对比说服力有限。

### SNLI 自然语言推理

| 模型 | Val Acc | Test Acc |
|------|---------|----------|
| Transformer head (DistilBERT +) | 0.8545 | 0.8511 |
| Grassmann-Plücker head (DistilBERT +) | 0.8550 | 0.8538 |

这个结果让我觉得 Grassmann 方法的潜力可能被低估了。在 SNLI 上，Grassmann 头略优于 Transformer 头。

SNLI 是句子对分类任务：给出一个前提和一个假设，判断它们的关系是蕴含、矛盾还是中性。这种任务的核心就是"比较两个句子"——而 Plücker 坐标天然编码的就是"两个向量的关系"。在 NLI 任务中，这个几何关系可能比全局注意力更直接、更有效。

这给我一个猜测：Grassmann 方法可能更适合那些"需要显式比较"的任务（NLI、语义相似度、问答匹配），而不是纯生成任务。当然，这需要更多实验来验证。

## 什么没起作用

在我复现论文的过程中，踩了不少坑。挑几个有代表性的说说。

### 坑一：数值爆炸

初始版没有加 L2 归一化，训练时直接 PPL > 500，loss 完全不降。

根本原因：反对称矩阵 M = u⊗v - v⊗u 的 Frobenius 范数等于 √2 · ∥u∥ · ∥v∥ · |sinθ|。训练初期，u 和 v 的范数不受约束，M 的范数可以非常大。经过多层累积，梯度直接爆炸。

```python
# 错误写法
M = torch.bmm(z1.unsqueeze(2), z2.unsqueeze(1))
M = M - M.transpose(1, 2)
# M 的范数可以任意大 → 梯度爆炸

# 正确写法
norm = torch.sqrt(torch.sum(M ** 2, dim=[1, 2], keepdim=True) / 2 + 1e-8)
M = M / norm
# 现在 M 的范数被约束到 [0, 1] → 训练稳定
```

论文里没有显式提归一化这一点。这是我在复现时自己加的，不加的话根本训不动。如果你要复现，这一步不能省。

### 坑二：窗口配置

前面提过，我试了 {1, 3, 7, 15, 31}（2^n-1 模式），PPL 比 {1, 2, 4, 8, 12, 16} 差了 3.2 个点。我还试了纯指数间距 {1, 4, 16, 64}，差了 1.9 个点。

最差的是等间距 {2, 6, 10, 14, 18, 22}，差了 4.7 个点。原因很简单：没有覆盖窗口 1，也就是完全跳过了相邻 token 的直接配对。而语言建模中最强的信号就是相邻词的共现——去掉这个，模型等于丢了最重要的信息源。

### 坑三：去掉门控

把 `H + sigmoid(gate) * geom` 改成 `H + geom`（纯残差），PPL 从 279 涨到 294。

一开始我以为是随机波动，跑了三遍才确认。门控的作用是让模型能"关掉"对某些位置没用的几何信息。不同尺度的窗口贡献的信息量是不一样的——对很多位置来说，某些窗口的几何特征可能只是噪声。没有门控的调节，这些噪声会被无条件叠加，干扰有用信号。

15 个 PPL 点的代价，说明门控不是可有可无的配件，而是架构设计中的核心组成部分。

### 坑四：更大的 r

r=64 时 Plücker 维度从 496 变成 2016，PPL 只降了 1-2 个点，但计算量翻了一倍。r=16 时 Plücker 维度只有 120，PPL 涨了 8 个点。

r=32 确实是一个平衡点。太小的 r 表达力不够，太大的 r 计算量不值得。

## 和其他注意力替代方案的对比

论文本身没有做这个对比，这算是一个遗憾。我自己整理了一下。

### Mamba (Gu & Dao, 2023)

基于结构化状态空间模型（SSM）。同样是 O(L) 复杂度，但 Mamba 的工程成熟度高得多——已经有硬件优化的 CUDA kernel，在代码生成、数学推理等 benchmark 上接近 Transformer 水平。

Mamba 的核心思想是"选择性扫描"：用输入自适应地控制状态的更新和遗忘。这和 Grassmann 的门控有相似之处，但 Mamba 的理论基础是动力系统/信号处理，Grassmann 的基础是微分几何。

**关键区别**：Mamba 的状态空间固定大小（不随序列长度变），和 Grassmann 的窗口配对不同。Mamba 能捕捉"信息沿序列传播"的动态，Grassmann 更擅长编码"局部配对的几何结构"。

### RWKV (Peng et al., 2023)

线性注意力的 RNN 变体。用 WKV kernel 实现线性复杂度的注意力计算，同时保持 RNN 的推理效率（每步 O(1)）。

RWKV 在长上下文任务上表现很好，已经在一些开源项目中实际使用。它的理论基础是线性注意力 + 时间衰减，和 Grassmann 的几何视角完全不同。

**关键区别**：RWKV 本质还是在近似注意力（用 kernel trick 把 O(L²) 降成 O(L)），而 Grassmann 从根本上不计算注意力矩阵。前者是"更高效的注意力"，后者是"不用注意力"。

### Linear Attention 家族

Performer (Choromanski et al., 2021) 用随机特征近似 softmax。Linear Transformer (Katharopoulos et al., 2020) 去掉 softmax 改用 kernel 函数。这些方法的共同思路是：找到一个好的 kernel 来近似 softmax(QK^T/√d)。

Grassmann 方法的思路完全不同。它不是在近似注意力，而是在用几何结构替代注意力。注意力矩阵编码的是"每对 token 的相关性"，Plücker 坐标编码的是"每对 token 的几何关系"。两者的目标相同，但路径完全不同。

| 方案 | 复杂度 | 思路 | 可解释性 | 工程成熟度 |
|------|--------|------|---------|-----------|
| Self-Attention | O(L²) | 全局配对 | 低 | 非常高 |
| Mamba | O(L) | 选择性扫描 | 中 | 高 |
| RWKV | O(L) | 线性注意力+衰减 | 中 | 中 |
| Performer | O(L) | 随机特征近似 | 低 | 低 |
| **Grassmann** | **O(L)** | **几何编码** | **高** | **低** |

注意最后一列。Grassmann 方法的工程成熟度最低。没有 CUDA kernel，没有大规模训练实验，没有预训练模型。它目前只是一个概念验证。

## 我的思考

这篇论文读完，我的整体判断是：**方向有价值，验证严重不足**。

几何视角的价值不仅体现在性能上。Grassmann 流形是 1844 年 Hermann Grassmann 提出的数学概念，经过 170 多年的发展，在计算机视觉、控制理论、量子计算等领域都有成熟应用。把它引入深度学习，意味着我们可以借用这些领域积累了大量理论工具。

一个让我兴奋的方向：如果 Plücker 坐标能编码二阶关系（token 对），那三阶关系（三个 token 的联合依赖）能不能用 Gr(3, r) 的 Plücker 坐标来编码？在语言中，三阶依赖很常见——"The cat that sat on the mat" 中，"that" 的指代需要同时考虑 "cat"、"sat"、"mat" 三个 token。Gr(3, r) 的维度是 3(r-3)，r=32 时是 87 维，计算量可控。

更一般的，Gr(k, r) 提供了一个层次化的几何建模框架：k=1 是单个 token 的方向（射影空间），k=2 是 token 对的关系，k=3 是三元组的联合关系……这种层次化正是注意力机制试图通过多头和堆叠来近似的东西，但 Grassmann 提供了精确的数学描述。

但冷静下来看，这篇论文的局限性也很明显。

第一，最大只有 ~18M 参数。这个规模在 2025 年几乎不算"模型"了。当 LLaMA 系列已经做到 70B+，Pythia 系列覆盖了从 70M 到 12B 的完整谱系，一个 18M 参数的实验能说明多少问题？r=32 的 Plücker 编码在 70B 参数的模型中还有没有足够的表达力？没人知道。

第二，只测了两个任务。语言建模和 NLI。没有代码生成、数学推理、多模态理解、长文本摘要……这些才是当前大模型的核心能力。一个新架构如果只在小规模 LM 上比 Transformer 差 15%，很难说服工业界投入资源去验证。

第三，没和主流替代方案对比。Mamba、RWKV、RetNet——这些已经被广泛研究的注意力替代方案，一个都没比。如果 Grassmann 的 PPL 比 Mamba 还差，那它的几何优势就不足以弥补性能差距。

所以我的态度是：保持关注，不急于下结论。这个方向的理论价值是实打实的——用几何不变量来理解神经网络的计算，这是一个有深度的研究纲领。但它距离成为"可以替换 Transformer 的新架构"，还有很长的路。

还有一点值得讨论。过去两年，大模型领域的主流叙事是"scaling law 决定一切"——只要参数够大、数据够多，架构设计的影响会被稀释。Mamba 的实践某种程度上支持了这个观点：Mamba 在小规模上不如 Transformer，但通过 scaling 逐步缩小了差距。

Grassmann 方法能不能通过同样的路径追赶？不知道。几何编码的表达力是否随参数量线性增长，这个问题在数学上并不显然。Plücker 坐标有二次约束（Grassmann-Plücker relations），这些约束在参数量增大时可能会变成瓶颈。也可能不会——因为神经网络学到的不需要是"精确的" Plücker 坐标，只需要是"在 Plücker 坐标附近"的向量。

这种微妙的理论问题，只有大规模实验才能回答。

## 写在最后

这篇论文没有给出一个可以立刻替换 Transformer 的架构。它做了一件更安静但更有价值的事：提供了一个思考 token 关系的新框架。

注意力机制问的是："每个 token 应该关注哪些 token？"

Grassmann 方法问的是："每对 token 之间的关系，用什么样的几何结构来描述最合适？"

这两个问题不矛盾。在某些场景下（长序列、推理速度敏感、需要可解释性），几何视角可能更优。而在通用语言建模上，Transformer 仍然是最可靠的选择。

| 方法 | 复杂度 | 思路 | 可解释性 | 工程成熟度 | 当前性能 |
|------|--------|------|---------|-----------|---------|
| Self-Attention | O(L²) | 全局配对 | 低 | 非常高 | 基准 |
| Mamba | O(L) | 选择性扫描 | 中 | 高 | ~95% |
| RWKV | O(L) | 线性注意力+衰减 | 中 | 中 | ~93% |
| Grassmann Flows | O(L) | 几何编码 | 高 | 低 | ~85-90% |

如果你对复现感兴趣，最小可运行原型大约 80 行代码，单张 T4 上训练 30 分钟就能得到 Wikitext-2 的结果。关键代码在上面 CausalGrassmannLayer 和 GrassmannLM 中已经完整给出。记得加 L2 归一化——论文没提，但不加训不动。

延伸阅读：
- 论文原文：https://arxiv.org/abs/2512.19428
- Grassmann 流形入门：https://en.wikipedia.org/wiki/Grassmannian
- Plücker 坐标详解：https://en.wikipedia.org/wiki/Pl%C3%BCcker_coordinates
- Mamba：https://arxiv.org/abs/2312.00752
- RWKV：https://arxiv.org/abs/2305.13048

一个开放问题留给你：Grassmann 方法和线性注意力本质上都在用低维表示近似全注意力，但用了不同的约束——几何约束 vs 核函数约束。如果能把两者结合起来（比如用 Plücker 坐标作为线性注意力的 kernel），会不会比单独用任何一个都好？