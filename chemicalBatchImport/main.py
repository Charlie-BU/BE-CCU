from math import isnan
import pandas as pd
from models import *


def importFromExcel(path):
    df = pd.read_excel(path)
    for _, row in df.iterrows():
        # 处理纯度
        try:
            purity = float(row.get('纯度', 0))
            if isnan(purity):
                purity = None
        except ValueError:
            purity = None
        # 处理分类
        try:
            type = 1 if "无机" in row["分类"] else 2
        except TypeError:
            type = None
        # 处理危险性
        dangerLevel = [5] if row['是否易制毒'] == "是" else []

        chemical = Chemical(
            name=row['药品名称'],
            CAS=row['CAS'],
            type=type,
            dangerLevel=dangerLevel,
            purity=purity,
            amount=1,
            specification=row.get('规格', None),
            site=row.get('位置', None),
            registerIds=[],
            responsorId=1,
        )
        session.add(chemical)
    session.commit()
    print("数据导入完成！")

