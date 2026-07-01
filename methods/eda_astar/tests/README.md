# Tests - Unit Testing Scripts

This directory contains unit tests for the EDA-CostA* project components.

---

## 📋 Test Scripts

### Risk Model Tests
- **test_fatality_risk.py** - Fatality risk model validation (Eq. 1-9)
- **test_traffic_risk.py** - Traffic risk model validation
- **test_noise_risk.py** - Noise risk model (original version)
- **test_noise_risk_corrected.py** - Noise risk model (corrected version)
- **test_noise_risk_standalone.py** - Noise risk standalone test

### Integration Tests
- **test_integrated_cost.py** - Integrated cost assessment model (Pang et al. 2022)
- **test_two_stage_eda.py** - Two-Stage EDA-CostA* algorithm validation

---

## 📊 Output Location

All test visualizations and outputs are saved to:

```
output/tests/
├── test_fatality_risk/
│   ├── fatality_risk_by_altitude.png
│   └── population_density.png
│
├── test_traffic_risk/
│   └── traffic_risk.png
│
└── ... (other test outputs)
```

**Note**: Unlike experiments which save to `output/experiment_XX/`, test outputs are organized under `output/tests/` for clear separation.

---

## 🚀 Running Tests

### Run All Tests
```bash
# Using uv
uv run python -m pytest tests/ -v

# Or run individual scripts
uv run python tests/test_fatality_risk.py
uv run python tests/test_traffic_risk.py
uv run python tests/test_integrated_cost.py
uv run python tests/test_two_stage_eda.py
```

### Run Specific Test
```bash
# Fatality risk model
uv run python tests/test_fatality_risk.py

# Traffic risk model
uv run python tests/test_traffic_risk.py

# Integrated cost model
uv run python tests/test_integrated_cost.py

# Two-Stage EDA algorithm
uv run python tests/test_two_stage_eda.py
```

---

## ✅ Test Coverage

| Component | Test Script | Status |
|-----------|-------------|--------|
| Fatality Risk Model | test_fatality_risk.py | ✅ Complete |
| Traffic Risk Model | test_traffic_risk.py | ✅ Complete |
| Noise Risk Model | test_noise_risk*.py | ✅ Complete |
| Integrated Cost Model | test_integrated_cost.py | ✅ Complete |
| Two-Stage EDA Algorithm | test_two_stage_eda.py | ✅ Complete |

---

## 📝 Writing New Tests

When adding new test scripts:

1. **Naming Convention**: Use `test_<component>.py` format
2. **Output Directory**: Save outputs to `output/tests/test_<component>/`
3. **Documentation**: Include docstring explaining what is tested
4. **Validation**: Print clear pass/fail indicators (✓/✗)

**Example**:
```python
from pathlib import Path

# Output directory
output_dir = Path(__file__).parent.parent / "output" / "tests" / "test_my_component"
output_dir.mkdir(parents=True, exist_ok=True)

# Save visualization
plt.savefig(output_dir / "result.png", dpi=150, bbox_inches='tight')
```

---

**Last Updated**: 2026-04-27
