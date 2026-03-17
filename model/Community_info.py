"""
小区信息模型
================================================
对应数据库中的 community_info 表，存储从安居客爬取的小区详细信息。
所有字段均使用 String(255) 类型，因为原始数据可能包含单位、描述等非纯数值内容。
"""

from extensions import db


class Community_info(db.Model):
    """
    小区信息模型类，映射数据库表 community_info。
    包含小区的基本信息、物业详情、价格、房源数量等字段。
    """
    __tablename__ = 'community_info'  # 数据库表名

    # ================= 核心标识字段 =================
    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
        comment="自增主键，唯一标识每条小区记录"
    )
    city = db.Column(
        db.String(255),
        nullable=True,
        comment="城市名称，如'北京'、'上海'"
    )
    community_name = db.Column(
        db.String(255),
        nullable=True,
        comment="小区名称"
    )
    price = db.Column(
        db.String(255),
        nullable=True,
        comment="小区均价（字符串形式，可能包含单位，如'65000元/㎡'）"
    )
    address = db.Column(
        db.String(255),
        nullable=True,
        comment="小区简要地址（从列表页提取）"
    )
    community_link = db.Column(
        db.String(255),
        nullable=True,
        comment="小区详情页的URL链接"
    )

    # ================= 物业与产权信息 =================
    property_type = db.Column(
        db.String(255),
        nullable=True,
        comment="物业类型，如'住宅'、'公寓'、'商铺'等"
    )
    ownership_type = db.Column(
        db.String(255),
        nullable=True,
        comment="权属类别，如'商品房'、'经济适用房'等"
    )
    completion_time = db.Column(
        db.String(255),
        nullable=True,
        comment="竣工时间，可能为年份或具体日期（如'2010年'）"
    )
    property_right_years = db.Column(
        db.String(255),
        nullable=True,
        comment="产权年限，通常为'70年'、'50年'等字符串"
    )
    total_households = db.Column(
        db.String(255),
        nullable=True,
        comment="总户数，可能包含单位'户'，如'1200户'"
    )
    total_building_area = db.Column(
        db.String(255),
        nullable=True,
        comment="总建筑面积，可能包含单位'㎡'，如'150000㎡'"
    )
    plot_ratio = db.Column(
        db.String(255),
        nullable=True,
        comment="容积率，如'2.5'"
    )
    greening_rate = db.Column(
        db.String(255),
        nullable=True,
        comment="绿化率，如'30%'"
    )
    building_type = db.Column(
        db.String(255),
        nullable=True,
        comment="建筑类型，如'高层'、'小高层'、'多层'等，可能组合如'高层/小高层'"
    )
    business_district = db.Column(
        db.String(255),
        nullable=True,
        comment="所属商圈，如'国贸'、'中关村'"
    )
    unified_heating = db.Column(
        db.String(255),
        nullable=True,
        comment="是否统一供暖，存储'是'、'否'或'未知'"
    )
    water_supply_power = db.Column(
        db.String(255),
        nullable=True,
        comment="供水供电类型，如'民用'、'商用'或'未知'"
    )

    # ================= 停车与物业费用 =================
    parking_spaces = db.Column(
        db.String(255),
        nullable=True,
        comment="停车位数量，可能包含单位'个'，如'500个'"
    )
    property_fee = db.Column(
        db.String(255),
        nullable=True,
        comment="物业费，可能包含单位'元/㎡·月'，如'3.5元/㎡·月'"
    )
    parking_fee = db.Column(
        db.String(255),
        nullable=True,
        comment="停车费，可能包含单位'元/月'，如'300元/月'"
    )
    parking_management_fee = db.Column(
        db.String(255),
        nullable=True,
        comment="车位管理费，可能包含单位'元/月'"
    )
    property_company = db.Column(
        db.String(255),
        nullable=True,
        comment="物业公司名称"
    )
    community_address = db.Column(
        db.String(255),
        nullable=True,
        comment="小区详细地址（从详情页提取）"
    )
    developer = db.Column(
        db.String(255),
        nullable=True,
        comment="开发商名称"
    )

    # ================= 房源数量 =================
    sale_houses = db.Column(
        db.String(255),
        nullable=True,
        comment="当前在售房源数量，可能包含单位'套'"
    )
    rent_houses = db.Column(
        db.String(255),
        nullable=True,
        comment="当前在租房源数量，可能包含单位'套'"
    )
