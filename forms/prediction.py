from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, FloatField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange


class PredictionForm(FlaskForm):
    city = SelectField('城市', choices=[], validators=[DataRequired()])
    property_type = SelectField('物业类型', choices=[
        ('住宅', '住宅'), ('公寓', '公寓'), ('商铺', '商铺'),
        ('写字楼', '写字楼'), ('别墅', '别墅'), ('其他', '其他')
    ], validators=[DataRequired()])
    building_type = StringField('建筑类型', validators=[DataRequired()])
    completion_time = StringField('竣工时间', validators=[DataRequired()])
    property_right_years = StringField('产权年限', validators=[DataRequired()])
    property_fee = FloatField('物业费(元/㎡·月)', validators=[DataRequired(), NumberRange(min=0, max=20)])
    plot_ratio = FloatField('容积率', validators=[DataRequired(), NumberRange(min=0, max=10)])
    greening_rate = FloatField('绿化率(%)', validators=[DataRequired(), NumberRange(min=0, max=100)])
    unified_heating = SelectField('集中供暖', choices=[('是', '是'), ('否', '否'), ('未知', '未知')],
                                  validators=[DataRequired()])
    water_supply_power = SelectField('水电类型', choices=[('民用', '民用'), ('商用', '商用'), ('未知', '未知')],
                                     validators=[DataRequired()])
    submit = SubmitField('预测')
