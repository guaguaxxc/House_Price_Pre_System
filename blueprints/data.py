"""
数据管理蓝图模块
================================================
提供小区数据的表格展示、详情查看、添加、编辑、删除功能。
所有操作基于 Community_info 模型，并通过 Flask-WTF 表单进行数据验证。
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from model.Community_info import Community_info
from forms.community import CommunityForm
from extensions import db

# 创建数据管理蓝图，URL前缀为 /data
data_bp = Blueprint('data', __name__, url_prefix='/data')


@data_bp.route('/table', methods=['GET', 'POST'])
def table():
    """
    展示小区数据表格，支持按城市、小区名称、地址进行搜索。
    请求参数:
        - GET: searchWord (可选) - 搜索关键词
        - POST: searchWord (表单) - 搜索关键词
    返回渲染后的表格页面，最多显示1000条记录以避免加载过慢。
    """
    # 获取当前登录用户名
    username = session.get('username')

    # 获取搜索关键词：优先从 GET 参数获取，其次从 POST 表单获取
    search_word = request.args.get('searchWord', '').strip() or request.form.get('searchWord', '').strip()

    # 构建基础查询
    query = Community_info.query

    # 如果有关键词，则在 city、community_name、community_address 三个字段中模糊搜索
    if search_word:
        query = query.filter(
            (Community_info.city.contains(search_word)) |
            (Community_info.community_name.contains(search_word)) |
            (Community_info.community_address.contains(search_word))
        )

    # 限制返回条数，避免一次性加载过多数据导致性能问题
    communities = query.limit(1000).all()

    return render_template('tableData.html',
                           username=username,
                           communities=communities,
                           search_word=search_word)


@data_bp.route('/detail/<int:id>')
def detail(id):
    """
    查看单个小区的详细信息。
    :param id: 小区记录的主键ID
    :return: 详情页面，若ID不存在则返回404
    """
    username = session.get('username')
    # 使用 get_or_404，若记录不存在自动返回404页面
    community = Community_info.query.get_or_404(id)
    return render_template('detail.html', username=username, community=community)


@data_bp.route('/add', methods=['GET', 'POST'])
def add():
    """
    添加新小区信息。
    GET 请求：显示空表单。
    POST 请求：验证表单数据，若通过则保存到数据库，并重定向到表格页面。
    """
    username = session.get('username')
    form = CommunityForm()  # 创建表单实例

    if form.validate_on_submit():
        # 表单验证通过，创建新模型实例
        community = Community_info()
        # 将表单数据批量填充到模型对象
        form.populate_obj(community)
        # 添加到数据库会话并提交
        db.session.add(community)
        db.session.commit()
        flash('小区信息添加成功！', 'success')  # 闪现成功消息
        # 重定向到表格页面，并自动搜索刚添加的小区名称
        return redirect(url_for('data.table', searchWord=community.community_name))

    # GET请求或验证失败时，显示添加页面
    return render_template('addHouse.html', username=username, form=form)


@data_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    """
    编辑现有小区信息。
    :param id: 要编辑的小区主键ID
    GET 请求：根据ID加载现有数据并填充表单。
    POST 请求：验证表单数据，若通过则更新数据库，并重定向。
    """
    username = session.get('username')
    # 获取要编辑的记录，不存在则404
    community = Community_info.query.get_or_404(id)
    # 创建表单，并用当前记录数据预填充
    form = CommunityForm(obj=community)

    if form.validate_on_submit():
        # 表单验证通过，将表单数据更新到模型对象
        form.populate_obj(community)
        # 提交更改
        db.session.commit()
        flash('小区信息更新成功！', 'success')
        return redirect(url_for('data.table', searchWord=community.community_name))

    # GET请求或验证失败时，显示编辑页面
    return render_template('editHouse.html', username=username, form=form, community=community)


@data_bp.route('/delete/<int:id>')
def delete(id):
    """
    删除指定小区信息。
    :param id: 要删除的小区主键ID
    删除后重定向到表格页面，并闪现删除成功消息。
    """
    community = Community_info.query.get_or_404(id)
    name = community.community_name
    db.session.delete(community)
    db.session.commit()
    flash(f'小区“{name}”删除成功！', 'success')
    return redirect(url_for('data.table', searchWord=name))
