"""
config_loader.py — Brand Configuration Management

Responsibilities:
  - Load BaselineConfig from YAML files in configs/
  - Validate the loaded data through Pydantic models
  - Provide clear, actionable error messages when a config is invalid
  - Save configs back to YAML (round-trip support)
  - List all available brand configs

Usage:
    from config_loader import load_config, list_configs

    config = load_config("configs/aeobrand.yaml")
    print(config.summary())
"""

import sys
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML is not installed. Run: pip install pyyaml")
    sys.exit(1)

from pydantic import ValidationError

# Ensure src/ is on the path when called from the project root
sys.path.insert(0, str(Path(__file__).parent))
from models import BaselineConfig, IntentMix

# Default configs directory (project root / configs/)
_DEFAULT_CONFIGS_DIR = Path(__file__).parent.parent / "configs"


# ── Public API ─────────────────────────────────────────────────────────────────

def load_config(path: str | Path) -> BaselineConfig:
    """
    Load and validate a brand configuration from a YAML file.

    Args:
        path: Absolute or relative path to a .yaml config file.

    Returns:
        Validated BaselineConfig instance.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the YAML is invalid or fails Pydantic validation.
    """
    config_path = Path(path).resolve()

    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}\n"
            f"  - Copy configs/example_template.yaml and edit it.\n"
            f"  - Available configs: {[c.name for c in list_configs()]}"
        )

    if config_path.suffix not in (".yaml", ".yml"):
        raise ValueError(f"Config file must be .yaml or .yml, got: {config_path.suffix}")

    # ── Parse YAML ────────────────────────────────────────────────────────────
    try:
        with open(config_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ValueError(
            f"YAML parse error in {config_path.name}:\n  {exc}\n"
            "  Check for incorrect indentation or missing quotes."
        ) from exc

    if not isinstance(raw, dict):
        raise ValueError(f"{config_path.name} must be a YAML mapping (dictionary), not a list or scalar.")

    # ── Normalise intent_mix (YAML dict → IntentMix model) ───────────────────
    if "intent_mix" in raw and isinstance(raw["intent_mix"], dict):
        try:
            raw["intent_mix"] = IntentMix(**raw["intent_mix"])
        except Exception as exc:
            raise ValueError(f"intent_mix is invalid: {exc}") from exc

    # ── Validate with Pydantic ────────────────────────────────────────────────
    try:
        config = BaselineConfig(**raw)
    except ValidationError as exc:
        _raise_friendly_validation_error(exc, config_path.name)

    return config


def save_config(config: BaselineConfig, path: str | Path) -> None:
    """
    Serialise a BaselineConfig back to a YAML file.

    Useful for saving a programmatically created config so it can be reused.

    Args:
        config: The validated BaselineConfig to save.
        path:   Destination .yaml file path (created if missing).
    """
    output_path = Path(path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to plain dict, serialising nested models
    data = config.model_dump()
    # intent_mix comes out as a nested dict — that's fine for YAML
    data["intent_mix"] = config.intent_mix.model_dump()

    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"[config_loader] Config saved → {output_path}")


def list_configs(directory: str | Path = _DEFAULT_CONFIGS_DIR) -> list[Path]:
    """
    Return all .yaml / .yml files found in a directory.

    Args:
        directory: Folder to scan (defaults to configs/).

    Returns:
        Sorted list of Path objects.
    """
    d = Path(directory)
    if not d.exists():
        return []
    return sorted(d.glob("*.yaml")) + sorted(d.glob("*.yml"))


def load_default_config() -> BaselineConfig:
    """
    Load the first non-template config in configs/, falling back to the
    built-in AEOBrand demo config if nothing else is available.

    Useful for scripts that want a config without requiring a CLI argument.
    """
    available = [
        p for p in list_configs()
        if "template" not in p.stem.lower()
    ]
    if available:
        return load_config(available[0])

    # Hard-coded fallback — always works, even with no YAML files
    return _builtin_demo_config()


def _builtin_demo_config() -> BaselineConfig:
    """Return the hard-coded AEOBrand demo config (no file dependency)."""
    return BaselineConfig(
        brand_name="AEOBrand",
        competitors=["Semrush", "BrightEdge", "Conductor"],
        keywords=[
            "Answer Engine Optimization",
            "AI brand visibility",
            "LLM brand tracking",
            "generative AI SEO",
        ],
        domain_context=(
            "B2B SaaS platform that measures how enterprise brands are "
            "represented across Large Language Models including ChatGPT, "
            "Claude, Gemini, and Perplexity."
        ),
        industry="B2B SaaS / MarTech",
        geography=["United States", "United Kingdom"],
        product_lines=["AEO Analytics Dashboard", "Brand Visibility Monitor"],
        use_cases=[
            "track brand mentions across AI assistants",
            "benchmark brand visibility against competitors",
        ],
        target_audience="CMOs and digital marketing directors at mid-to-large enterprises",
        num_prompts=10,
    )


# ── Error formatting ───────────────────────────────────────────────────────────

def _raise_friendly_validation_error(exc: ValidationError, filename: str) -> None:
    """Convert Pydantic ValidationError into a clear, actionable message."""
    lines = [f"\n[Config Error] '{filename}' failed validation:\n"]
    for error in exc.errors():
        field = " → ".join(str(loc) for loc in error["loc"])
        msg   = error["msg"]
        lines.append(f"  Field '{field}': {msg}")
    lines.append(
        "\n  Tip: Compare your file against configs/example_template.yaml"
    )
    raise ValueError("\n".join(lines)) from exc


# ── CLI: python src/config_loader.py ─────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AEOBrand Config Loader Utility")
    parser.add_argument("--list",     action="store_true", help="List all configs in configs/")
    parser.add_argument("--validate", metavar="FILE",      help="Validate a config file")
    parser.add_argument("--show",     metavar="FILE",      help="Show parsed config fields")
    args = parser.parse_args()

    if args.list:
        configs = list_configs()
        if not configs:
            print("No config files found in configs/")
        else:
            print(f"Found {len(configs)} config file(s):\n")
            for p in configs:
                try:
                    cfg = load_config(p)
                    print(f"  [OK] {p.name:<35}  {cfg.summary()}")
                except Exception as e:
                    print(f"  [ERR] {p.name:<34}  {e}")

    elif args.validate:
        try:
            cfg = load_config(args.validate)
            print(f"[OK] '{args.validate}' is valid.\n{cfg.summary()}")
        except Exception as e:
            print(f"[FAIL] {e}")
            sys.exit(1)

    elif args.show:
        try:
            cfg = load_config(args.show)
            import json
            print(json.dumps(cfg.model_dump(), indent=2, default=str))
        except Exception as e:
            print(f"[FAIL] {e}")
            sys.exit(1)

    else:
        print("Usage:")
        print("  python src/config_loader.py --list")
        print("  python src/config_loader.py --validate configs/aeobrand.yaml")
        print("  python src/config_loader.py --show configs/aeobrand.yaml")
