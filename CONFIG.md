# API 配置指南

> Case 3 自动化报告生成系统 - API 配置完整说明

本文档详细说明如何配置系统所需的 API 密钥和相关设置。

---

## 📋 目录

- [快速开始](#快速开始)
- [配置方式](#配置方式)
- [配置优先级](#配置优先级)
- [Claude API 配置](#claude-api-配置)
- [其他 AI 服务商配置](#其他-ai-服务商配置)
- [故障排查](#故障排查)
- [安全最佳实践](#安全最佳实践)

---

## 🚀 快速开始

### 步骤 1: 获取 API 密钥

本项目使用 **Azure AI Foundry** 托管的 **Claude API**。

**获取方式**：
- **方式 A**（推荐）：从面试官处获取临时 API 密钥
- **方式 B**：使用您自己的 Anthropic API 密钥

### 步骤 2: 创建环境变量文件

```bash
# 复制模板文件
cp .env.example .env

# 编辑 .env 文件，填写您的 API 密钥
nano .env  # 或使用您喜欢的编辑器
```

### 步骤 3: 填写必需配置

在 `.env` 文件中，至少需要配置以下内容：

```bash
# Claude API 密钥（必需）
ANTHROPIC_API_KEY=your-actual-api-key-here

# API 端点（使用默认值即可）
ANTHROPIC_ENDPOINT=https://agentinterview-resource.services.ai.azure.com/anthropic/

# 模型名称（推荐使用 sonnet）
ANTHROPIC_MODEL=claude-sonnet-4-5
```

### 步骤 4: 验证配置

运行测试脚本验证配置是否正确：

```bash
# 方式 1：使用 demo.sh 脚本
bash demo.sh

# 方式 2：直接运行测试
python -c "from src.ai_generator import create_generator_from_config; g = create_generator_from_config(); print('✅ API 配置成功!')"
```

---

## ⚙️ 配置方式

系统支持两种配置方式：

### 方式 1: 环境变量配置（推荐）

**优点**：
- ✅ 安全性高（不会意外提交到 Git）
- ✅ 灵活性强（不同环境可使用不同配置）
- ✅ 符合最佳实践

**步骤**：

1. 创建 `.env` 文件（已在 `.gitignore` 中）：
   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env` 文件：
   ```bash
   ANTHROPIC_API_KEY=sk-ant-xxxxx
   ANTHROPIC_ENDPOINT=https://agentinterview-resource.services.ai.azure.com/anthropic/
   ANTHROPIC_MODEL=claude-sonnet-4-5
   ```

3. 系统会自动读取环境变量

### 方式 2: 直接修改 case3_config.py（不推荐）

**缺点**：
- ⚠️ 容易意外提交 API 密钥到 Git
- ⚠️ 难以管理多环境配置

**步骤**：

编辑 `case3_config.py` 文件：

```python
# Claude API 配置
endpoint = "https://agentinterview-resource.services.ai.azure.com/anthropic/"
deployment_name = "claude-sonnet-4-5"
api_key = "sk-ant-xxxxx"  # 替换为您的实际 API 密钥
```

---

## 🔄 配置优先级

系统按以下优先级读取配置（从高到低）：

1. **环境变量** `ANTHROPIC_API_KEY`
2. **环境变量** `CLAUDE_API_KEY`（兼容性备选）
3. **默认值**（如果未设置则报错）

**示例代码**（在 `src/ai_generator.py` 中）：

```python
# 优先从环境变量读取
api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")

if not api_key:
    raise ValueError(
        "API key not found. Set ANTHROPIC_API_KEY or CLAUDE_API_KEY "
        "environment variable"
    )
```

---

## 🤖 Claude API 配置

### Azure AI Foundry 端点

本项目使用 **Azure AI Foundry** 托管的 Claude API。

**配置参数**：

| 参数名 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| API 密钥 | `ANTHROPIC_API_KEY` | *（必需）* | 从面试官获取或使用自己的密钥 |
| API 端点 | `ANTHROPIC_ENDPOINT` | `https://agentinterview-resource.services.ai.azure.com/anthropic/` | Azure AI Foundry 端点 |
| 模型名称 | `ANTHROPIC_MODEL` | `claude-sonnet-4-5` | 推荐使用 sonnet（性价比高） |

### 可用模型

| 模型名称 | 特点 | 适用场景 | 成本 |
|----------|------|----------|------|
| `claude-opus-4-5` | 最强大 | 复杂推理、长文档分析 | 高 |
| `claude-sonnet-4-5` | **推荐** | 平衡性能和成本 | 中 |

### Azure AI Foundry 特殊处理

系统会自动检测 Azure AI Foundry 端点并进行特殊处理：

```python
if "azure" in api_config.endpoint.lower():
    # Azure AI Foundry 使用自定义端点
    self.client = Anthropic(
        api_key=api_config.api_key,
        base_url=api_config.endpoint
    )
else:
    # 标准 Anthropic API
    self.client = Anthropic(api_key=api_config.api_key)
```

### 标准 Anthropic API（可选）

如果您想使用标准的 Anthropic API（而非 Azure AI Foundry）：

```bash
# .env 文件
ANTHROPIC_API_KEY=sk-ant-xxxxx
ANTHROPIC_ENDPOINT=https://api.anthropic.com/v1
ANTHROPIC_MODEL=claude-sonnet-4-5
```

---

## 🌐 其他 AI 服务商配置

系统预留了其他 AI 服务商的配置接口（在 `case3_config.py` 中），但当前版本仅支持 Claude。

### OpenAI（预留）

```bash
OPENAI_API_KEY=your-openai-key
OPENAI_ENDPOINT=https://agentinterview-resource.services.ai.azure.com/openai/
OPENAI_MODEL=gpt-4
```

### DeepSeek（预留）

```bash
DEEPSEEK_API_KEY=your-deepseek-key
DEEPSEEK_ENDPOINT=https://agentinterview-resource.services.ai.azure.com/deepseek/
DEEPSEEK_MODEL=deepseek-chat
```

### Google Gemini（预留）

```bash
GEMINI_API_KEY=your-gemini-key
GEMINI_ENDPOINT=https://agentinterview-resource.services.ai.azure.com/gemini/
GEMINI_MODEL=gemini-pro
```

### Mistral（预留）

```bash
MISTRAL_API_KEY=your-mistral-key
MISTRAL_ENDPOINT=https://agentinterview-resource.services.ai.azure.com/mistral/
MISTRAL_MODEL=mistral-large-latest
```

> **注意**：这些服务商配置目前仅供参考，实际使用需要修改代码以支持。

---

## 🔧 故障排查

### 问题 1: API 密钥未找到

**错误信息**：
```
ValueError: API key not found. Set ANTHROPIC_API_KEY or CLAUDE_API_KEY environment variable
```

**解决方法**：

1. 确认 `.env` 文件存在：
   ```bash
   ls -la .env
   ```

2. 确认 `.env` 文件中有 `ANTHROPIC_API_KEY`：
   ```bash
   cat .env | grep ANTHROPIC_API_KEY
   ```

3. 确认密钥不为空：
   ```bash
   echo $ANTHROPIC_API_KEY
   ```

4. 如果使用 Python 脚本，确保加载了 `.env`：
   ```python
   from dotenv import load_dotenv
   load_dotenv()  # 加载 .env 文件
   ```

### 问题 2: API 调用失败 (401 Unauthorized)

**错误信息**：
```
anthropic.AuthenticationError: 401 Unauthorized
```

**解决方法**：

1. 确认 API 密钥正确：
   - 检查是否有多余的空格
   - 确认密钥格式正确（通常以 `sk-ant-` 开头）

2. 确认密钥有效：
   - 密钥可能已过期
   - 密钥可能已被撤销
   - 联系面试官获取新密钥

### 问题 3: API 调用超时

**错误信息**：
```
requests.exceptions.Timeout: Request timeout after 60s
```

**解决方法**：

1. 检查网络连接：
   ```bash
   curl https://agentinterview-resource.services.ai.azure.com/anthropic/
   ```

2. 增加超时时间（在 `.env` 中）：
   ```bash
   REQUEST_TIMEOUT=120
   ```

3. 检查防火墙设置

### 问题 4: API 限流 (429 Too Many Requests)

**错误信息**：
```
anthropic.RateLimitError: 429 Too Many Requests
```

**解决方法**：

系统已内置重试机制（指数退避），但如果仍然遇到限流：

1. 减少并发请求数量
2. 增加请求间隔
3. 联系面试官增加 API 配额

---

## 🔒 安全最佳实践

### 1. 永远不要提交 API 密钥到 Git

**检查清单**：
- ✅ `.env` 已在 `.gitignore` 中
- ✅ 使用 `.env.example` 作为模板
- ✅ 定期检查 Git 历史记录

**验证**：
```bash
# 确认 .env 被忽略
git status | grep .env
# 应该不显示 .env

# 确认 .gitignore 包含 .env
cat .gitignore | grep "^\.env$"
# 应该显示 .env
```

### 2. 使用环境变量而非硬编码

**❌ 不推荐**：
```python
api_key = "sk-ant-xxxxx"  # 硬编码密钥
```

**✅ 推荐**：
```python
api_key = os.getenv("ANTHROPIC_API_KEY")  # 从环境变量读取
```

### 3. 定期轮换 API 密钥

- 建议每 30-90 天更换一次 API 密钥
- 使用完临时密钥后及时撤销

### 4. 限制 API 密钥权限

- 只授予必要的权限
- 使用只读密钥（如果可能）

### 5. 监控 API 使用量

- 定期检查 Token 使用量
- 设置使用量告警

---

## 📚 相关文档

- [README.md](README.md) - 项目使用说明
- [DESIGN.md](docs/DESIGN.md) - 系统设计文档
- [METRICS.md](docs/METRICS.md) - 性能和 Token 统计
- [.env.example](.env.example) - 环境变量模板

---

## ❓ 常见问题（FAQ）

### Q: 可以使用免费的 API 密钥吗？

A: 可以，但免费密钥通常有较严格的限流限制。建议使用付费密钥以获得更好的体验。

### Q: 如何查看 API 使用量？

A: 系统会在每次生成报告后输出 Token 使用统计。详见 [METRICS.md](docs/METRICS.md)。

### Q: 是否支持其他 AI 服务商？

A: 当前版本仅支持 Claude API。其他服务商配置已预留接口，但需要代码修改。

### Q: 如何切换模型？

A: 修改 `.env` 文件中的 `ANTHROPIC_MODEL` 变量：
```bash
# 使用 Opus（更强大，成本更高）
ANTHROPIC_MODEL=claude-opus-4-5

# 使用 Sonnet（推荐，性价比高）
ANTHROPIC_MODEL=claude-sonnet-4-5
```

---

## 📞 获取帮助

如果您在配置过程中遇到问题：

1. 查看本文档的 [故障排查](#故障排查) 部分
2. 查看系统日志（`logs/` 目录）
3. 联系面试官获取支持
4. 提交 Issue（如果适用）

---

**祝您配置顺利！** 🎉
