# Grassmann Flows 论文调研清单

## 论文基本信息
- 标题: "Attention Is Not What You Need: Grassmann Flows as an Attention-Free Alternative for Sequence Modeling"
- arXiv: 2512.19428, 2024年12月22日提交
- 作者: Chong Zhang
- 分类: cs.LG, cs.AI, math.AG（代数几何）

## 核心论点
1. Self-attention 本质是"张量提升"(tensor lifting)：hidden vectors → L×d 高维空间 → L×L 权重矩阵选择
2. 这种机制表达能力极强，但数学上不透明——多层之后无法用简洁的不变量描述
3. 提出基于 Grassmann 流形的无注意力架构

## Causal Grassmann Layer 四步
1. **线性降维**: h_t ∈ R^d → z_t ∈ R^r (d=256, r=32)
2. **多尺度局部配对**: 窗口 {1, 2, 4, 8, 12, 16}，配对相邻 token
3. **Plücker 坐标编码**: 每对 (z_t, z_{t+Δ}) 视为 R^r 中的 2D 子空间
   - Gr(k,r): R^r 中所有 k 维子空间的集合
   - k=2, r=32: Gr(2,32) 维度 2×(32-2)=60
   - Plücker 嵌入: C(32,2)=496 维射影坐标
   - Plücker 范数编码"关系强度"：平行≈0, 正交=1
4. **门控融合**: H + sigmoid(gate) * geom，残差 + 门控

## 复杂度对比
| L | Attention FLOPS | Grassmann FLOPS | 倍数 |
|---|----------------|----------------|------|
| 128 | 53M | 52M | 1.0x |
| 512 | 818M | 201M | 4.1x |
| 2048 | 13B | 793M | 16.4x |
| 8192 | 208B | 3.2B | 66.0x |

## 实验数据

### Wikitext-2 语言建模
- 6层, d=256: Transformer PPL 241-253, Grassmann PPL 275-282 (~14%差距)
- 12层, d=256: Transformer PPL 235, Grassmann PPL 261 (~11%差距)
- Grassmann 从深度获益更多（5.4% vs 2.4%）

### SNLI 自然语言推理
- Grassmann-Plücker head: Val 0.8550, Test 0.8538
- Transformer head: Val 0.8545, Test 0.8511
- Grassmann 略优

## 踩坑经验
1. 数值不稳定：反对称矩阵需 L2 归一化，否则梯度爆炸，PPL > 500
2. 窗口选择：{1,3,7,15,31} 比 {1,2,4,8,12,16} 差 ~3.2 PPL（短距离采样稀疏）
3. 去掉门控：PPL 从 279 涨到 294（差 15 点）

## 局限性
1. 最大仅 ~18M 参数，无 GPT-scale 验证
2. 仅测试 LM + NLI，无代码/数学/多模态
3. 未与 RWKV、Mamba、RetNet 等竞品对比
4. 仅探索 k=2（二阶关系），未探索 k>2
5. 8倍信息压缩 (d=256 → r=32)

## 竞品对比资料（需补充）
- **Mamba**: SSM-based, O(L), 硬件优化好，在多项 benchmark 接近 Transformer
- **RWKV**: Linear attention variant, RNN-style, 长 context 表现好
- **RetNet**: Linear attention + retention mechanism
- **Linear Attention**: Performer, Linear Transformer 等

## Grassmann 流形背景知识
- Gr(k,n): R^n 中所有 k 维线性子空间的集合
- 维度: k(n-k)
- 是一个紧致连通流形
- Plücker 坐标: 自然嵌入到射影空间 P(C(n,k)-1)
- k=2 时，Plücker 坐标 = 反对称矩阵的上三角部分
- Plücker 关系: 坐标需要满足二次约束（Grassmann-Plücker relations）
