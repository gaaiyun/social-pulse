import pandas as pd
import numpy as np

# 内容数据
content_data = pd.DataFrame({
    'content_id': range(1, 101),
    'title': [f'精彩{i}分享' for i in range(1, 101)],
    'platform': np.random.choice(['微信', '微博', '抖音', '小红书'], 100),
    'reads': np.random.randint(1000, 100000, 100),
    'likes': np.random.randint(100, 10000, 100),
    'comments': np.random.randint(10, 1000, 100),
    'shares': np.random.randint(5, 500, 100),
    'publish_time': pd.date_range('2024-01-01', periods=100, freq='2H').strftime('%Y-%m-%d %H:%M:%S'),
    'content_type': np.random.choice(['图文', '视频', '直播'], 100),
    'keywords': np.random.choice(['科技,AI', '生活，日常', '美食，探店', '旅行，风景'], 100)
})
content_data.to_csv('sample_data/content_sample.csv', index=False, encoding='utf-8-sig')

# 粉丝数据
dates = pd.date_range('2024-01-01', periods=30, freq='D')
fan_data = pd.DataFrame({
    'date': dates.strftime('%Y-%m-%d'),
    'new_fans': np.random.randint(50, 500, 30),
    'unfollows': np.random.randint(10, 100, 30),
    'total_fans': np.cumsum(np.random.randint(50, 500, 30)) + 10000,
    'interactions': np.random.randint(100, 5000, 30),
    'gender': np.random.choice(['男', '女'], 30),
    'age': np.random.randint(18, 60, 30),
    'city': np.random.choice(['北京', '上海', '广州', '深圳', '杭州'], 30)
})
fan_data.to_csv('sample_data/fan_sample.csv', index=False, encoding='utf-8-sig')

# 评论数据
comments = [
    '太棒了，非常喜欢！', '一般般吧', '质量很差，失望', '超级好用，推荐！',
    '还不错', '完全不值', '很好的体验', '态度太差了',
    '物流很快', '用了一次就坏了', '会回购的', '客服很耐心',
    '包装精美', '性价比很高', '失望透顶', '超出预期',
    '平平无奇', '强烈推荐', '不要买', '非常满意'
]
comment_data = pd.DataFrame({
    'comment': np.random.choice(comments, 200),
    'date': pd.to_datetime(np.random.choice(dates, 200)).strftime('%Y-%m-%d'),
    'content_id': np.random.randint(1, 101, 200),
    'platform': np.random.choice(['微信', '微博', '抖音', '小红书'], 200)
})
comment_data.to_csv('sample_data/comment_sample.csv', index=False, encoding='utf-8-sig')

print('Success: Sample data generated')
print(f'  - content_sample.csv: {len(content_data)} rows')
print(f'  - fan_sample.csv: {len(fan_data)} rows')
print(f'  - comment_sample.csv: {len(comment_data)} rows')
