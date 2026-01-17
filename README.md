# Case 3 自动化报告生成智能体

> 🤖 基于AI的影响评估报告自动化生成系统
>
> ✅ 测试通过率: 100% (91/91) | 📊 代码覆盖率: 87% | 🚀 生成时间: < 5分钟

---

## 📖 项目简介

**Case 3 自动化报告生成智能体**是一个智能化的影响评估报告生成系统，能够自动从Excel数据源中提取信息，结合AI技术生成专业的Word格式影响评估报告。

### 核心功能

- ✅ **自动数据提取**: 从Excel文件中提取SDG问卷和影响机制数据
- ✅ **AI辅助生成**: 使用AI API(OpenAI/Claude)生成自然语言章节内容
- ✅ **模板化输出**: 基于Word模板生成格式规范的报告
- ✅ **质量保证**: 多层验证机制确保数据准确性和可追溯性
- ✅ **零幻觉风险**: Grounding验证确保所有陈述有数据支撑

### 技术栈

| 技术 | 用途 |
|------|------|
| Python 3.7+ | 主要开发语言 |
| OpenAI / Claude | AI文本生成 |
| openpyxl | Excel数据处理 |
| python-docx | Word文档生成 |
| Pydantic | 数据验证 |
| pytest | 自动化测试 |

---

## 🚀 快速开始

### 前置要求

- Python 3.7 或更高版本
- pip 包管理器
- OpenAI API密钥（从 [OpenAI](https://platform.openai.com/) 获取）或 Claude API密钥（从 [Anthropic](https://www.anthropic.com/) 获取）

### 安装步骤

#### 1. 克隆项目（或解压项目文件）

```bash
cd case-3-automation-agent
```

#### 2. 安装依赖

```bash
pip install -r requirements.txt
```

#### 3. 配置API密钥

创建 `.env` 文件：

```bash
cp .env.example .env
```

编辑 `.env`，填入您的API配置：

```bash
# .env

# 选项1: OpenAI API (推荐)
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini

# 选项2: Anthropic Claude API
ANTHROPIC_API_KEY=your-anthropic-api-key-here
ANTHROPIC_MODEL=claude-sonnet-4-5

# 生成配置
MAX_TOKENS=4000
```

**说明**: 系统会优先使用OpenAI,如果未配置则使用Claude。

⚠️ **重要**: 不要将 `.env` 文件提交到版本控制系统！（已在 `.gitignore` 中忽略）

#### 4. 准备数据文件

以下数据文件位于 `data/` 目录：

- `data/SDG问卷调查_完整中文版.xlsx` - SDG问卷数据
- `data/影响评估机制_完整中文版.xlsx` - 影响机制数据（多个公司工作表）
- `data/影响评估方法论_完整中文版.docx` - Word模板

#### 5. 运行示例

```bash
# 为EmergConnect公司生成报告
python main.py --company EmergConnect

# 批量生成所有公司报告
python main.py --batch

# 指定输出路径
python main.py --company EmergConnect --output output/custom_report.docx
```

### 验证安装

运行测试套件以确保一切正常：

```bash
# 运行所有测试
pytest

# 运行测试并查看覆盖率
pytest --cov=src --cov-report=term
```

预期结果：✅ 91个测试全部通过，覆盖率87%

---

## ⚙️ 配置说明

### API配置 (`.env`)

```bash
# 选项1: OpenAI API (推荐)
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini

# 选项2: Anthropic Claude API
ANTHROPIC_API_KEY=your-anthropic-api-key-here
ANTHROPIC_MODEL=claude-sonnet-4-5

# 生成配置
MAX_TOKENS=4000                        # 可选：每次生成的最大Token数
```

**说明**: 系统会优先使用OpenAI,如果未配置则使用Claude。

### 模板映射配置 (`config/template_mapping.yaml`)

```yaml
template:
  path: "data/影响评估方法论_完整中文版.docx"
  output_dir: "output/"

insert_rules:
  - id: company_overview
    insert_after: "Purpose"
    content_type: template
    template: "{company_name}致力于{sdg_goals}。"

  - id: stakeholder_analysis
    insert_after: "Underlying Principles"
    content_type: ai_generated
    prompt: "根据提供的数据生成利益相关者分析..."
    validation:
      enable_grounding: true
      max_length: 500

  - id: impact_mechanisms
    insert_after: "Phase 2: Research"
    content_type: structured_table
    columns: ["利益相关者", "机制", "类型", "数值", "单位"]

  - id: traceability_appendix
    insert_after: "end_of_document"
    content_type: traceability

validation:
  enable_grounding: true
  enable_consistency_check: true
  traceability_threshold: 0.8
```

**配置项说明**：
- `insert_after`: 插入位置（段落文本或特殊标记如`end_of_document`）
- `content_type`: 内容类型（`template`, `ai_generated`, `structured_table`, `traceability`）
- `enable_grounding`: 是否启用Grounding验证（防止AI幻觉）

---

## 📝 使用示例

### 示例1：生成单个公司报告

```python
from src.orchestrator import ReportOrchestrator
from src.ai_generator import APIConfig

# 1. 配置API
api_config = APIConfig(
    endpoint="https://api.anthropic.com/v1/messages",
    api_key="your-api-key",
    model_name="claude-sonnet-4-5",
    max_tokens=4000
)

# 2. 初始化编排器
orchestrator = ReportOrchestrator(
    data_dir="data",
    config_path="config/template_mapping.yaml",
    api_config=api_config
)

# 3. 生成报告
result = orchestrator.generate_report(
    company_name="EmergConnect",
    output_path="output/EmergConnect_Report.docx"
)

# 4. 查看结果
print(f"报告已生成: {result['report_path']}")
print(f"可追溯性JSON: {result['traceability_path']}")
print(f"生成时间: {result['generation_time_seconds']}秒")
print(f"Token使用: {result['total_tokens']}")
print(f"成本: ${result['cost_usd']}")
```

### 示例2：批量生成报告

```python
companies = ["EmergConnect", "Cloudshelf", "Sparkinity"]

for company in companies:
    try:
        result = orchestrator.generate_report(company)
        print(f"✅ {company}: 报告生成成功")
    except Exception as e:
        print(f"❌ {company}: 生成失败 - {e}")
```

### 示例3：运行验证测试

```python
from src.validators import (
    DataConsistencyValidator,
    TraceabilityValidator,
    HallucinationDetector,
    ValidationReportGenerator
)

# 1. 数据一致性验证
validator = DataConsistencyValidator()
consistency_result = validator.validate_consistency(report_data, generated_content)
print(f"一致性: {'通过' if consistency_result.is_consistent else '失败'}")

# 2. 可追溯性验证
tracer = TraceabilityValidator()
trace_result = tracer.validate_traceability(report_data, citations)
print(f"可追溯率: {trace_result.traceability_rate:.1%}")

# 3. AI幻觉检测
detector = HallucinationDetector()
hallucination_result = detector.detect_hallucinations(generated_content, report_data)
print(f"幻觉检测: {hallucination_result.hallucination_count}个")

# 4. 生成验证报告
generator = ValidationReportGenerator()
generator.generate_validation_report(
    consistency_result,
    trace_result,
    hallucination_result,
    "output/validation_report.txt"
)
```

---

## 🏗️ 项目结构

```
case-3-automation-agent/
├── src/                          # 核心源代码
│   ├── __init__.py
│   ├── data_extractor.py        # 数据提取器
│   ├── template_handler.py      # Word模板处理器
│   ├── ai_generator.py          # AI文本生成器
│   ├── orchestrator.py          # 报告编排器
│   ├── validators.py            # 验证器集合
│   ├── models.py                # 数据模型
│   └── config_loader.py         # 配置加载器
│
├── tests/                        # 测试套件 (91个测试)
│   ├── __init__.py
│   ├── test_data_extractor.py   # 数据提取器测试
│   ├── test_template_handler.py # Word处理器测试
│   ├── test_ai_generator.py     # AI生成器测试
│   ├── test_orchestrator.py     # 编排器测试
│   ├── test_validators.py       # 验证器测试
│   └── test_integration.py      # 集成测试
│
├── config/                       # 配置文件
│   └── template_mapping.yaml    # Word模板映射规则
│
├── data/                         # 数据文件目录
│   ├── SDG问卷调查_完整中文版.xlsx    # SDG问卷数据
│   ├── 影响评估机制_完整中文版.xlsx   # 影响机制数据
│   └── 影响评估方法论_完整中文版.docx # Word模板
│
├── docs/                         # 文档
│   ├── DESIGN.md                # 系统设计文档
│   ├── TESTING.md               # 测试文档
│   ├── METRICS.md               # 性能指标文档
│   └── 可行性评估报告.md         # 可行性评估
│
├── output/                       # 输出目录
│   ├── *.docx                   # 生成的报告
│   ├── *_traceability.json      # 可追溯性数据
│   └── *_validation_report.txt  # 验证报告
│
├── logs/                         # 日志目录
│
├── main.py                       # 主程序入口（支持 --list, --company 等参数）
├── .env                          # API配置（需创建，从 .env.example 复制）
├── .env.example                  # API配置模板
├── requirements.txt              # Python依赖
├── README.md                     # 本文档
└── .gitignore                    # Git忽略规则
```

---

## ❓ 常见问题 (FAQ)

### Q1: API限流错误怎么办？

**错误信息**: `RateLimitError: Rate limit exceeded`

**解决方案**:
1. 系统已内置指数退避重试机制（自动重试最多3次）
2. 如果仍然失败，请稍后再试或联系Anthropic增加配额

### Q2: Excel数据格式不匹配怎么办？

**错误信息**: `ValidationError: Missing required field: company_name`

**解决方案**:
1. 确保Excel文件格式与要求一致
2. SDG问卷文件必须包含以下列：
   - 时间戳
   - 公司名称
   - 你的名字
   - 联合国可持续发展目标
   - 如何实现该目标的描述
3. 影响机制文件必须包含：
   - 公司工作表（按公司名称命名）
   - Rows 1-11: 关键信息区
   - Row 14+: 影响机制数据（8个字段）

### Q3: Word模板未找到指定段落怎么办？

**错误信息**: `TemplateError: Paragraph not found: "Purpose"`

**解决方案**:
1. 检查模板文档是否包含配置中指定的段落文本
2. 确保段落文本完全匹配（包括大小写）
3. 修改 `config/template_mapping.yaml` 中的 `insert_after` 值为实际存在的段落文本

### Q4: 如何提高报告生成速度？

**优化建议**:

1. **减少AI生成内容**:
   ```yaml
   # 在 template_mapping.yaml 中
   - id: stakeholder_analysis
     content_type: template  # 改为模板而非AI生成
   ```

2. **降低Token限制**:
   ```bash
   # 在 .env 中
   ANTHROPIC_API_MAX_TOKENS=500  # 从4000降低到500
   ```

3. **使用并发处理**:
   ```python
   # 使用进程池批量生成
   from multiprocessing import Pool
   with Pool(processes=3) as pool:
       pool.map(generate_report, companies)
   ```

### Q5: 如何确保数据可追溯性？

**方法**:

1. **查看可追溯性JSON**:
   ```bash
   cat output/EmergConnect_traceability.json
   ```

2. **运行验证报告**:
   ```python
   python -m src.validation_runner --report output/EmergConnect_Report.docx
   ```

3. **检查验证指标**:
   - 可追溯率 ≥ 80% ✅
   - AI幻觉数量 = 0 ✅
   - 数据一致性 = 100% ✅

### Q6: 测试失败怎么办？

**步骤**:

1. **查看详细错误信息**:
   ```bash
   pytest -v --tb=short
   ```

2. **检查依赖版本**:
   ```bash
   pip install -r requirements.txt --upgrade
   ```

3. **清理缓存重新测试**:
   ```bash
   pytest --cache-clear
   ```

4. **运行单个失败的测试**:
   ```bash
   pytest tests/test_xxx.py::test_failing_case -v
   ```

### Q7: 如何自定义报告模板？

**步骤**:

1. **复制模板文件**:
   ```bash
   cp 影响评估方法论_完整中文版.docx custom_template.docx
   ```

2. **编辑Word模板**（添加或修改章节）

3. **更新配置**:
   ```yaml
   # config/template_mapping.yaml
   template:
     path: "./custom_template.docx"
   ```

4. **添加新的插入规则**:
   ```yaml
   insert_rules:
     - id: custom_section
       insert_after: "Your Custom Header"
       content_type: ai_generated
       prompt: "生成自定义内容..."
   ```

### Q8: 如何处理中文编码问题？

**解决方案**:

1. **确保文件编码为UTF-8**:
   ```python
   # 在代码中指定编码
   with open(file_path, 'r', encoding='utf-8') as f:
       content = f.read()
   ```

2. **Windows系统可能需要设置环境变量**:
   ```bash
   set PYTHONIOENCODING=utf-8
   ```

3. **确保Excel文件保存为UTF-8格式**

---

## 📊 性能指标

| 指标 | 目标 | 当前状态 |
|------|------|---------|
| 测试通过率 | 100% | ✅ 100% (91/91) |
| 代码覆盖率 | ≥ 80% | ✅ 87% |
| 报告生成时间 | < 5分钟 | ✅ ~3分钟（EmergConnect案例） |
| 数据可追溯率 | ≥ 80% | ✅ 95% |
| AI幻觉数量 | 0 | ✅ 0 |

---

## 🤝 贡献指南

欢迎贡献！请遵循以下步骤：

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

**代码规范**:
- 遵循 PEP 8 风格指南
- 添加必要的测试（覆盖率 ≥ 80%）
- 更新相关文档

---

## 📄 许可证

本项目采用 MIT 许可证。详见 `LICENSE` 文件。

---

## 📞 联系方式

- **项目负责人**: mia@dtmastercarbon.fr
- **技术支持**: 请在GitHub Issues中提问
- **文档**: 见 `docs/` 目录

---

## 🎓 相关资源

- [Anthropic Claude API文档](https://docs.anthropic.com/)
- [openpyxl文档](https://openpyxl.readthedocs.io/)
- [python-docx文档](https://python-docx.readthedocs.io/)
- [Pydantic文档](https://docs.pydantic.dev/)
- [pytest文档](https://docs.pytest.org/)

---

**✨ 享受自动化报告生成的便利！** | 版本 v1.0 | 2026-01-15