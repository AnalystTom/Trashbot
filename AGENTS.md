# Trashbot Agent Notes

## Hugging Face dataset inspection

Use the built-in inspection CLI to explore `nebius/SWE-agent-trajectories` rows and schema:

```bash
python3 /Users/tom/Dev/Trashbot/hermes-agent/load_data.py
```

Useful variants:

```bash
# Focus on a few fields
python3 /Users/tom/Dev/Trashbot/hermes-agent/load_data.py \
  --sample-size 3 \
  --fields instance_id,model_name,target

# Start from a later row and print full values
python3 /Users/tom/Dev/Trashbot/hermes-agent/load_data.py \
  --start-index 100 \
  --sample-size 1 \
  --full-values
```

If your shell has `python` mapped, `python /Users/tom/Dev/Trashbot/hermes-agent/load_data.py` is equivalent.
