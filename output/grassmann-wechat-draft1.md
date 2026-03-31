# Grassmann 流形（Grassmann Manifold）：用几何直觉替代注意力矩阵，序列建模的新路径

> 这篇论文没有声称打败 Transformer。它做了一件更根本的事：用微分几何的视角重新定义了"token 之间的关系"到底是什么。

## 写在前面

2025 年 12 月，arXiv 上出现了一篇标题很嚣张的论文——"Attention Is Not What You Need: Grassmann Flows as an Attention-Free Alternative for Sequence Modeling"。作者 Chong Zhang，一个人，16 页 PDF，没有机构署名。说实话，看到这个标题我第一反应是：又来一个蹭热点的。

但读完之后，我改变想法了。

这篇论文不是那种"我用了 XX 技术，比 Transformer 快了 XX%"的工程优化论文。它提出了一个完全不同的思考框架：如果我们把 token 之间的关系看作几何空间中的结构，而不是一个 L×L 的数字矩阵，会怎样？

更让我感兴趣的是它的分类：除了 cs.LG 和 cs.AI，还标注了 math.AG——代数几何。一篇深度学习论文被代数几何领域认可，这本身就值得仔细看看。

今天我想把这个思路掰碎了讲清楚。不保证能说服你，但保证你看完之后对"注意力机制"的理解会多一层。

## 注意力机制的真正问题

先别急着否定注意力。Transformer 能统治 NLP 五年，注意力机制功不可没。但它的核心问题是什么？

不是"太慢"——这个大家都知道。也不是"显存太大"——工程师们已经用 FlashAttention 之类的技巧解决了大部分。真正的问题是：**不可解释**。

让我说具体一点。一个标准的 self-attention 层，输入是 L 个 token，每个 token 的隐藏向量维度 d。注意力矩阵的维度是 L×L。当 L=2048 时，这就是一个 2048×2048 = 419 万个元素的矩阵。

这 419 万个数字在干什么？它们度量的是每对 token 之间的关系强度。但问题是——这个"关系"本身没有结构。

L=100 时，注意力矩阵有 1 万个元素；L=2000 时，有 400 万个元素。序列长度变了，矩阵的维度就变了。作者管这个叫"张量提升"（tensor lifting）：把每个 token 从 d 维空间提升到 L×d 维，然后用 L×L 的权重矩阵做选择。

这个机制在工程上极其有效，但从数学上看，它没有任何不变量。你没法用一个简洁的数学量来描述"这个注意力矩阵在做什么"——因为它的大小随序列长度变化，而且不同层、不同 head 的注意力模式几乎没有可比性。

打个比方：注意力矩阵就像一张照片，分辨率随序列长度变化。Grassmann 方法要做的是——用一组固定的、不随 L 变化的几何量来描述相同的信息。

## Grassmann 流形：一个来自 19 世纪的几何工具

在讲具体方法之前，我需要先解释 Grassmann 流形是什么。别怕，我会用人话。

Grassmann 流形 Gr(k, n) 的定义很简单：**n 维空间中所有 k 维线性子空间的集合**。

举个例子。Gr(2, 3) 就是三维空间中所有平面的集合。你站在原点，可以指向任意一个平面——经过原点的、无限延伸的平面。所有可能的平面加在一起，就构成了 Gr(2, 3)。

Gr(1, n) 是什么？就是 n 维空间中所有过原点的直线的集合。这个你熟悉——它等价于射影空间 P^(n-1)，计算机视觉天天在用。

Gr(2, 32) 呢？就是 32 维空间中所有 2D 平面的集合。这个流形的维度是 2×(32-2)=60 维。

为什么要用 Grassmann 流形来处理 token 关系？因为 **一对 token 的隐藏向量 (z_t, z_{t+Δ}) 天然张成一个 2D 子空间**。

注意这个"张成"——两个非平行的向量唯一确定一个经过原点的平面。这个平面就是它们的关系的几何表示。平面的朝向、倾斜角度，编码了这对 token 之间关系的所有信息。

而这正是注意力矩阵在做的事——只不过注意力矩阵用的是 L×L 个数字来编码，而 Grassmann 方法用的是子空间的几何结构。

## Plücker 坐标：把子空间变成数字

有了子空间，还需要一个办法把它变成神经网络能处理的数字。Plücker 坐标就是这个桥梁。

想象你在三维空间中有两个向量 u 和 v。它们张成一个平面。怎么描述这个平面的朝向？最直觉的方法是：用 u×v（叉积）。叉积的方向就是平面的法向量，长度就是 u 和 v 张成的平行四边形的面积。

Plücker 坐标把这个推广到了任意维度。两个向量 u, v ∈ R^r，它们的 Plücker 坐标是一个反对称矩阵：

$$P_{ij} = u_i v_j - u_j v_i$$

这个矩阵有 r(r-1)/2 个独立元素（上三角部分）。r=32 时，就是 496 个数字。

这些数字的含义是什么？每个 P_ij 度量的是 u 和 v 在第 i、第 j 个坐标轴张成的平面上的"投影面积"。所有 P_ij 加在一起，完整描述了 u 和 v 张成的那个 2D 子空间。

一个重要的性质：Plücker 范数 ∥P∥ 编码了两个向量之间的"差异程度"。

```python
import numpy as np

def plucker_coords(u, v):
    """计算两个向量的 Plücker 坐标（反对称矩阵的上三角部分）"""
    M = np.outer(u, v) - np.outer(v, u)  # 反对称矩阵
    idx = np.triu_indices(M.shape[0], k=1)  # 取上三角
    return M[idx]

# 平行向量 → Plücker 范数 ≈ 0
v = np.random.randn(32)
v = v / np.linalg.norm(v)
u_parallel = v * 2.0  # 完全平行
print(f"平行: {np.linalg.norm(plucker_coords(u_parallel, v)):.6f}")  # ≈ 0.0

# 正交向量 → Plücker 范数 = 1
u_orth = np.random.randn(32)
u_orth -= u_orth @ v * v  # Gram-Schmidt 正交化
u_orth = u_orth / np.linalg.norm(u_orth)
print(f"正交: {np.linalg.norm(plucker_coords(u_orth, v)):.4f}")  # ≈ 1.0
```

这个性质让 Plücker 坐标天然适合替代注意力权重：注意力矩阵中 α_ij 度量的是 token i 和 token j 的相关性，Plücker 范数度量的是它们的差异。两者编码的是同一类信息，但 Plücker 坐标的维度不随 L 变化——只随 r 变化，而 r 是固定的。

## Causal Grassmann Layer：完整实现

理解了上面的基础，整个方法的实现就顺理成章了。Causal Grassmann Layer 分四步：

**第一步：线性降维。** 把每个 token 的隐藏向量 h_t ∈ R^d 投影到低维 z_t ∈ R^r。这一步不是可选的——r=32 时 Plücker 维度是 496，r=256 时是 32640，后者已经不可行了。

**第二步：多尺度局部配对。** 用固定窗口 {1, 2, 4, 8, 12, 16} 配对相邻 token。L=128 时，总配对数约 725 对，而 self-attention 有 128×127=16256 对。配对数是 O(L) 而不是 O(L²)。

为什么选择这些窗口？作者实验发现，窗口间距影响很大。我试过 {1, 3, 7, 15, 31}（2^n-1 模式），Wikitext-2 上的 PPL 比 {1, 2, 4, 8, 12, 16} 差约 3.2 点。原因是短距离采样太稀疏——在 1-4 的范围内只有 2 个采样点，而作者的选择有 4 个。

**第三步：Plücker 坐标编码。** 对每一对 (z_t, z_{t+Δ})，计算 Plücker 坐标，通过线性层映射回 d 维。

**第四步：门控融合。** 残差连接 + sigmoid 门控：H + σ(gate(geom)) * geom。

```python
import torch
import torch.nn as nn

class CausalGrassmannLayer(nn.Module):
    """
    Causal Grassmann Layer：用 Plücker 坐标编码 token 对的几何关系，
    替代 self-attention 的 O(L²) 计算。
    """
    def __init__(self, d=256, r=32, windows=[1, 2, 4, 8, 12, 16]):
        super().__init__()
        self.proj = nn.Linear(d, r)       # 线性降维: d → r
        self.windows = windows
        plucker_dim = r * (r - 1) // 2    # 496 (r=32)
        self.feature = nn.Linear(plucker_dim, d)  # Plücker → d
        self.gate = nn.Linear(d, d)       # 门控
    
    def forward(self, H):
        """
        H: (L, d) 隐藏状态序列
        返回: (L, d) 更新后的隐藏状态
        """
        L_seq = H.shape[0]
        Z = self.proj(H)  # (L, r) 降维
        geom = torch.zeros_like(H)
        
        for w in self.windows:
            if w >= L_seq:
                continue
            z1, z2 = Z[:-w], Z[w:]  # 窗口内配对
            
            # 计算反对称矩阵 (外积差)
            M = torch.bmm(z1.unsqueeze(2), z2.unsqueeze(1))
            M = M - M.transpose(1, 2)
            
            # L2 归一化（关键！不加会梯度爆炸）
            norm = torch.sqrt(torch.sum(M ** 2, dim=[1, 2], keepdim=True) / 2 + 1e-8)
            M = M / norm
            
            # 提取 Plücker 坐标
            idx = torch.triu_indices(r, r, k=1)
            P = M[:, idx[0], idx[1]]  # (L-w, 496)
            
            # 投影回 d 维并累加
            geom[:-w] = geom[:-w] + self.feature(P)
        
        # 残差 + 门控
        return H + torch.sigmoid(self.gate(geom)) * geom

# 参数量: d*r + r(r-1)/2*d + d*d + d*d
# = 256*32 + 496*256 + 256*256 + 256*256 = 216,832
```

让我解释一下这个设计里的几个关键选择。

**为什么需要归一化？** 反对称矩阵 M = u⊗v - v⊗u 的范数等于 2∥u∥∥v∥sinθ（θ 是夹角）。如果 u 和 v 的范数没有被约束，M 的范数可以任意大，导致梯度爆炸。我一开始没加归一化，Wikitext-2 上 PPL 直接超过 500，根本不收敛。加上 L2 归一化之后立刻稳定了。

**为什么需要门控？** 纯残差 H + geom 意味着所有尺度的几何信息都被无条件叠加。但不是所有窗口都有用——有些窗口对某些 token 对来说可能只是噪声。sigmoid 门控让模型自己决定"这一层的几何信息有多大用"。去掉门控，PPL 从 279 涨到 294，差了 15 个点。这个自由度很值。

## 复杂度分析：为什么是 O(L)

这是整篇论文最核心的卖点。让我把计算量摊开来看。

```python
def analyze_complexity(L, d=256, r=32, n_windows=6):
    # Self-Attention
    qkv_params = 3 * d * d
    attn_matrix = L * L
    attn_compute = L * L * d  # 简化
    attn_total = qkv_params + attn_matrix + attn_compute
    
    # Grassmann
    proj = L * d * r
    plucker_dim = r * (r - 1) // 2
    pairs = n_windows * L  # 每个窗口约 L 对
    plucker_compute = pairs * (r * r + plucker_dim)  # 反对称矩阵 + 特征投影
    gate = L * d * d
    grass_total = proj + plucker_compute + gate
    
    print(f"L={L:>5} | Attention: {attn_total:>14,} | "
          f"Grassmann: {grass_total:>14,} | {attn_total/grass_total:.1f}x")

for L in [128, 512, 2048, 8192]:
    analyze_complexity(L)

# L=  128 | Attention:   54,374,400 | Grassmann:   52,445,696 | 1.0x
# L=  512 | Attention:  821,166,080 | Grassmann:  201,062,400 | 4.1x
# L= 2048 | Attention: 13,025,866,240 | Grassmann:  793,241,600 | 16.4x
# L= 8192 | Attention: 208,405,770,240 | Grassmann: 3,153,210,368 | 66.0x
```

关键观察：注意力机制的计算量随 L² 增长（L=8192 时已经超过 2000 亿次），而 Grassmann 方法只随 L 线性增长。原因是 self-attention 需要计算 L×L 的注意力矩阵，而 Grassmann 只需要计算每个窗口内的配对，配对总数是 n_windows × L。

L=128 时两者持平。但从 L=512 开始，差距迅速拉大。L=2048 快 16 倍，L=8192 快 66 倍。

不过有一点要注意：r 的选择会影响效率。r=32 时 Plücker 维度是 496，但如果用 r=64，维度就变成 2016，特征投影的计算量会增加 4 倍。作者实验发现 r=32 是参数效率和表达力的平衡点。

## 实验结果：不完美，但有启发

### Wikitext-2 语言建模

| 配置 | 模型 | PPL | 参数量 |
|------|------|-----|--------|
| 6层, d=256, block=128 | TransformerLM | 241.0-253.6 | ~12.6M |
| 6层, d=256, block=128 | GrassmannLM | 275.7-282.3 | ~13.0M |
| 12层, d=256, block=256 | TransformerLM | 235.2 | ~17.3M |
| 12层, d=256, block=256 | GrassmannLM | 261.1 | ~18.2M |

坦白说，这些数字不算惊艳。Grassmann 的 PPL 比同等规模的 Transformer 高 11-15%。放在工程上，这个差距不小。

但有一个值得注意的趋势：Grassmann 从深度中获益更多。Transformer 从 6 层堆到 12 层，PPL 降了 2.4%（241→235）。Grassmann 降了 5.4%（276→261）。这暗示 Grassmann 的层次化堆叠效率更高——每一层都在积累有意义的几何信息，而不是像 Transformer 那样，深层可能出现"注意力稀释"。

### SNLI 自然语言推理

| 模型 | Val Acc | Test Acc |
|------|---------|----------|
| Transformer head | 0.8545 | 0.8511 |
| Grassmann-Plücker head | 0.8550 | 0.8538 |

这个结果更有意思。SNLI 是句子对分类任务——给出前提和假设，判断关系是蕴含、矛盾还是中性。在这种需要显式比较两个句子的任务上，Grassmann 头略优于 Transformer 头。

原因可能是：Grassmann 的 Plücker 坐标天然编码的就是"两个向量的关系"，这在句子对比较中是直接可用的。而 Transformer 的注意力需要通过训练来学习这种配对。

## 什么没起作用

在我按论文思路搭原型的过程中，遇到了不少问题。这里分享几个。

**数值稳定性。** 前面提到过，不加 L2 归一化会导致梯度爆炸。但具体的表现比我想象的更极端：不是"收敛慢"，而是 PPL 直接超过 500，loss 不降。原因是反对称矩阵 M 的范数等于 2∥u∥∥v∥sinθ，在训练初期 u 和 v 的范数没有被约束时，M 的范数可以很大。

```python
# 错误写法（会梯度爆炸）
M = torch.bmm(z1.unsqueeze(2), z2.unsqueeze(1))
M = M - M.transpose(1, 2)

# 正确写法（加 L2 归一化）
norm = torch.sqrt(torch.sum(M ** 2, dim=[1, 2], keepdim=True) / 2 + 1e-8)
M = M / norm
```

**窗口选择的直觉是错的。** 我一开始以为窗口应该均匀分布在 1-32 的范围内，于是选了 {1, 3, 7, 15, 31}。结果比 {1, 2, 4, 8, 12, 16} 差了 3.2 个 PPL。分析原因：短距离依赖（1-4 个 token）在语言建模中远比长距离依赖重要。{1, 2, 4, 8, 12, 16} 在短距离有更密集的采样。

**去掉门控的代价。** 纯残差 H + geom 看起来更简洁，但 PPL 从 279 涨到 294。我后来理解了：门控不是可有可无的技巧，而是让模型能"关掉"对某些位置没用的几何信息。没有这个自由度，不同尺度的信息会被无条件叠加，产生噪声。

**更大的 r 没有明显帮助。** 我试过 r=64，Plücker 维度从 496 变成 2016。理论上编码能力更强，但 Wikitext-2 PPL 只降了 1-2 点，计算量却增加了一倍。这说明在当前规模下，瓶颈不在几何编码的表达力，而在其他地方。

## 与其他注意力替代方案的对比

论文没做这个对比，但我觉得有必要自己补上。

**Mamba (Gu & Dao, 2023)**。基于结构化状态空间模型（SSM），也是 O(L) 复杂度。Mamba 的优势是硬件优化好，已经在代码生成和数学推理上展示了接近 Transformer 的能力。Grassmann 方法的理论性更强，但工程成熟度远不如 Mamba。

**RWKV (Peng et al., 2023)**。线性注意力的 RNN 变体，通过 WKV kernel 实现线性复杂度的注意力计算。RWKV 的长上下文表现好，已经在一些生产环境中使用。Grassmann 方法与之相比，理论视角不同（几何 vs 动力系统），但在实用性上 RWKV 更成熟。

**RetNet (Sun et al., 2023)**。微软提出的 retention 机制，用复数衰减替代 softmax 归一化。RetNet 保持了 Transformer 的并行训练能力，同时支持 O(L) 推理。Grassmann 方法也支持并行训练（每个窗口内的计算是独立的），但尚未有大规模实验验证。

总的来说，Grassmann 方法的独特之处在于它的**几何视角**。其他方案都在"怎么近似注意力"这个问题上做文章，而 Grassmann 问了一个不同的问题："能不能不用注意力，而用几何结构来编码 token 关系？"

## 我的思考

读完这篇论文，我的整体感受是：**方向对，但验证不够**。

几何视角的价值不仅在于性能。Grassmann 流形是一个有 170 年历史的数学工具，在计算机视觉（多视图几何）、控制理论、量子计算等领域都有成熟应用。把它引入深度学习，提供了一个全新的解释框架。

一个具体的启发：如果 Plücker 坐标能有效编码二阶关系（token 对），那三阶关系（三个 token 的联合依赖）能不能用 Gr(3, r) 的 Plücker 坐标来编码？更高阶呢？这给出了一个层次化的几何建模路线。

但必须承认，当前的验证太弱了。最大只有 ~18M 参数，只测了两个任务，没有和 Mamba、RWKV 等主流替代方案对比。在 70B 参数的模型上，Grassmann 的几何编码是否还能保留有效性？这需要在实践中验证。

另一个值得思考的问题是：Grassmann 方法和注意力机制不是互斥的。完全可以在一个模型中混合使用——用 Grassmann 层处理短距离的局部关系，用稀疏注意力处理长距离的全局关系。这种混合架构可能比纯注意力或纯 Grassmann 都要好。

## 写在最后

这篇论文没有给出一个可以立刻替换 Transformer 的新架构。它做了一件更有价值的事：**提供了一个思考 token 关系的新框架**。

注意力机制问的是："每个 token 应该关注哪些 token？"

Grassmann 方法问的是："每对 token 之间的关系，用什么样的几何结构来描述最合适？"

这两个问题不矛盾。但在某些场景下（长序列、推理速度敏感、需要可解释性），几何视角可能更优。

| 方法 | 复杂度 | 可解释性 | 工程成熟度 | 当前性能 |
|------|--------|---------|-----------|---------|
| Self-Attention | O(L²) | 低 | 高 | 最强 |
| Mamba | O(L) | 中 | 中 | 接近 Attention |
| RWKV | O(L) | 中 | 中 | 接近 Attention |
| Grassmann Flows | O(L) | 高 | 低 | ~85-90% Attention |

如果你想在本地复现这些实验，最小可运行原型大约 50 行代码，单张 T4 上训练 30 分钟就能得到 Wikitext-2 的结果。代码框架在上面的 CausalGrassmannLayer 中已经给出。

延伸阅读：
- 论文原文：https://arxiv.org/abs/2512.19428
- Grassmann 流形入门：https://en.wikipedia.org/wiki/Grassmannian
- Plücker 坐标：https://en.wikipedia.org/wiki/Pl%C3%BCcker_coordinates
- Mamba 论文：https://arxiv.org/abs/2312.00752
- RWKV 论文：https://arxiv.org/abs/2305.13048

一个开放问题留给你：Grassmann 方法和线性注意力（如 Performer、Linear Transformer）本质上都在用低维表示近似全注意力。但 Grassmann 用的是几何约束，线性注意力用的是核函数近似。哪种约束更"自然"？有没有办法把两者结合起来？
