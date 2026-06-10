import os

# mypackage/__init__.py
from importlib.metadata import version, PackageNotFoundError

# build version
try:
    __version__ = version("poe2trade")
except PackageNotFoundError:
    try:
        from ._build_meta import __build_version__
    except ImportError:
        __build_version__ = "0.0.0"
    __version__ = __build_version__

# build date
try:
    from ._build_meta import __build_date__
except ImportError:
    __build_date__ = "dev"
    
# Get the absolute path of the poe2trade package root
poe2trade_root = os.path.dirname(os.path.abspath(__file__))
jewel_list=['sapphire','emerald','ruby']
divine_exalt = 110
chaos_exalt = 10
annul_exalt = 60
quality_feature_flag = False
corrupted_feature_flag = False
ignore_allocates_flag = True
buyout_only = False
train_super_xgb: bool = True
train_super_rf:  bool = False  # not needed with XGBoost
train_super_gbr: bool = False  # not needed with XGBoost
shap_flag = False
score_training_flag = True
hyperparameter_flag = True
use_previous_model_settings = False
score_with_z = False
use_cuda = False
quantile_splitters = [50, 80]
use_dev = False
