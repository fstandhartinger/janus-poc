# Private Benchmark Dataset

This folder is reserved for the private test suite used in competition scoring.
The JSONL files under `test/` are intentionally gitignored.

## Generate a local private dataset

```bash
cd bench/scripts
python generate_private_dataset.py
```

## Provide a secure dataset path

If you store the private dataset elsewhere, set an environment variable:

```bash
export JANUS_PRIVATE_DATASET_PATH=/absolute/path/to/private/test
```

The loader will read any `*.jsonl` files in that directory.
