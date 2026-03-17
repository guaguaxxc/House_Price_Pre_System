import csv
import os
from utils.query import query

def store():
    # ========== 配置项（根据数据量调整） ==========
    csv_path = 'anjuke_spider/communities_data.csv'
    batch_size = 500  # 批量大小
    insert_sql = '''
    INSERT INTO community_info(
        city,community_name,price,address,community_link,
        property_type,ownership_type,completion_time,property_right_years,total_households,
        total_building_area,plot_ratio,greening_rate,building_type,business_district,
        unified_heating,water_supply_power,parking_spaces,property_fee,parking_fee,
        parking_management_fee,property_company,community_address,developer,sale_houses,rent_houses
    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    '''

    # ========== 初始化统计 ==========
    total_count = 0    # 总行数
    success_count = 0  # 成功行数
    fail_count = 0     # 失败行数
    batch_data = []    # 批量数据缓存
    batch_num = 0      # 批次号

    # ========== 读取CSV并批量插入 ==========
    try:
        # 检查CSV文件是否存在
        if not os.path.exists(csv_path):
            print(f"❌ CSV文件不存在：{os.path.abspath(csv_path)}")
            return

        # 读取CSV（utf-8-sig兼容中文）
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            readerCsv = csv.reader(f)
            next(readerCsv)  # 跳过表头

            for row_idx, h in enumerate(readerCsv, start=2):  # 行号从2开始
                total_count += 1

                # 1. 校验字段数（避免索引越界）
                if len(h) != 26:
                    print(f"⚠️ 第{row_idx}行：字段数错误（预期26个，实际{len(h)}个），跳过")
                    fail_count += 1
                    continue

                # 2. 数据清洗（空值转None，去空格）
                clean_row = [cell.strip() or None for cell in h]
                batch_data.append(clean_row)

                # 3. 达到批量大小则提交
                if len(batch_data) >= batch_size:
                    batch_num += 1
                    print(f"\n📦 开始提交第 {batch_num} 批数据（{len(batch_data)} 条）")
                    # 调用批量插入
                    query(insert_sql, batch_data, type='no_select', batch=True)
                    # 更新统计
                    success_count += len(batch_data)
                    print(f"✅ 第 {batch_num} 批提交成功，累计成功 {success_count} 条")
                    # 清空缓存
                    batch_data = []

            # 4. 提交剩余的最后一批数据（不足batch_size的部分）
            if batch_data:
                batch_num += 1
                print(f"\n📦 提交最后一批数据（{len(batch_data)} 条）")
                query(insert_sql, batch_data, type='no_select', batch=True)
                success_count += len(batch_data)
                print(f"✅ 最后一批提交成功，累计成功 {success_count} 条")

        # ========== 导入汇总 ==========
        fail_count = total_count - success_count  # 重新计算失败数（更准确）
        print("\n" + "="*50)
        print(f"📊 大数据量CSV导入汇总：")
        print(f"总处理行数：{total_count}")
        print(f"成功插入：{success_count}")
        print(f"失败行数：{fail_count}")
        print(f"成功率：{success_count/total_count*100:.2f}%" if total_count > 0 else "0%")
        print("="*50)

    except FileNotFoundError:
        print(f"❌ 找不到CSV文件：{csv_path}")
    except MemoryError:
        print(f"❌ 内存不足：建议减小batch_size（当前{batch_size}）")
    except Exception as e:
        print(f"❌ 导入过程异常：{e}")

# 执行批量导入
if __name__ == "__main__":
    store()