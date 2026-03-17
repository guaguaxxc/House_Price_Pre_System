"""
错误响应模块
================================================
提供统一的错误页面渲染函数，当发生错误时调用此函数返回友好的错误提示页面。
"""

from flask import render_template


def errorResponse(errorMsg):
    """
    渲染错误页面，并显示给定的错误信息。
    :param errorMsg: str - 需要向用户显示的错误描述信息
    :return: 渲染后的 error.html 页面，包含 errorMsg 变量
    """
    return render_template('error.html', errorMsg=errorMsg)
