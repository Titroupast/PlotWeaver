# 🖋️ PlotWeaver: The Light Novel Alchemist

> **"Where logic weaves the threads, and imagination colors the world."** ♪

**PlotWeaver** 是一款专为轻小说续写设计的智能化 Agent 框架。它不只是简单的文本生成器，而是一位拥有“长期记忆”与“严谨逻辑”的数字副作家。通过结构化的规划与多维度的审校，PlotWeaver 能够有效解决 AI 续写中常见的“设定吃书”、“人设崩坏”以及“剧情水字数”等痛点。

---

## ✨ 核心特性 (Core Features)

* **Structured Plotting**: 拒绝盲目续写。在生成正文前，Agent 会先输出章节规划（JSON Schema），确保逻辑自洽。
* **RAG-Powered Memory**: 建立专属的“世界观知识库”，自动检索角色设定与前文伏笔。
* **Multi-Agent Workflow**: 模拟真实的创作流程——“大纲编剧 -> 正文撰写 -> 严格审校”。
* **Skill-Based Evolution**: 模块化的 Skill 架构，可针对不同文风（如：恋爱喜剧、异世界战斗）进行微调。

---

## 📅 7天进化之路 (7-Day Roadmap)

| 进度      | 阶段目标               | 核心重点                              |
| :-------- | :--------------------- | :------------------------------------ |
| **Day 1** | 🧬 **最小原型跑通**     | 实现基础 API 调用与流式输出           |
| **Day 2** | 📐 **结构化规划**       | 引入 Structured Outputs，先大纲后正文 |
| **Day 3** | 📚 **设定记忆注入**     | 使用 File Search / RAG 检索世界观设定 |
| **Day 4** | 🛠️ **工具调用 (Tools)** | 让模型学会查设定、存草稿、搜伏笔      |
| **Day 5** | ⚖️ **审稿 Agent**       | 自动化检查人设一致性与文风匹配度      |
| **Day 6** | 🧩 **Skill 沉淀**       | 将常用工序封装为可复用的任务技能      |
| **Day 7** | 📊 **评测基线建立**     | 建立测试样本集，量化续写质量          |

---

## 🚀 快速开始 (Quick Start)

### 1. 环境准备
```bash
# 克隆项目
git clone [https://github.com/Titroupast/PlotWeaver.git](https://github.com/Titroupast/PlotWeaver.git)
cd PlotWeaver

# 创建虚拟环境并安装依赖
conda create -n PlotWeaver python=3.9
conda -r requirements.txt
```

## 2. 配置 API Key

在根目录创建 `.env` 文件（已加入 .gitignore，请放心存放♪）：

```
ARK_API_KEY=your_ark_api_key_here
ARK_MODEL=your_model_id_here
```

## 3. 开启创作

```bash
python main.py
```

------

## 🎨 文风预览 (Style Showcase)

> *“少年握紧了手中的断剑，眼前的巨龙发出低沉的咆哮。那是来自远古的威压，但他的血液中，某种更古老的东西正在苏醒……”* —— **PlotWeaver 续写示例**

------

## 🕊️ 关于作者

本项目由 **Titroupast** 发起，致力于探索生成式 AI 与叙事艺术的完美融合。如果你也对 AI 创作感兴趣，欢迎提交 Issue 或 Pull Request，让我们一起编织更精彩的故事吧！♪

