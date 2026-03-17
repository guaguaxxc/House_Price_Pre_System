"""
蓝图初始化模块
================================================
该文件用于从各个蓝图模块导入蓝图实例，并注册。
"""

from .home import home_bp  # 首页相关路由
from .data import data_bp  # 数据管理（增删改查）相关路由
from .chart import chart_bp  # 图表展示相关路由
from .prediction import prediction_bp  # 房价预测相关路由
