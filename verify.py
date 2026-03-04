"""
项目验证脚本 - 验证所有模块正常工作
"""

import pandas as pd
from content_analyzer import ContentAnalyzer
from fan_analyzer import FanAnalyzer
from sentiment_analyzer import SentimentAnalyzer

print("=" * 50)
print("社交媒体分析平台 - 模块验证")
print("=" * 50)
print()

# 测试加载示例数据
print("加载示例数据...")
content = pd.read_csv('sample_data/content_sample.csv')
fan = pd.read_csv('sample_data/fan_sample.csv')
comment = pd.read_csv('sample_data/comment_sample.csv')
print(f"  [OK] content_sample.csv: {len(content)} 条")
print(f"  [OK] fan_sample.csv: {len(fan)} 条")
print(f"  [OK] comment_sample.csv: {len(comment)} 条")
print()

# 测试各模块
print("测试 ContentAnalyzer...")
ca = ContentAnalyzer(content)
metrics = ca.performance_metrics()
viral = ca.identify_viral_content()
print(f"  [OK] 表现指标：{len(metrics)} 条记录")
print(f"  [OK] 爆款内容：{len(viral)} 条")
print()

print("测试 FanAnalyzer...")
fa = FanAnalyzer(fan)
growth = fa.calculate_growth_metrics()
demo = fa.analyze_demographics()
print(f"  [OK] 总粉丝数：{growth['total_fans']:,}")
print(f"  [OK] 净增粉丝：{growth['net_new_fans']:,}")
print(f"  [OK] 性别分布：{demo['gender_dist']}")
print()

print("测试 SentimentAnalyzer...")
sa = SentimentAnalyzer(comment)
comment_df = sa.analyze_batch()
dist = sa.sentiment_distribution()
print(f"  [OK] 平均情感分：{dist['avg_score']:.2f}")
print(f"  [OK] 积极评论：{dist['positive']} ({dist['positive_pct']:.1f}%)")
print(f"  [OK] 消极评论：{dist['negative']} ({dist['negative_pct']:.1f}%)")
print()

print("=" * 50)
print("[SUCCESS] 所有模块验证成功！")
print("=" * 50)
print()
print("下一步:")
print("  1. 运行 start.bat 启动应用")
print("  2. 或使用命令：streamlit run dashboard.py")
print("  3. 浏览器访问：http://localhost:8501")
