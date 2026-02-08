# Proposal Workspace

Standalone workspace for the proposal pipeline using LangGraph.

## Quick start

- Create a virtual environment and install dependencies.

```bash
pip install -r requirements.txt
pip install -e .
```

- Run the CLI:

```bash
proposal-cli run --spec /path/to/spec.docx --out /path/to/output
```

## Notes

- Use `--manual` to provide non-interactive cover/schedule inputs.
- Use `--debug` to write `debug/evidence.json`, `debug/llm_output.json`, and `debug/placeholder_map.json`.
