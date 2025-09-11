import os

# mypackage/__init__.py
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("poe2trade")
except PackageNotFoundError:
    __version__ = "0.0.0"  # fallback for dev environments
    
# Get the absolute path of the poe2trade package root
poe2trade_root = os.path.dirname(os.path.abspath(__file__))
divine_exalt = 147
chaos_exalt = 4
quality_feature_flag = False
corrupted_feature_flag = False
ignore_allocates_flag = True
buyout_only = True
train_super_xgb: bool = True
train_super_rf:  bool = False  # not needed with XGBoost
train_super_gbr: bool = False  # not needed with XGBoost
shap_flag = False
score_training_flag = True
hyperparameter_flag = True
use_previous_model_settings = False
score_with_z = False
knn_k = 10
use_cuda = False
quantile_splitters = [50, 80]
