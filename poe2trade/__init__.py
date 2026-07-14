import os
import ast
from pathlib import Path

# mypackage/__init__.py
from importlib.metadata import PackageNotFoundError, version


def _version_from_setup_py():
    setup_py = Path(__file__).resolve().parents[1] / "setup.py"
    if not setup_py.exists():
        return None
    try:
        tree = ast.parse(setup_py.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None
    for node in ast.walk(tree):
        for keyword in getattr(node, "keywords", []):
            if getattr(keyword, "arg", None) == "version" and isinstance(keyword.value, ast.Constant):
                return str(keyword.value.value)
    return None


# build version
try:
    from ._build_meta import __build_version__
except ImportError:
    __build_version__ = None

if __build_version__:
    __version__ = __build_version__
else:
    __version__ = _version_from_setup_py()
    if not __version__:
        try:
            __version__ = version("poe2trade")
        except PackageNotFoundError:
            __version__ = "0.0.0"

# build date
try:
    from ._build_meta import __build_date__
except ImportError:
    __build_date__ = "dev"

# build commit
try:
    from ._build_meta import __build_commit__
except ImportError:
    __build_commit__ = "unknown"

# Get the absolute path of the poe2trade package root
poe2trade_root = os.path.dirname(os.path.abspath(__file__))
jewel_list = [
    "Sapphire",
    "Emerald",
    "Ruby",
    "Diamond",
    "Time-Lost_Sapphire",
    "Time-Lost_Emerald",
    "Time-Lost_Ruby",
    "Time-Lost_Diamond",
]
divine_exalt = 435
chaos_exalt = 59
annul_exalt = 332
quality_feature_flag = False
corrupted_feature_flag = False
item_status_feature_flag = False
ignore_allocates_flag = True
buyout_only = False
train_super_xgb: bool = True
train_super_rf:  bool = False  # not needed with XGBoost
train_super_gbr: bool = False  # not needed with XGBoost
train_super_log_price: bool = True  # train regressors on log1p(price); predictions auto-inverted to exalts
shap_flag = False
score_training_flag = True
hyperparameter_flag = True
use_previous_model_settings = False
score_with_z = False
use_cuda = False
quantile_splitters = [50, 80]
use_dev = False
