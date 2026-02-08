# DocCollate

DocCollate 已拆分为多个可独立运行的子项目，每个目录负责一类材料生成。

## 目录结构

- `proposal/`：项目建议书生成
- `copyright/`：软件著作权登记申请表生成（DOCX）
- `registration/`：软件产品登记测试表生成（DOCX）
- `environment/`：非嵌入式环境文档生成（DOCX）
- `function/`：产品测试功能表生成（DOCX）
- `assessment/`：产品评估申请材料生成（XLSX）

## 通用要求

- Python `>=3.10`
- 每个子项目使用各自虚拟环境（推荐 `.venv`）
- 如需 LLM 功能，请配置环境变量：
  - `DOCCOLLATE_LLM_API_KEY`
  - `DOCCOLLATE_LLM_BASE_URL`
  - `DOCCOLLATE_LLM_MODEL`

## 快速启动（以 assessment 为例）

```bash
cd /home/charlie/workspace/doccollate/assessment
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python3 src/main.py run --input-json /home/charlie/workspace/doccollate/assessment/input_assessment.json --debug
```

## 各模块运行命令

### copyright

```bash
cd /home/charlie/workspace/doccollate/copyright
source .venv/bin/activate
python3 src/main.py run --input-json /home/charlie/workspace/doccollate/copyright/input_copyright.json --debug
```

### registration

```bash
cd /home/charlie/workspace/doccollate/registration
source .venv/bin/activate
python3 src/main.py run --input-json /home/charlie/workspace/doccollate/registration/input_registration.json --debug
```

### environment

```bash
cd /home/charlie/workspace/doccollate/environment
source .venv/bin/activate
python3 src/main.py run --input-json /home/charlie/workspace/doccollate/environment/input_environment.json --debug
```

### function

```bash
cd /home/charlie/workspace/doccollate/function
source .venv/bin/activate
python3 src/main.py run --input-json /home/charlie/workspace/doccollate/function/input_function.json --debug
```

### assessment

```bash
cd /home/charlie/workspace/doccollate/assessment
source .venv/bin/activate
python3 src/main.py run --input-json /home/charlie/workspace/doccollate/assessment/input_assessment.json --debug
```

## 调试输出

开启 `--debug` 后，通常会在模块目录下生成 `debug/`，例如：

- `*.stage1.json`：检索上下文、评分结果等中间数据
- `*.stage2.json`：最终结构化字段

## 注意事项

- 路径支持 Windows/WSL/Linux 自适应（已做统一路径处理）。
- 若推送 GitHub 报 `fetch first`，先执行：

```bash
git fetch origin
```

