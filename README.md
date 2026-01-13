# DocCollate

DocCollate is a CLI tool that generates three groups of documents from a software spec:

- Proposal: 立项建议书
- Test forms: 产品测试功能表 / 产品测试登记表 / 非嵌入式软件环境 / 产品评估申请表
- Copyright: 计算机软件著作权登记申请表

All outputs share the same spec input and output directory. You choose which group to generate.

## Install

```bash
uv pip install -e .
```

## Run

```bash
doccollate
```

The CLI will prompt for:

- Output directory
- Spec file path (`.md`, `.docx`, `.pdf`)
- Software name + version (manual input)
- Contact preset (from `soft_copyright.yaml`)
- Applicant type (only for copyright or all)

## Templates

Templates live in `assets/` and are configured via `.env` or `pyproject.toml`.
Current template file names:

- `assets/proposal_template.docx`
- `assets/test_function_form.docx`
- `assets/test_registration_form.docx`
- `assets/assessment_application_materials.xlsx`
- `assets/non_embedded_environment.docx`
- `assets/software_copyright_application_form.docx`

## Configuration

### Environment (.env)

```dotenv
DOCCOLLATE_LLM_API_KEY=...
DOCCOLLATE_LLM_BASE_URL=...
DOCCOLLATE_LLM_MODEL=...

DOCCOLLATE_TEMPLATE_PROPOSAL=...
DOCCOLLATE_TEMPLATE_FUNC=...
DOCCOLLATE_TEMPLATE_REG=...
DOCCOLLATE_TEMPLATE_ASSESS=...
DOCCOLLATE_TEMPLATE_ENV=...
DOCCOLLATE_TEMPLATE_COPYRIGHT=...

DOCCOLLATE_CONTACT_INFO=.../soft_copyright.yaml
DOCCOLLATE_PANDOC_SAVE_MD=1
```

### pyproject.toml

`tool.doccollate.*` contains default values for templates, dates, and proposal settings.
Values can be overridden by `.env`.

## Spec parsing

- `.md`: parsed directly
- `.docx`: converted via pandoc to markdown (if available), otherwise parsed via python-docx
- `.pdf`: parsed via pdfplumber

If `DOCCOLLATE_PANDOC_SAVE_MD=1`, the converted markdown is saved next to the input file.

## Notes

- The tool generates all data fields (even if a target does not use them).
- For product type in the assessment Excel, the value is normalized to one of the allowed options.
