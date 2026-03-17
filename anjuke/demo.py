"""
安居客小区信息爬虫
"""
import csv
import time
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from bs4 import BeautifulSoup

# ========================== 全局配置 ==========================
# 请求头配置（模拟浏览器访问）
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0',
    'Referer': 'https://member.anjuke.com/',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
}

# Cookies配置（需要定期更新）
COOKIES = {
    'ajkAuthTicket': 'TT=3f67c23d85c369b7018fcb4e1418466f&TS=1738219179437&PBODY=IotzzfNhkTJKGH_LuUrSfcNHUGin1wBsHjAQYBL3k0USZDHrUxL6RQUv1ZsFPDHjxvQl0uvU2zSgIEdSFCHUc7wYEf4slKV2U2F9rwNnp6xHgufTxMgdYWZEob_Tep-poDqBMbQQgayOQhsaRgVjw8K8ut3QqqMfPgYGpKJJBHw&VER=2&CUID=fzgJGetduRhII81NXadF-HKyO1Hvr8W-',
    'ctid': '24',
}

# 重试策略配置
RETRY_STRATEGY = Retry(
    total=3,  # 最大重试次数
    backoff_factor=1,  # 重试等待时间因子
    status_forcelist=[500, 502, 503, 504],  # 需要重试的状态码
    allowed_methods=frozenset(['GET', 'POST'])  # 允许重试的HTTP方法
)

# 其他配置
BASE_URL = 'https://foshan.anjuke.com/community/p{page}/'  # 分页URL模板
REQUEST_DELAY = 0.5  # 请求间隔时间（秒），防止被封禁
CSV_HEADERS = [  # CSV文件表头
    '小区名称', '价格', '地址', '小区链接',
    '物业类型', '权属类别', '竣工时间', '产权年限', '总户数', '总建筑面积', '容积率',
    '绿化率', '建筑类型', '所属商圈', '统一供暖', '供水供电', '停车位', '物业费',
    '停车费', '车位管理费', '物业公司', '小区地址', '开发商', '在售房源', '在租房源'
]


# ========================== 工具函数 ==========================
def create_session():
    """
    创建带有重试策略的请求会话
    返回：
        requests.Session - 配置好的会话对象
    """
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=RETRY_STRATEGY)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session


def safe_get_text(element, selector, default='N/A'):
    """
    安全获取元素文本内容
    参数：
        element: BeautifulSoup对象 - 父元素
        selector: str - CSS选择器
        default: str - 默认返回值
    返回：
        str - 元素的文本内容或默认值
    """
    target = element.select_one(selector)
    return target.get_text(strip=True) if target else default


# ========================== 主程序 ==========================
def main():
    # 用户输入
    community_count = int(input("请输入需要抓取的小区数量："))

    # 初始化会话
    session = create_session()

    # 准备CSV文件
    with open('communities.csv', mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(CSV_HEADERS)

        page_count = (community_count // 25) + (1 if community_count % 25 else 0)
        collected = 0  # 已收集数量

        # 分页抓取
        for current_page in range(1, page_count + 1):
            print(f"\n➤ 正在处理第 {current_page}/{page_count} 页...")

            # 获取列表页
            try:
                list_url = BASE_URL.format(page=current_page)
                response = session.get(
                    list_url,
                    headers=HEADERS,
                    cookies=COOKIES,
                    timeout=10
                )
                response.raise_for_status()
            except Exception as e:
                print(f"⚠️ 列表页请求失败: {e}")
                continue

            # 解析小区列表
            list_soup = BeautifulSoup(response.text, 'html.parser')
            communities = list_soup.find_all('a', class_='li-row')

            # 遍历每个小区
            for community in communities:
                if collected >= community_count:
                    break

                # 提取基本信息
                name = safe_get_text(community, 'div.li-title')
                price = safe_get_text(community, 'div.community-price')
                address = safe_get_text(community, 'div.props')
                link = community.get('href', '')
                print(f"\n▌ 正在处理小区：{name}")

                # 获取详情页
                try:
                    detail_response = session.get(
                        link,
                        headers=HEADERS,
                        cookies=COOKIES,
                        timeout=15
                    )
                    detail_response.raise_for_status()
                except Exception as e:
                    print(f"  ⚠️ 详情页请求失败: {e}")
                    continue

                # 解析详情页
                detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
                details = []

                # 提取主要信息
                for index in range(14):  # 0-13对应预设的标签
                    value = safe_get_text(detail_soup, f'div.value.value_{index}')
                    details.append(value)

                # 提取额外信息
                extra_info = {
                    '停车费': 'N/A',
                    '车位管理费': 'N/A',
                    '物业公司': 'N/A',
                    '小区地址': 'N/A',
                    '开发商': 'N/A'
                }
                for column in detail_soup.find_all('div', class_='column-1'):
                    label = safe_get_text(column, 'div.label')
                    value = safe_get_text(column, 'div.value')
                    for key in extra_info:
                        if key in label:
                            extra_info[key] = value

                # 提取房源信息
                sale = detail_soup.find('div', class_='sale')
                rent = detail_soup.find('div', class_='rent')
                sale_info = f"{safe_get_text(sale, 'i.source-number')} {safe_get_text(sale, 'i.source-unit')}" if sale else 'N/A'
                rent_info = f"{safe_get_text(rent, 'i.source-number')} {safe_get_text(rent, 'i.source-unit')}" if rent else 'N/A'

                # 构建完整数据行
                row = [
                    name, price, address, link,
                    *details,
                    *extra_info.values(),
                    sale_info, rent_info
                ]

                # 写入CSV
                writer.writerow(row)
                collected += 1
                print(f"  ✅ 已保存 {collected}/{community_count} - {name}")

                # 请求间隔
                time.sleep(REQUEST_DELAY)

    print("\n🎉 数据抓取完成！结果已保存到 communities.csv")


if __name__ == '__main__':
    main()
