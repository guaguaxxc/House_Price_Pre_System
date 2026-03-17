"""
CSV 数据导入脚本
================================================
将爬虫生成的 communities_data.csv 文件中的数据批量导入到数据库表 community_info 中。
使用 Flask 应用上下文和 SQLAlchemy ORM 进行批量插入，支持大文件分批处理，避免内存溢出，并统计导入结果。
"""
import csv
import os
from app import create_app
from extensions import db
from model.Community_info import Community_info


def store():
    """
    主导入函数：读取 CSV 文件，分批插入数据库。
    配置项：
        csv_path: CSV 文件路径（相对项目根目录）
        batch_size: 每批插入的记录数
    统计信息：
        total_count: 读取的总行数（不含表头）
        success_count: 成功插入的行数
        fail_count: 失败的行数（字段数错误等）
    """
    # ========== 配置项 ==========
    csv_path = 'anjuke_spider/communities_data.csv'  # CSV 文件路径
    batch_size = 500  # 每批插入的行数

    # ========== 初始化统计变量 ==========
    total_count = 0
    success_count = 0
    fail_count = 0
    batch_data = []  # 当前批次的数据缓存（字典列表）
    batch_num = 0

    # 创建 Flask 应用并获取应用上下文（确保数据库操作在正确的环境中）
    app = create_app()
    with app.app_context():
        try:
            # 检查 CSV 文件是否存在
            if not os.path.exists(csv_path):
                print(f"❌ CSV文件不存在：{os.path.abspath(csv_path)}")
                return

            # 以 utf-8-sig 编码打开（兼容 UTF-8 BOM）
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                next(reader)  # 跳过表头行

                # 定义字段名列表，顺序必须与 CSV 列顺序一致
                field_names = [
                    'city', 'community_name', 'price', 'address', 'community_link',
                    'property_type', 'ownership_type', 'completion_time', 'property_right_years', 'total_households',
                    'total_building_area', 'plot_ratio', 'greening_rate', 'building_type', 'business_district',
                    'unified_heating', 'water_supply_power', 'parking_spaces', 'property_fee', 'parking_fee',
                    'parking_management_fee', 'property_company', 'community_address', 'developer', 'sale_houses',
                    'rent_houses'
                ]

                # 逐行处理数据
                for row_idx, row in enumerate(reader, start=2):  # 行号从2开始（表头占第1行）
                    total_count += 1

                    # 校验字段数（必须为26列）
                    if len(row) != len(field_names):
                        print(f"⚠️ 第{row_idx}行：字段数错误（预期{len(field_names)}个，实际{len(row)}个），跳过")
                        fail_count += 1
                        continue

                    # 数据清洗：去除两端空格，空字符串转为 None（便于数据库插入）
                    cleaned_row = [cell.strip() or None for cell in row]
                    # 将列表转换为字典，键为字段名
                    row_dict = dict(zip(field_names, cleaned_row))
                    batch_data.append(row_dict)
                    # 当缓存达到批量大小时，执行批量插入
                    if len(batch_data) >= batch_size:
                        batch_num += 1
                        print(f"\n📦 开始提交第 {batch_num} 批数据（{len(batch_data)} 条）")
                        try:
                            # 使用 SQLAlchemy 的批量插入映射（速度快，直接映射字典到模型）
                            db.session.bulk_insert_mappings(Community_info, batch_data)
                            db.session.commit()
                            success_count += len(batch_data)
                            print(f"✅ 第 {batch_num} 批提交成功，累计成功 {success_count} 条")
                        except Exception as e:
                            db.session.rollback()
                            print(f"❌ 第 {batch_num} 批提交失败：{e}")
                            fail_count += len(batch_data)
                        finally:
                            batch_data = []  # 清空缓存

                # 处理最后一批不足 batch_size 的数据
                if batch_data:
                    batch_num += 1
                    print(f"\n📦 提交最后一批数据（{len(batch_data)} 条）")
                    try:
                        db.session.bulk_insert_mappings(Community_info, batch_data)
                        db.session.commit()
                        success_count += len(batch_data)
                        print(f"✅ 最后一批提交成功，累计成功 {success_count} 条")
                    except Exception as e:
                        db.session.rollback()
                        print(f"❌ 最后一批提交失败：{e}")
                        fail_count += len(batch_data)

            # ========== 导入结果汇总 ==========
            fail_count = total_count - success_count  # 重新计算失败数（更准确）
            print("\n" + "=" * 50)
            print(f"📊 CSV导入汇总：")
            print(f"总处理行数：{total_count}")
            print(f"成功插入：{success_count}")
            print(f"失败行数：{fail_count}")
            print(f"成功率：{success_count / total_count * 100:.2f}%" if total_count > 0 else "0%")
            print("=" * 50)

        except FileNotFoundError:
            print(f"❌ 找不到CSV文件：{csv_path}")
        except MemoryError:
            print(f"❌ 内存不足：建议减小batch_size（当前{batch_size}）")
        except Exception as e:
            print(f"❌ 导入过程异常：{e}")


if __name__ == "__main__":
    store()
