### hand-written test (25 replies)

| System | Exact date ↑ | Too early ↓ | Kind ↑ | Valid JSON ↑ |
|---|---|---|---|---|
| Keyword rules | 60.0% | 16.0% | 84.0% | 100.0% |
| Qwen3-8B, untrained | 68.0% | 12.0% | 80.0% | 100.0% |
| Fine-tuned v1 (SFT, before dev fixes) | 80.0% | 12.0% | 92.0% | 100.0% |
| Fine-tuned v2 (SFT, shipped) | 92.0% | 8.0% | 100.0% | 100.0% |

### hand-written dev (50 replies)

| System | Exact date ↑ | Too early ↓ | Kind ↑ | Valid JSON ↑ |
|---|---|---|---|---|
| Keyword rules | 50.0% | 16.0% | 66.0% | 100.0% |
| Qwen3-8B, untrained | 72.0% | 6.0% | 86.0% | 100.0% |
| Fine-tuned v1 (SFT, before dev fixes) | 86.0% | 8.0% | 94.0% | 100.0% |
| Fine-tuned v2 (SFT, shipped) | 96.0% | 2.0% | 98.0% | 100.0% |

### synthetic held-out (300 replies)

| System | Exact date ↑ | Too early ↓ | Kind ↑ | Valid JSON ↑ |
|---|---|---|---|---|
| Keyword rules | 83.0% | 5.7% | 89.3% | 100.0% |
| Qwen3-8B, untrained | 69.0% | 1.3% | 70.3% | 98.0% |
| Fine-tuned v1 (SFT, before dev fixes) | 91.0% | 0.7% | 91.7% | 100.0% |
| Fine-tuned v2 (SFT, shipped) | 93.7% | 2.0% | 96.0% | 100.0% |
