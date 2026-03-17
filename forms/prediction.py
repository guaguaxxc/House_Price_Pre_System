"""
房价预测表单模块
================================================
该模块定义了用于房价预测的输入表单，包含模型所需的所有特征字段。
字段类型包括下拉选择框（SelectField）和文本输入框，并配置了必要的验证器。
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, FloatField, SubmitField
from wtforms.validators import DataRequired, NumberRange


class PredictionForm(FlaskForm):
    """
    房价预测表单，用户需填写小区相关信息，提交后由模型进行价格预测。
    字段与模型训练时的特征一一对应。
    """
    # 城市下拉框，选项在视图函数中动态加载（从数据库获取）
    city = SelectField(
        '城市',
        choices=[],  # 选项将在渲染时动态填充
        validators=[DataRequired()]  # 必填
    )

    # 物业类型下拉框，预定义常见类型
    property_type = SelectField(
        '物业类型',
        choices=[
            ('住宅', '住宅'),
            ('公寓', '公寓'),
            ('商铺', '商铺'),
            ('写字楼', '写字楼'),
            ('别墅', '别墅'),
            ('其他', '其他')
        ],
        validators=[DataRequired()]  # 必填
    )

    # 建筑类型，文本输入（例如“高层/小高层”）
    building_type = StringField(
        '建筑类型',
        validators=[DataRequired()]  # 必填
    )

    # 竣工时间，文本输入（例如“2010年”）
    completion_time = StringField(
        '竣工时间',
        validators=[DataRequired()]  # 必填
    )

    # 产权年限，文本输入（可能包含“年”字）
    property_right_years = StringField(
        '产权年限',
        validators=[DataRequired()]  # 必填
    )

    # 物业费，浮点数，限制范围
    property_fee = FloatField(
        '物业费(元/㎡·月)',
        validators=[DataRequired(), NumberRange(min=0, max=20)]  # 必填，范围0-20
    )

    # 容积率，浮点数，限制范围
    plot_ratio = FloatField(
        '容积率',
        validators=[DataRequired(), NumberRange(min=0, max=10)]  # 必填，范围0-10
    )

    # 绿化率，浮点数，限制范围
    greening_rate = FloatField(
        '绿化率(%)',
        validators=[DataRequired(), NumberRange(min=0, max=100)]  # 必填，范围0-100
    )

    # 集中供暖，下拉选择
    unified_heating = SelectField(
        '集中供暖',
        choices=[
            ('是', '是'),
            ('否', '否'),
            ('未知', '未知')
        ],
        validators=[DataRequired()]  # 必填
    )

    # 水电类型，下拉选择
    water_supply_power = SelectField(
        '水电类型',
        choices=[
            ('民用', '民用'),
            ('商用', '商用'),
            ('未知', '未知')
        ],
        validators=[DataRequired()]  # 必填
    )

    # 提交按钮
    submit = SubmitField('预测')
