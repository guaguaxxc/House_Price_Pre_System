from extensions import db


class Community_info(db.Model):
    __tablename__ = 'community_info'  # 对应数据库表名

    # 字段定义（所有String类型长度均改为255，保持字段含义不变）
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="自增主键")
    city = db.Column(db.String(255), nullable=True, comment="城市")
    community_name = db.Column(db.String(255), nullable=True, comment="小区名称")
    price = db.Column(db.String(255), nullable=True, comment="价格（含单位）")
    address = db.Column(db.String(255), nullable=True, comment="地址")
    community_link = db.Column(db.String(255), nullable=True, comment="小区链接")
    property_type = db.Column(db.String(255), nullable=True, comment="物业类型")
    ownership_type = db.Column(db.String(255), nullable=True, comment="权属类别")
    completion_time = db.Column(db.String(255), nullable=True, comment="竣工时间")
    property_right_years = db.Column(db.String(255), nullable=True, comment="产权年限")
    total_households = db.Column(db.String(255), nullable=True, comment="总户数")
    total_building_area = db.Column(db.String(255), nullable=True, comment="总建筑面积")
    plot_ratio = db.Column(db.String(255), nullable=True, comment="容积率")
    greening_rate = db.Column(db.String(255), nullable=True, comment="绿化率")
    building_type = db.Column(db.String(255), nullable=True, comment="建筑类型")
    business_district = db.Column(db.String(255), nullable=True, comment="所属商圈")
    unified_heating = db.Column(db.String(255), nullable=True, comment="统一供暖")
    water_supply_power = db.Column(db.String(255), nullable=True, comment="供水供电")
    parking_spaces = db.Column(db.String(255), nullable=True, comment="停车位")
    property_fee = db.Column(db.String(255), nullable=True, comment="物业费")
    parking_fee = db.Column(db.String(255), nullable=True, comment="停车费")
    parking_management_fee = db.Column(db.String(255), nullable=True, comment="车位管理费")
    property_company = db.Column(db.String(255), nullable=True, comment="物业公司")
    community_address = db.Column(db.String(255), nullable=True, comment="小区地址")
    developer = db.Column(db.String(255), nullable=True, comment="开发商")
    sale_houses = db.Column(db.String(255), nullable=True, comment="在售房源")
    rent_houses = db.Column(db.String(255), nullable=True, comment="在租房源")