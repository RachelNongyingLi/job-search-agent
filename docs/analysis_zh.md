# 需求、简历画像与 Workflow 分析

## 1. 需求分析

这个项目应定位为一个 **local-first 找工 agent**，核心目标不是替用户“全自动投递”，而是把求职中最耗精力、最容易丢上下文的步骤结构化：

- 输入岗位 JD，输出匹配度、强匹配证据、缺口和是否值得投递。
- 根据 JD 给出简历定制方向，尤其是项目顺序、skills 排序、profile summary 和 bullet 取舍。
- 生成 cover letter、recruiter message、面试准备问题等草稿。
- 用 CSV 追踪投递状态，避免岗位、简历版本、链接和 follow-up 分散在不同地方。
- 默认保护隐私：真实简历、成绩单、学籍证明、手机号和学号不进入 GitHub。

## 2. 简历画像

候选人背景适合主打以下方向：

- **AI / LLM / Agent / Automation**：CALE framework、prompt construction、model inference、result parsing、automated evaluation、reproducible reporting。
- **NLP / Information Extraction**：CasRel、TDEER、TPLinker、UniRel；适合连接到 document AI、knowledge extraction、procurement assistant 等岗位叙事。
- **Machine Learning / Research Evaluation**：DenseNet、VAE imputation、model comparison、simulation design、evaluation metrics。
- **Quantitative Methods**：causal inference、Bayesian modeling、psychometrics、IRT、econometrics，适合强调严谨实验和可解释评估。
- **Business Process Collaboration**：Advantest 版本简历里已经开始靠近 AI assistant、RPA、procurement/global process 语言，适合投 AI automation intern、data/AI analyst intern、business copilot prototype 相关岗位。

主要短板需要诚实处理：

- 工业级 production backend/cloud/deployment 经验可能不足。
- 德语能力未在简历中体现，德国本地岗位若要求 German fluency 需要筛掉或单独标注风险。
- 工作经验以研究/项目为主，应把“可复现 pipeline、文档、跨团队沟通、业务流程理解”讲清楚。

## 3. 推荐 Workflow

1. **Profile 管理**
   - 用 `profiles/nongying_public.json` 维护公开安全版候选人画像。
   - 私密版本可以放在 `data/private/`，由 `.gitignore` 排除。

2. **JD 分析**
   - 保存 JD 到 `examples/` 或本地私有 `data/jobs/`。
   - 运行 `job-agent analyze --job path/to/jd.txt`。

3. **匹配报告**
   - agent 输出 Markdown，包括 fit score、decision、strong evidence、gaps、resume targeting plan、cover letter、recruiter message、interview prep。

4. **简历定制**
   - MVP 不直接改 `.docx`，先给 Markdown 建议，避免自动覆盖真实简历。
   - 后续可加 DOCX generator 或用固定模板生成版本化简历。

5. **投递追踪**
   - `job-agent track add` 写入 CSV。
   - `job-agent track list` 查看 pipeline。

## 4. MVP 边界

第一版包含：

- 本地 profile JSON。
- JD keyword parser。
- rule-based fit scoring。
- Markdown material generator。
- CSV application tracker。
- README、example JD、基础测试。

第一版不做：

- 自动登录 LinkedIn、Workday 或公司官网。
- 自动投递。
- 自动改写真实 `.docx` 简历。
- 云端数据库。
- 强依赖外部 LLM API。

后续扩展：

- 添加 OpenAI/本地模型 provider，用于更自然的 JD parsing 和 cover letter 改写。
- 添加 DOCX resume generator。
- 添加 Streamlit/FastAPI dashboard。
- 添加 STAR story bank 和 interview prep mode。
- 添加 job clipper，把网页 JD 保存成本地文件。
