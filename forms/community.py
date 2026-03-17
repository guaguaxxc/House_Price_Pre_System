"""
小区信息表单模块
================================================
该模块定义了用于小区数据增删改查的 Flask-WTF 表单。
包含小区所有字段，并配置了相应的验证器，确保数据合法性。
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField, IntegerField
from wtforms.validators import DataRequired, Optional, NumberRange, Length


class CommunityForm(FlaskForm):
    """
    小区信息表单，对应 Community_info 模型的所有字段。
    用于添加和编辑小区信息时接收用户输入，并进行基础验证。
    """

    # 基础信息字段
    city = StringField(
        '城市',
        validators=[DataRequired(), Length(max=50)]  # 必填，最大长度50
    )
    community_name = StringField(
        '小区名称',
        validators=[DataRequired(), Length(max=100)]  # 必填，最大长度100
    )
    price = FloatField(
        '单价(元/㎡)',
        validators=[Optional(), NumberRange(min=0)]  # 可选，若填写则必须≥0
    )
    address = StringField(
        '地址',
        validators=[Optional(), Length(max=200)]  # 可选，最大长度200
    )
    community_link = StringField(
        '链接',
        validators=[Optional(), Length(max=200)]  # 可选，最大长度200
    )

    # 详细信息字段
    property_type = StringField(
        '物业类型',
        validators=[Optional(), Length(max=50)]  # 可选，最大长度50
    )
    ownership_type = StringField(
        '产权性质',
        validators=[Optional(), Length(max=50)]  # 可选，最大长度50
    )
    completion_time = StringField(
        '竣工时间',
        validators=[Optional(), Length(max=50)]  # 可选，最大长度50（可能包含“年”字）
    )
    property_right_years = StringField(
        '产权年限',
        validators=[Optional(), Length(max=50)]  # 可选，最大长度50（可能含“年”）
    )
    total_households = IntegerField(
        '总户数',
        validators=[Optional()]  # 可选，整数
    )
    total_building_area = FloatField(
        '总建筑面积(㎡)',
        validators=[Optional()]  # 可选，浮点数
    )
    plot_ratio = FloatField(
        '容积率',
        validators=[Optional(), NumberRange(min=0, max=10)]  # 可选，范围0-10
    )
    greening_rate = FloatField(
        '绿化率(%)',
        validators=[Optional(), NumberRange(min=0, max=100)]  # 可选，范围0-100
    )
    building_type = StringField(
        '建筑类型',
        validators=[Optional(), Length(max=100)]  # 可选，最大长度100
    )
    business_district = StringField(
        '商圈',
        validators=[Optional(), Length(max=100)]  # 可选，最大长度100
    )
    unified_heating = StringField(
        '集中供暖',
        validators=[Optional(), Length(max=10)]  # 可选，最大长度10（是/否/未知）
    )
    water_supply_power = StringField(
        '水电类型',
        validators=[Optional(), Length(max=20)]  # 可选，最大长度20（民用/商用/未知）
    )
    parking_spaces = IntegerField(
        '车位',
        validators=[Optional()]  # 可选，整数
    )
    property_fee = FloatField(
        '物业费(元/㎡·月)',
        validators=[Optional(), NumberRange(min=0)]  # 可选，必须≥0
    )
    parking_fee = FloatField(
        '停车费(元/月)',
        validators=[Optional(), NumberRange(min=0)]  # 可选，必须≥0
    )
    parking_management_fee = FloatField(
        '车位管理费(元/月)',
        validators=[Optional(), NumberRange(min=0)]  # 可选，必须≥0
    )
    property_company = StringField(
        '物业公司',
        validators=[Optional(), Length(max=100)]  # 可选，最大长度100
    )
    community_address = StringField(
        '社区地址',
        validators=[Optional(), Length(max=200)]  # 可选，最大长度200
    )
    developer = StringField(
        '开发商',
        validators=[Optional(), Length(max=100)]  # 可选，最大长度100
    )
    sale_houses = IntegerField(
        '在售房源(套)',
        validators=[Optional()]  # 可选，整数
    )
    rent_houses = IntegerField(
        '在租房源(套)',
        validators=[Optional()]  # 可选，整数
    )

    # 提交按钮
    submit = SubmitField('提交')
