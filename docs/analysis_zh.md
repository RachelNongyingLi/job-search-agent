# 需求、痛点与 Workflow 分析

## 1. 核心定位

这个项目不是“帮我海投更多岗位”的 agent，而是一个 **local-first precision applying agent**。

它的目标是：在不泄露隐私、不编造经历的前提下，帮助候选人判断一个岗位是否值得认真投、应该怎么改材料、哪些短板能补、哪些硬门槛必须提前筛掉。

## 2. 为什么现在的 AI 投递还不够

现在公司端和候选人端都在用 AI：

- 公司用 AI 做简历筛选、审批、排序、路由。
- 候选人用 AI 改简历、写 cover letter、批量投递。

但这并没有真正解决找工作的核心问题，因为：

- **海投不等于精投。** AI 可以让投递速度更快，但不能自动判断哪些岗位值得投入高质量定制。
- **AI 对市场硬约束理解不足。** 很多时候影响结果的不只是能力，而是语言、地点、通勤、身份、签证、是否本地、能否 relocation、入职时间等现实条件。
- **AI 不掌握候选人的完整信息。** 简历只是候选人的一部分。很多真实优势、限制、偏好、正在学习的内容，不会自然出现在一次 prompt 里。
- **AI 容易幻觉式改写。** 它会把“了解过”写成“有经验”，把“项目里碰到过”写成“生产环境负责过”，这会造成面试风险。
- **JD 里的要求不等价。** 有些是硬门槛，有些是加分项，有些是 HR 模板噪音，有些是面试前可以补的内容。

所以这个 agent 的核心不是替用户生成更华丽的文本，而是帮用户建立判断系统。

## 3. 第一个模块：市场硬约束判断

找工作中经常有一些比技术能力更硬的过滤条件：

- 是否要求 German 或本地语言。
- 是否要求已有 work authorization。
- 是否必须 onsite 或住得近。
- 是否接受学生、实习生、part-time、remote。
- 公司是否更偏好本地候选人。
- 岗位是否要求马上入职、长期合同、特定国家税务身份。

普通 AI 简历改写常常忽略这些，因为它只看 JD 和简历文本，不知道这些条件在真实招聘里可能比项目经历更重要。

本项目将这些条件单独放进 **Market Hard Filters**。这意味着：

- 技术匹配高但市场硬约束不清楚时，报告不会直接鼓励深度投递。
- 语言、地点、身份、通勤会被标记为投递前必须确认的问题。
- 公开 GitHub profile 不保存身份/签证/住址等敏感信息，只提示本地确认。

这至少让我们从海投向精投递进一步。

## 4. 第二个模块：能力分层，而不是盲目改写

为了降低 agent 幻觉，本项目把能力分成三类：

### Root Strengths

已经有证据支撑、可以写进简历并在面试中展开的能力。例如：

- Python pipeline。
- LLM/agent workflow。
- NLP information extraction。
- Model evaluation。
- Causal inference 或 psychometrics。
- Reproducible analysis 和 documentation。

这些是可以被强化表达的内容。

### Interview-Upskill Items

短时间内可以补上、可以为面试准备的内容。例如：

- 某个 RPA 工具的基础概念。
- 公司所在行业的 domain vocabulary。
- 简单 cloud deployment 或 dashboard demo。
- 某个岗位常见工具的 basic workflow。

这些内容可以进入学习计划，但不应该被写成已经有深度经验。

### Irrelevant Or Low-Signal Items

不相关、太泛、太高级或没有证据的内容。例如：

- JD 模板里很长但不关键的工具列表。
- unsupported senior ownership。
- 没做过的 production leadership。
- 和目标岗位弱相关的技术堆砌。

这些内容不应该为了 ATS 而硬塞进简历。

## 5. 第三个模块：Application Memory

一次投递的价值不只是投出去，还应该反过来完善 memory：

- 哪类岗位反复出现语言门槛。
- 哪类岗位反复要求本地/onsite/visa。
- 哪些技能总是成为可补短板。
- 哪些 root strengths 在某类岗位中最常被匹配。
- 哪些岗位看起来相关但其实是低质量匹配。

后续版本可以把这些信息存到本地 memory 文件中，让 agent 越投越懂用户，而不是每次都从零开始。

## 6. 当前 MVP Workflow

1. 用户把 JD 保存成 `.txt` 或 `.md`。
2. agent 读取匿名或本地私有 profile。
3. agent 输出：
   - fit score
   - market hard filters
   - root strengths
   - interview-upskill items
   - low-signal/unsupported items
   - resume targeting plan
   - cover letter / recruiter message draft
   - memory updates
4. 用户决定是否值得深度定制。
5. 用户用 CSV 记录投递状态。
6. 如果需要长期学习，运行 `job-agent analyze --memory memory.local.json`，把 root strengths、interview-upskill items 和 market risks 写入本地私有 memory。

## 7. 隐私原则

公开仓库只保留匿名 sample profile。

不要提交：

- 真实姓名和联系方式。
- 出生日期、学号、证件、成绩单、学籍证明。
- 真实简历 `.docx/.pdf`。
- 签证/身份信息。
- 住址、通勤、可 relocation 等私密市场信息。
- 真实投递记录和公司沟通。

这些内容应该只存在于 `.gitignore` 覆盖的本地私有文件中。

## 8. 后续扩展

- 本地 private memory store。
- 更强的 market filter parser。
- 基于 root/upskill/irrelevant 的 resume version planner。
- 面试准备模式，把 upskill items 转成 3 天或 7 天学习计划。
- 可选 LLM provider，但必须带 anti-hallucination guard。
- 本地 dashboard 展示投递 pipeline 和市场反馈。
