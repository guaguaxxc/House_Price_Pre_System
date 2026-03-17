from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from model.Community_info import Community_info
from forms.community import CommunityForm
from extensions import db

data_bp = Blueprint('data', __name__, url_prefix='/data')


@data_bp.route('/table', methods=['GET', 'POST'])
def table():
    username = session.get('username')
    search_word = request.args.get('searchWord', '').strip() or request.form.get('searchWord', '').strip()
    query = Community_info.query
    if search_word:
        query = query.filter(
            (Community_info.city.contains(search_word)) |
            (Community_info.community_name.contains(search_word)) |
            (Community_info.community_address.contains(search_word))
        )
    communities = query.limit(1000).all()
    return render_template('tableData.html', username=username, communities=communities, search_word=search_word)


@data_bp.route('/detail/<int:id>')
def detail(id):
    username = session.get('username')
    community = Community_info.query.get_or_404(id)
    return render_template('detail.html', username=username, community=community)


@data_bp.route('/add', methods=['GET', 'POST'])
def add():
    username = session.get('username')
    form = CommunityForm()
    if form.validate_on_submit():
        community = Community_info()
        form.populate_obj(community)
        db.session.add(community)
        db.session.commit()
        flash('小区信息添加成功！', 'success')
        return redirect(url_for('data.table', searchWord=community.community_name))
    return render_template('addHouse.html', username=username, form=form)


@data_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    username = session.get('username')
    community = Community_info.query.get_or_404(id)
    form = CommunityForm(obj=community)
    if form.validate_on_submit():
        form.populate_obj(community)
        db.session.commit()
        flash('小区信息更新成功！', 'success')
        return redirect(url_for('data.table', searchWord=community.community_name))
    return render_template('editHouse.html', username=username, form=form, community=community)


@data_bp.route('/delete/<int:id>')
def delete(id):
    community = Community_info.query.get_or_404(id)
    name = community.community_name
    db.session.delete(community)
    db.session.commit()
    flash(f'小区“{name}”删除成功！', 'success')
    return redirect(url_for('data.table', searchWord=name))
