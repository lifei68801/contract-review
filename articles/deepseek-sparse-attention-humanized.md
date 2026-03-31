# DeepSeek Sparse Attention：长文本推理效率突破

## 长文本推理的现实困境

Transformer 架构的注意力机制是大语言模型的核心，但它有个致命问题：计算复杂度随序列长度平方级增长。当序列长度达到 128K tokens 时，注意力矩阵需要 128K × 128K ≈ 16B 个元素——这不管用什么 GPU 都吃不消。

2025年12月，DeepSeek 团队发布了 DeepSeek-V3.2，其中最关键的技术突破叫 DeepSeek Sparse Attention（DSA）。它把核心注意力的计算复杂度从 O(L²) 降到 O(Lk)，k 远小于 L，而且模型性能基本不掉。

这篇文章会讲清楚 DSA 怎么做到的。

## 传统注意力机制的问题

### 标准 Attention 的计算瓶颈

Transformer 的注意力公式：

$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$$

Q、K、V 是查询、键、值矩阵。序列长度 L 时，注意力矩阵的计算复杂度是 O(L²d)，d 是隐藏层维度。

这不是理论问题，是实实在在的工程瓶颈。128K 的上下文意味着注意力矩阵要存 16B 个元素。即使用 H800，显存和时间开销都会爆炸。

### 现有稀疏注意力方案为什么不够好

学术界早就注意到这个问题了，提出了不少方案：

- **局部注意力**：每个 token 只看邻域，全局依赖建模能力直接废了。
- **滑动窗口注意力**：固定窗口，同样抓不住长距离依赖。
- **稀疏 Transformer**：预定义稀疏模式，灵活性差。

这些方案能降复杂度，但代价是性能下降。DSA 的创新点在于：用可学习的索引机制动态选择最相关的 token，效率要，性能也要。

## DSA 的核心设计

### 整体架构

DSA 原型有两个关键组件：

1. **Lightning Indexer（闪电索引器）**：快速评估 query token 和历史 token 的相关性，输出索引分数。
2. **Fine-grained Token Selection（细粒度 Token 选择）**：根据索引分数选 top-k 个最相关的 key-value 对，只对这些做注意力计算。

### Lightning Indexer：快速算索引分数

Lightning Indexer 要做的事很简单：算 query token $\mathbf{h}_t$ 和历史 token $\mathbf{h}_s$ 的相关性分数 $I_{t,s}$，决定哪些该被选中。

索引分数公式：

$$I_{t,s} = \sum_{j=1}^{H^I} w_{t,j}^I \cdot \text{ReLU}\left(\mathbf{q}_{t,j}^I \cdot \mathbf{k}_s^I\right)$$

参数说明：
- $H^I$ 是索引器的头数（头数少，所以快）
- $\mathbf{q}_{t,j}^I \in \mathbb{R}^{d^I}$ 从 query token $\mathbf{h}_t$ 导出
- $\mathbf{k}_s^I \in \mathbb{R}^{d^I}$ 从历史 token $\mathbf{h}_s$ 导出
- $w_{t,j}^I \in \mathbb{R}$ 是可学习的权重
- ReLU 作激活函数，为了吞吐量

几个设计点：

索引器头数少，能用 FP8 跑，计算效率高。ReLU 替代 softmax，省掉指数运算。点积快速评估相关性，给后续精细筛选打基础。

### Fine-grained Token Selection：精准选 Token

有了索引分数 $\{I_{t,s}\}$，下一步是为每个 query token $\mathbf{h}_t$ 选 top-k 个 key-value 条目 $\{\mathbf{c}_s\}$。

注意力输出：

$$\mathbf{u}_t = \text{Attn}\left(\mathbf{h}_t, \{\mathbf{c}_s | I_{t,s} \in \text{Top-k}(I_{t,:})\}\right)$$

核心思想：**不是所有历史 token 都重要**。选最相关的 k 个，复杂度从 O(L²) 降到 O(Lk)，关键信息不丢。

### 在 MLA 架构下的实现

DeepSeek-V3.2 用 Multi-head Latent Attention（MLA）作为基础注意力架构。为了从 DeepSeek-V3.1-Terminus 平滑迁移，DSA 在 MLA 框架下做了特定实现。

关键设计：内核层面，每个 key-value 条目要被多个 query 共享才高效。所以 DSA 基于 MLA 的 MQA（Multi-Query Attention）模式实现，每个潜在向量被同一 query token 的所有 query head 共享。

好处：
- 兼容现有 MLA 架构，不用大规模重构
- 支持 MQA 高效推理
- 保持 MLA 的推理效率特性

## 两阶段训练：从 Dense 到 Sparse 的平滑过渡

直接训练稀疏注意力模型不稳定。DeepSeek 团队设计了两阶段训练策略。

### Dense Warm-up Stage：初始化 Lightning Indexer

目标：保持 Dense Attention，训练 Lightning Indexer 学会对齐注意力分布。

步骤：

1. 冻结主模型参数，只训练 Lightning Indexer，Dense Attention 不变。

2. 算目标分布：对第 t 个 query token，聚合主注意力分数（跨所有注意力头求和），序列维度 L1 归一化，得 $p_{t,:} \in \mathbb{R}^t$。

3. KL 散度损失：

$$\mathcal{L}^I = \sum_{t} \mathbb{D}_{\text{KL}}\left(p_{t,:} \| \text{Softmax}(I_{t,:})\right)$$

4. 训练配置：
   - 学习率：$10^{-3}$
   - 训练步数：1000 步
   - 每步批次：16 个序列 × 128K tokens
   - 总 token 数：2.1B tokens

意图很明显：warm-up 阶段让索引器学会生成和主注意力分布对齐的分数，给后续稀疏训练打底。

### Sparse Training Stage：全模型适应稀疏模式

目标：引入 Fine-grained Token Selection，优化所有模型参数，让模型适应 DSA 的稀疏模式。

关键改进：索引器的训练目标改为只考虑被选中的 token 集合 $\mathcal{S}_t = \{s | I_{t,s} \in \text{Top-k}(I_{t,:})\}$：

$$\mathcal{L}^I = \sum_{t} \mathbb{D}_{\text{KL}}\left(p_{t,\mathcal{S}_t} \| \text{Softmax}(I_{t,\mathcal{S}_t})\right)$$

技术细节：

1. 分离优化：索引器的输入从计算图分离，单独优化。索引器的训练信号只来自 $\mathcal{L}^I$，主模型优化只根据语言建模损失。

2. 训练配置：
   - 学习率：$7.3 \times 10^{-6}$
   - 每个 query 选的 key-value token 数：2048
   - 训练步数：15000 步
   - 每步批次：480 个序列 × 128K tokens
   - 总 token 数：943.7B tokens

大规模训练下来，模型适应了 DSA 的稀疏模式，学会只关注最相关的 token，语言建模能力保持住。

## 复杂度与推理效率

### 理论复杂度

DSA 把核心注意力复杂度从 $O(L^2)$ 降到 $O(Lk)$，k 远小于 L。

注意：Lightning Indexer 复杂度还是 $O(L^2)$，但头数少、能跑 FP8，实际开销远低于 MLA 的注意力计算。

### 实测推理成本

DeepSeek 团队在 H800 集群上实测：

Prefilling 阶段：
- 短序列：实现了特殊的 masked MHA 模式模拟 DSA，短上下文效率更高。
- 长序列：DSA 显著降成本，成本曲线随 token 位置线性增长，不是平方级。

Decoding 阶段：
- DSA 优势更明显，超长上下文场景下尤其显著。
- 按 GPU 小时算成本（2 USD/GPU 小时），长文本生成任务能省超过 50%。

## 性能评估：效率有了，效果怎么样？

### 标准基准测试

DeepSeek-V3.2-Exp（带 DSA）在 2025 年 9 月评测，和 DeepSeek-V3.1-Terminus（Dense Attention）在多个基准上表现相当。

发现：
- 短上下文任务，没观察到明显性能退化。
- 长上下文任务，DSA 模型同样有竞争力。

### 人类偏好评估

ChatbotArena 的 Elo 分数评估，两个模型用相同后训练策略，得分接近。稀疏注意力没损害人类偏好匹配度。

### 长上下文专项评测

独立评测机构的测试：

- **AA-LCR**：DeepSeek-V3.2-Exp 推理模式比 DeepSeek-V3.1-Terminus 高 4 分。
- **Fiction.liveBench**：多个指标持续超越 Dense Attention 版本。

DSA 不仅没导致性能退化，某些长上下文推理任务上还更好。可能原因：稀疏选择机制起了类似注意力正则化的作用，帮模型聚焦关键信息。

## 设计背后的思考

### 为什么用可学习的索引机制？

传统稀疏注意力方案用预定义稀疏模式（局部窗口、稀疏块等），问题明显：不同任务、不同位置对注意力的需求是动态的。

DSA 的可学习索引机制让模型自己决定关注哪些 token。Lightning Indexer 在推理时动态生成相关性分数，实现"按需关注"。

### ReLU 还是 Softmax：为什么选 ReLU？

标准注意力用 softmax 归一化，要算指数函数，高维空间开销大。

DSA 在索引分数计算用 ReLU：
- ReLU 计算简单，没指数运算。
- 稀疏选择场景下，只关心相对大小，不需要严格概率分布。
- 实验证明 ReLU 在这个任务上效果行。

### 为什么两阶段训练？

直接从随机初始化训练稀疏注意力模型不稳定：

1. 冷启动问题：索引器初期分数随机，选的 token 质量不稳定。
2. 梯度信号冲突：索引器和主模型同时训练，可能陷入局部最优。

两阶段训练先让索引器对齐主注意力分布，再联合优化，缓解了这些问题。

## 实际应用场景

### 长文本生成

文档摘要、长文写作，DSA 能高效处理 128K tokens 上下文，推理成本大幅降低。

### 代码智能体

代码生成、代码审查，经常要处理大型代码库。DSA 让模型高效"浏览"整个代码库，不受限于上下文窗口。

### 搜索智能体

DeepSeek-V3.2 的搜索智能体评测中，DSA 让模型在有限上下文窗口内处理更多搜索结果，提升答案质量。BrowseComp 评测显示，配合上下文管理策略，DeepSeek-V3.2 达到 67.6 的 Pass@1 分数。

### 多轮对话

对话历史不断增长。DSA 的线性复杂度让模型能处理更长对话历史，上下文理解能力提升。

## 未来可能的方向

### 技术演进

DSA 给稀疏注意力提供了新思路，未来可能的方向：

1. 更精细的选择策略：现在用 top-k 选择，未来可以探索基于重要性分数的动态选择。
2. 层级稀疏：结合层级注意力，不同层级用不同稀疏模式。
3. 硬件协同设计：针对 DSA 计算模式设计专用硬件加速器。

### 与其他技术的融合

DSA 可以和这些技术结合：

- KV Cache 压缩：结合 DSA 的选择机制，进一步压缩缓存。
- 推测解码（Speculative Decoding）：推测阶段用更激进的稀疏策略。
- 混合专家（MoE）：DSA 和 MoE 结合，计算效率双重提升。

## 总结

DeepSeek Sparse Attention 通过 Lightning Indexer 和 Fine-grained Token Selection 的组合，实现了从 O(L²) 到 O(Lk) 的复杂度优化。

价值不仅在效率提升，更在于证明：**稀疏注意力不意味着性能妥协**。精心设计和训练，可以构建既高效又强的注意力机制。

对开发者，理解 DSA 原理有助于更好利用 DeepSeek-V3.2 的能力。对研究者，DSA 提供了稀疏注意力设计的新范式，值得深入探索。

大模型技术快速发展的今天，DSA 代表了一个重要方向：**在保持模型能力的前提下，追求更高计算效率**。这不仅是技术优化要求，更是 AI 大规模落地应用的关键前提。

---

**参考文献**：
1. DeepSeek-AI. (2025). DeepSeek-V3.2: Pushing the Frontier of Open Large Language Models. arXiv:2512.02556.
2. Vaswani, A., et al. (2017). Attention is All You Need. NeurIPS.
3. DeepSeek-AI. (2024). DeepSeek-V2: A Strong, Economical, and Efficient Mixture-of-Experts Language Model.

本文基于 DeepSeek-V3.2 论文的技术细节撰写。如有疏漏，欢迎指正。
