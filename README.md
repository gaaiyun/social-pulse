> **维护状态说明**：本仓库当前是 AI 辅助生成的初始脚手架，未在生产环境持续打磨。代码可作为参考与起点，使用前请自行核对接口、依赖与边界条件。如果你打算接手维护、把它合并到其他项目，或者发现 bug，欢迎开 issue 或 PR。
# 社交媒体分析平台 📊

一个功能强大的社交媒体数据分析和内容优化平台，支持多平台数据整合、智能分析和运营优化建议。

## ✨ 核心功能

### 1. 多平台整合
- 📱 支持微信、微博、抖音、小红书四大平台
- 🔄 统一数据格式，一站式管理
- 📊 跨平台数据对比分析

### 2. 内容分析
- 🔥 爆款内容特征识别
- 📈 阅读量、点赞、转发深度分析
- ⏰ 最佳发布时间建议
- 📝 内容类型表现对比

### 3. 粉丝分析
- 📊 粉丝增长趋势追踪
- ⏰ 粉丝活跃时段分析
- 👤 粉丝画像（年龄、性别、地域）
- 📈 留存率分析

### 4. 情感分析
- 💬 评论情感倾向分析
- 📊 情感分布可视化
- 📈 情感趋势追踪
- ⚠️ 负面反馈预警

### 5. 竞品对比
- 📊 多维度账号对比
- 📱 平台间表现对比
- 📝 内容策略对比

### 6. 报告导出
- 📋 自动化运营报告生成
- 📥 支持 Markdown 格式导出
- 🎯 定制化报告章节

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Windows / macOS / Linux

### 安装步骤

1. **克隆项目**
```bash
cd social-media-analytics
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **运行应用**
```bash
streamlit run dashboard.py
```

4. **访问应用**
打开浏览器访问：http://localhost:8501

## 📁 项目结构

```
social-media-analytics/
├── dashboard.py              # 主界面
├── content_analyzer.py       # 内容分析模块
├── fan_analyzer.py          # 粉丝分析模块
├── sentiment_analyzer.py    # 情感分析模块
├── requirements.txt         # 依赖列表
├── README.md               # 项目说明
├── tests/                  # 单元测试
│   ├── test_content.py
│   ├── test_fan.py
│   └── test_sentiment.py
└── sample_data/            # 示例数据
    ├── content_sample.csv
    ├── fan_sample.csv
    └── comment_sample.csv
```

## 📊 数据格式

### 内容数据 (content_data.csv)
```csv
content_id,title,platform,reads,likes,comments,shares,publish_time,content_type,keywords
1,精彩分享，微信，50000,3000,200,150,2024-01-01 10:00:00，图文，科技,AI
2,视频展示，抖音，100000,8000,500,400,2024-01-01 14:00:00，视频，生活，日常
```

### 粉丝数据 (fan_data.csv)
```csv
date,new_fans,unfollows,total_fans,interactions,gender,age,city
2024-01-01,200,50,10000,1500，男，25，北京
2024-01-02,250,40,10200,1600，女，30，上海
```

### 评论数据 (comment_data.csv)
```csv
comment,date,content_id,platform
太棒了，非常喜欢！,2024-01-01,1，微信
一般般吧，2024-01-01,2，抖音
```

## 🎯 使用指南

### 1. 数据导入
- 使用示例数据快速体验
- 上传 CSV 文件导入自有数据
- 支持多平台数据混合分析

### 2. 内容分析
- 查看内容表现 TOP20
- 分析爆款内容特征
- 获取最佳发布时间建议

### 3. 粉丝分析
- 追踪粉丝增长趋势
- 分析粉丝活跃时段
- 了解粉丝画像特征

### 4. 情感分析
- 自动分析评论情感
- 查看情感分布和趋势
- 识别负面反馈

### 5. 生成报告
- 选择报告章节
- 一键生成运营报告
- 下载 Markdown 格式

## 🧪 测试

### 运行单元测试
```bash
# 安装测试依赖
pip install pytest pytest-cov

# 运行所有测试
pytest tests/ -v

# 查看测试覆盖率
pytest tests/ --cov=. --cov-report=html
```

### 测试要求
- ✅ 测试覆盖率 > 70%
- ✅ 所有核心功能测试通过
- ✅ UI 交互验证通过

## 🔧 技术栈

- **前端界面**: Streamlit
- **数据处理**: Pandas, NumPy
- **数据可视化**: Plotly
- **情感分析**: SnowNLP
- **测试框架**: Pytest

## 📝 API 集成（扩展功能）

### 微信公号 API
```python
# 示例：从微信公号导入数据
def import_wechat_data(appid, secret):
    # 获取 accessToken
    # 调用公众号 API
    # 返回 DataFrame
    pass
```

### 微博 API
```python
# 示例：从微博导入数据
def import_weibo_data(access_token):
    # 调用微博 API
    # 解析响应
    # 返回 DataFrame
    pass
```

### 抖音 API
```python
# 示例：从抖音导入数据
def import_douyin_data(access_token):
    # 调用抖音开放平台 API
    # 获取视频数据
    # 返回 DataFrame
    pass
```

### 小红书 API
```python
# 示例：从小红书导入数据
def import_xiaohongshu_data(api_key):
    # 调用小红书 API
    # 获取笔记数据
    # 返回 DataFrame
    pass
```

## 💡 最佳实践

### 1. 数据质量
- 确保数据格式正确
- 定期检查数据完整性
- 清理异常值和重复数据

### 2. 分析频率
- 每日：查看基础指标
- 每周：深度内容分析
- 每月：生成完整报告

### 3. 优化建议
- 根据爆款特征调整内容策略
- 在最佳发布时间发布
- 及时回应负面评论

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 📞 联系方式

如有问题或建议，请提交 Issue。

---

**Made with ❤️ for Social Media Operators**
