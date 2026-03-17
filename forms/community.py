from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField, IntegerField, SelectField
from wtforms.validators import DataRequired, Optional, NumberRange, Length


class CommunityForm(FlaskForm):
    city = StringField('城市', validators=[DataRequired(), Length(max=50)])
    community_name = StringField('小区名称', validators=[DataRequired(), Length(max=100)])
    price = FloatField('单价(元/㎡)', validators=[Optional(), NumberRange(min=0)])
    address = StringField('地址', validators=[Optional(), Length(max=200)])
    community_link = StringField('链接', validators=[Optional(), Length(max=200)])
    property_type = StringField('物业类型', validators=[Optional(), Length(max=50)])
    ownership_type = StringField('产权性质', validators=[Optional(), Length(max=50)])
    completion_time = StringField('竣工时间', validators=[Optional(), Length(max=50)])
    property_right_years = StringField('产权年限', validators=[Optional(), Length(max=50)])
    total_households = IntegerField('总户数', validators=[Optional()])
    total_building_area = FloatField('总建筑面积(㎡)', validators=[Optional()])
    plot_ratio = FloatField('容积率', validators=[Optional(), NumberRange(min=0, max=10)])
    greening_rate = FloatField('绿化率(%)', validators=[Optional(), NumberRange(min=0, max=100)])
    building_type = StringField('建筑类型', validators=[Optional(), Length(max=100)])
    business_district = StringField('商圈', validators=[Optional(), Length(max=100)])
    unified_heating = StringField('集中供暖', validators=[Optional(), Length(max=10)])
    water_supply_power = StringField('水电类型', validators=[Optional(), Length(max=20)])
    parking_spaces = IntegerField('车位', validators=[Optional()])
    property_fee = FloatField('物业费(元/㎡·月)', validators=[Optional(), NumberRange(min=0)])
    parking_fee = FloatField('停车费(元/月)', validators=[Optional(), NumberRange(min=0)])
    parking_management_fee = FloatField('车位管理费(元/月)', validators=[Optional(), NumberRange(min=0)])
    property_company = StringField('物业公司', validators=[Optional(), Length(max=100)])
    community_address = StringField('社区地址', validators=[Optional(), Length(max=200)])
    developer = StringField('开发商', validators=[Optional(), Length(max=100)])
    sale_houses = IntegerField('在售房源(套)', validators=[Optional()])
    rent_houses = IntegerField('在租房源(套)', validators=[Optional()])
    submit = SubmitField('提交')
