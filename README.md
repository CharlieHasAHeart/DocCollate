# DocCollate

DocCollate 是一个本地 CLI 工具，用于将结构化的软件说明书（Markdown）转换为完整的软件测试、评估与软著申请材料。它按章节分块并通过 BM25 检索筛选上下文，再生成字段内容并输出 DOCX/XLSX 文档。

## 产出内容

- 产品测试功能表（.docx）
- 产品测试登记表（.docx）
- 非嵌入式软件环境（.docx）
- 产品评估申请（.xlsx）
- 计算机软件著作权登记申请表（.docx）

## 环境要求

- Python 3.10+
- 可用的 OpenAI 兼容接口与 API Key

## 安装与配置

安装依赖：

```bash
pip install -r requirements.txt
```

配置模板路径（必须使用绝对路径）：

```bash
export DOCCOLLATE_TEMPLATE_FUNC=/abs/path/产品测试功能表.docx
export DOCCOLLATE_TEMPLATE_REG=/abs/path/产品测试登记表.docx
export DOCCOLLATE_TEMPLATE_ENV=/abs/path/非嵌入式软件环境.docx
export DOCCOLLATE_TEMPLATE_ASSESS=/abs/path/产品评估申请所需材料.xlsx
export DOCCOLLATE_TEMPLATE_COPYRIGHT=/abs/path/计算机软件著作权登记申请表.docx
```

配置 API：

```bash
export OPENAI_API_KEY=your_key
export OPENAI_BASE_URL=your_base_url  # 可选
export OPENAI_MODEL=gpt-4o-mini       # 可选
```

公司信息配置保存在 `soft_copyright.yaml`。

## 使用方式

交互运行：

```bash
python -m doccollate
```

或直接传参：

```bash
python -m doccollate \
  --input /path/to/manual.md \
  --app-name "软件名称" \
  --app-version "V1.0"
```

说明：

- 当前仅支持 Markdown 说明书。
- 字段抽取使用 BM25 检索获取相关上下文。
- 功能表采用 Coverage Retrieval：先覆盖式收集模块，再用 LLM 规范化描述。
- `app__name` 与 `app__version` 由命令行输入。
- 机器型号/配置与 OS 池为内置随机生成，不依赖说明书。

## 输出位置

所有生成文件会保存到你运行时选择的输出目录中。

## 许可证

内部使用。
