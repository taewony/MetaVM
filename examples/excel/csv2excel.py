#!/usr/bin/env python3
import pandas as pd

# CSV 파일 읽기
df = pd.read_csv('file3.csv')

# Excel 파일로 저장 (인덱스 없이 저장)
df.to_excel('file3.xlsx', index=False, engine='openpyxl')