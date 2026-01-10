# DocCollate

DocCollate is a local CLI that turns a structured software manual (Markdown) into a full set of software test, assessment, and copyright forms. It uses chapter-scoped prompts so each field is generated from the correct section, then writes DOCX/XLSX outputs.

## What it generates

- 产品测试功能表 (.docx)
- 产品测试登记表 (.docx)
- 非嵌入式软件环境 (.docx)
- 产品评估申请 (.xlsx)
- 计算机软件著作权登记申请表 (.docx)

## Requirements

- Python 3.10+
- A compatible OpenAI API endpoint and key

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Set template paths (absolute paths required):

```bash
export DOCCOLLATE_TEMPLATE_FUNC=/abs/path/产品测试功能表.docx
export DOCCOLLATE_TEMPLATE_REG=/abs/path/产品测试登记表.docx
export DOCCOLLATE_TEMPLATE_ENV=/abs/path/非嵌入式软件环境.docx
export DOCCOLLATE_TEMPLATE_ASSESS=/abs/path/产品评估申请所需材料.xlsx
export DOCCOLLATE_TEMPLATE_COPYRIGHT=/abs/path/计算机软件著作权登记申请表.docx
```

Set API settings:

```bash
export OPENAI_API_KEY=your_key
export OPENAI_BASE_URL=your_base_url  # optional
export OPENAI_MODEL=gpt-4o-mini       # optional
```

Company profiles live in `soft_copyright.yaml`.

## Usage

Run interactively:

```bash
python -m doccollate
```

Or pass inputs directly:

```bash
python -m doccollate \
  --input /path/to/manual.md \
  --app-name "软件名称" \
  --app-version "V1.0"
```

Notes:

- Only Markdown manuals are supported.
- The tool reads only the required chapters per field.
- `app__name` and `app__version` are entered manually.
- Machine model/config and OS pools are generated without relying on the manual.

## Outputs

All generated files are saved under the output directory you select at runtime.

## License

Internal use.
