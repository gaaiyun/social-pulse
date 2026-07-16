"""
社交媒体分析工具 - 主界面
Social Media Analytics Dashboard

多平台数据整合、内容分析、粉丝分析、情感分析一体化平台
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os

# 导入自定义模块
from content_analyzer import ContentAnalyzer
from fan_analyzer import FanAnalyzer
from sentiment_analyzer import SentimentAnalyzer


# 页面配置
st.set_page_config(
    page_title="社交媒体分析平台",
    page_icon="bar_chart",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 样式
st.markdown("""
<style>
.main-header {
    font-size: 2.5rem;
    font-weight: bold;
    color: #1f77b4;
    text-align: center;
    margin-bottom: 1rem;
}
.metric-card {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)


def generate_sample_data():
    """生成示例数据"""
    # 内容数据
    content_data = pd.DataFrame({
        'content_id': range(1, 101),
        'title': [f'精彩{i} 分享' for i in range(1, 101)],
        'platform': np.random.choice(['微信', '微博', '抖音', '小红书'], 100),
        'reads': np.random.randint(1000, 100000, 100),
        'likes': np.random.randint(100, 10000, 100),
        'comments': np.random.randint(10, 1000, 100),
        'shares': np.random.randint(5, 500, 100),
        'publish_time': pd.date_range('2024-01-01', periods=100, freq='h'),
        'content_type': np.random.choice(['图文', '视频', '直播'], 100),
        'keywords': np.random.choice(['科技,AI', '生活，日常', '美食，探店', '旅行，风景'], 100)
    })
    
    # 粉丝数据
    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    new_fans = np.random.randint(50, 500, 30)
    unfollows = np.random.randint(10, 100, 30)
    fan_data = pd.DataFrame({
        'date': dates,
        'new_fans': new_fans,
        'unfollows': unfollows,
        'total_fans': 10000 + np.cumsum(new_fans - unfollows),
        'interactions': np.random.randint(100, 5000, 30),
        'gender': np.random.choice(['男', '女'], 30),
        'age': np.random.randint(18, 60, 30),
        'city': np.random.choice(['北京', '上海', '广州', '深圳', '杭州'], 30)
    })
    
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
        'date': np.random.choice(dates, 200),
        'content_id': np.random.randint(1, 101, 200),
        'platform': np.random.choice(['微信', '微博', '抖音', '小红书'], 200)
    })
    
    return content_data, fan_data, comment_data


def main():
    """主函数"""
    
    # 标题
    st.markdown('<div class="main-header">社交媒体分析平台</div>', unsafe_allow_html=True)
    st.markdown("### 多平台数据整合 · 智能分析 · 运营优化")
    st.markdown("---")
    
    # 侧边栏
    st.sidebar.title("功能导航")
    
    # 功能选择
    features = st.sidebar.radio(
        "选择功能模块",
        ["数据概览", "内容分析", "粉丝分析", "情感分析", "竞品对比", "报告导出"],
        label_visibility="collapsed"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 数据管理")
    
    # 数据上传选项
    data_source = st.sidebar.radio(
        "数据来源",
        ["使用示例数据", "上传 CSV 文件"]
    )
    
    # 初始化数据
    content_data = None
    fan_data = None
    comment_data = None
    
    if data_source == "使用示例数据":
        content_data, fan_data, comment_data = generate_sample_data()
        st.sidebar.success("已加载示例数据")
    else:
        uploaded_content = st.sidebar.file_uploader("上传内容数据 (CSV)", type=['csv'])
        uploaded_fan = st.sidebar.file_uploader("上传粉丝数据 (CSV)", type=['csv'])
        uploaded_comment = st.sidebar.file_uploader("上传评论数据 (CSV)", type=['csv'])
        
        if uploaded_content:
            content_data = pd.read_csv(uploaded_content)
        if uploaded_fan:
            fan_data = pd.read_csv(uploaded_fan)
        if uploaded_comment:
            comment_data = pd.read_csv(uploaded_comment)
    
    # 平台筛选
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 数据筛选")
    platforms = st.sidebar.multiselect(
        "选择平台",
        ["微信", "微博", "抖音", "小红书"],
        default=["微信", "微博", "抖音", "小红书"]
    )
    
    # 根据平台筛选数据
    if content_data is not None and 'platform' in content_data.columns:
        content_data = content_data[content_data['platform'].isin(platforms)]
    if comment_data is not None and 'platform' in comment_data.columns:
        comment_data = comment_data[comment_data['platform'].isin(platforms)]
    
    # 主内容区域
    if features == "数据概览":
        show_overview(content_data, fan_data, comment_data)
    elif features == "内容分析":
        show_content_analysis(content_data)
    elif features == "粉丝分析":
        show_fan_analysis(fan_data)
    elif features == "情感分析":
        show_sentiment_analysis(comment_data)
    elif features == "竞品对比":
        show_competitor_analysis(content_data, fan_data)
    elif features == "报告导出":
        show_report_export(content_data, fan_data, comment_data)


def show_overview(content_data, fan_data, comment_data):
    """显示数据概览"""
    st.header("数据概览")
    
    if content_data is None or fan_data is None:
        st.warning("请先加载数据")
        return
    
    # 核心指标
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_reads = content_data['reads'].sum() if content_data is not None else 0
        st.metric("总阅读量", f"{total_reads:,}", delta=f"{total_reads/len(content_data):.0f}/篇")
    
    with col2:
        total_engagement = content_data[['likes', 'comments', 'shares']].sum().sum() if content_data is not None else 0
        st.metric("总互动量", f"{total_engagement:,}")
    
    with col3:
        current_fans = fan_data['total_fans'].iloc[-1] if len(fan_data) > 0 else 0
        st.metric("当前粉丝", f"{current_fans:,}")
    
    with col4:
        avg_sentiment = 0.65  # 默认值
        if comment_data is not None and len(comment_data) > 0:
            from sentiment_analyzer import SentimentAnalyzer
            analyzer = SentimentAnalyzer(comment_data.head(50))  # 只分析前 50 条
            analyzer.analyze_batch()
            avg_sentiment = analyzer.sentiment_distribution()['avg_score']
        st.metric("平均情感分", f"{avg_sentiment:.2f}")
    
    st.markdown("---")
    
    # 图表区域
    col1, col2 = st.columns(2)
    
    with col1:
        if content_data is not None:
            # 平台分布
            platform_dist = content_data['platform'].value_counts()
            fig = px.pie(
                values=platform_dist.values,
                names=platform_dist.index,
                title='各平台内容分布'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if content_data is not None:
            # 内容类型分布
            type_dist = content_data['content_type'].value_counts()
            fig = px.bar(
                x=type_dist.index,
                y=type_dist.values,
                title='内容类型分布',
                labels={'x': '类型', 'y': '数量'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # 趋势图
    st.subheader("粉丝增长趋势")
    if fan_data is not None:
        fan_analyzer = FanAnalyzer(fan_data)
        fig = fan_analyzer.create_growth_chart()
        st.plotly_chart(fig, use_container_width=True)


def show_content_analysis(content_data):
    """显示内容分析"""
    st.header("内容分析")
    
    if content_data is None:
        st.warning("请先加载内容数据")
        return
    
    # 初始化分析器
    analyzer = ContentAnalyzer(content_data)
    
    # 关键指标
    col1, col2, col3 = st.columns(3)
    
    with col1:
        avg_reads = content_data['reads'].mean()
        st.metric("平均阅读量", f"{avg_reads:,.0f}")
    
    with col2:
        metrics = analyzer.performance_metrics()
        avg_engagement = metrics['engagement_rate'].mean()
        st.metric("平均互动率", f"{avg_engagement:.2f}%")
    
    with col3:
        viral_content = analyzer.identify_viral_content()
        st.metric("爆款内容数", len(viral_content))
    
    st.markdown("---")
    
    # 爆款内容特征
    st.subheader("爆款内容特征")
    features = analyzer.analyze_content_features()
    
    if features:
        col1, col2 = st.columns(2)
        with col1:
            st.write("**爆款标题平均长度**:", f"{features.get('viral_title_avg_length', 0):.1f} 字")
            st.write("**普通标题平均长度**:", f"{features.get('normal_title_avg_length', 0):.1f} 字")
        
        with col2:
            if 'viral_peak_hours' in features:
                st.write("**爆款发布高峰时段**:", f"{features['viral_peak_hours'][0] if features['viral_peak_hours'] else 'N/A'}:00")
    
    # 内容表现图表
    st.subheader("内容表现 TOP20")
    fig = analyzer.create_performance_chart()
    st.plotly_chart(fig, use_container_width=True)
    
    # 最佳发布时间
    st.subheader("⏰ 最佳发布时间分析")
    try:
        time_analysis = analyzer.time_analysis()
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**最佳发布小时**: {time_analysis['best_hour']}:00")
        with col2:
            days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
            st.write(f"**最佳发布星期**: {days[time_analysis['best_day']]}")
    except Exception as e:
        st.info("时间分析需要 publish_time 列")
    
    # 爆款内容列表
    st.subheader("爆款内容列表")
    viral_content = analyzer.identify_viral_content()
    if len(viral_content) > 0:
        display_cols = ['content_id', 'title', 'reads', 'likes', 'comments', 'shares', 'engagement_rate']
        available_cols = [col for col in display_cols if col in viral_content.columns]
        st.dataframe(viral_content[available_cols].head(10), use_container_width=True)


def show_fan_analysis(fan_data):
    """显示粉丝分析"""
    st.header("粉丝分析")
    
    if fan_data is None:
        st.warning("请先加载粉丝数据")
        return
    
    # 初始化分析器
    analyzer = FanAnalyzer(fan_data)
    
    # 增长指标
    st.subheader("增长指标")
    metrics = analyzer.calculate_growth_metrics()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总粉丝数", f"{metrics.get('total_fans', 0):,}")
    with col2:
        st.metric("净增粉丝", f"{metrics.get('net_new_fans', 0):,}")
    with col3:
        st.metric("日均增长", f"{metrics.get('avg_daily_growth', 0):.0f}")
    with col4:
        st.metric("增长率", f"{metrics.get('growth_rate', 0):.2f}%")
    
    st.markdown("---")
    
    # 粉丝增长趋势图
    st.subheader("粉丝增长趋势")
    fig = analyzer.create_growth_chart()
    st.plotly_chart(fig, use_container_width=True)
    
    # 粉丝画像
    st.subheader("粉丝画像")
    demo = analyzer.analyze_demographics()
    
    if demo:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if 'gender_dist' in demo:
                fig = analyzer.create_demographics_chart('gender')
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if 'age_group_dist' in demo:
                fig = analyzer.create_demographics_chart('age')
                st.plotly_chart(fig, use_container_width=True)
        
        with col3:
            if 'top_cities' in demo:
                fig = analyzer.create_demographics_chart('city')
                st.plotly_chart(fig, use_container_width=True)
    
    # 活跃时段
    st.subheader("⏰ 粉丝活跃时段")
    try:
        active_hours = analyzer.analyze_active_hours()
        st.write(f"**最活跃时段**: {active_hours['peak_hour']}:00")
        st.write(f"**TOP3 活跃时段**: {[f'{h}:00' for h in active_hours['top_3_hours']]}")
    except Exception as e:
        st.info("活跃时段分析需要 active_time 或 datetime 列")


def show_sentiment_analysis(comment_data):
    """显示情感分析"""
    st.header("情感分析")
    
    if comment_data is None:
        st.warning("请先加载评论数据")
        return
    
    # 初始化分析器
    analyzer = SentimentAnalyzer(comment_data)
    
    # 分析情感
    with st.spinner("正在分析评论情感..."):
        df = analyzer.analyze_batch()
    
    # 情感分布
    st.subheader("情感分布")
    dist = analyzer.sentiment_distribution()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("积极评论", f"{dist['positive']} ({dist['positive_pct']:.1f}%)")
    with col2:
        st.metric("中性评论", f"{dist['neutral']} ({dist['neutral_pct']:.1f}%)")
    with col3:
        st.metric("消极评论", f"{dist['negative']} ({dist['negative_pct']:.1f}%)")
    
    st.markdown("---")
    
    # 情感分布图
    col1, col2 = st.columns(2)
    
    with col1:
        fig = analyzer.create_sentiment_chart()
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        try:
            fig = analyzer.create_trend_chart()
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.info("趋势图需要 date 列")
    
    # 情感报告
    st.subheader("分析报告")
    report = analyzer.generate_report()
    st.markdown(report)
    
    # 负面反馈
    st.subheader("负面反馈 TOP10")
    negative_feedback = analyzer.extract_negative_feedback()
    if len(negative_feedback) > 0:
        st.dataframe(negative_feedback[['comment', 'sentiment_score']], use_container_width=True)


def show_competitor_analysis(content_data, fan_data):
    """显示竞品对比分析"""
    st.header("竞品对比分析")
    
    if content_data is None:
        st.warning("请先加载数据")
        return
    
    st.info("提示：上传多个账号的数据进行对比分析")
    
    # 按平台对比
    if 'platform' in content_data.columns:
        st.subheader("各平台表现对比")
        
        platform_metrics = content_data.groupby('platform').agg({
            'reads': ['mean', 'sum'],
            'likes': 'mean',
            'comments': 'mean',
            'shares': 'mean'
        }).round(2)
        
        st.dataframe(platform_metrics, use_container_width=True)
        
        # 平台对比图
        fig = px.bar(
            content_data.groupby('platform')['reads'].mean().reset_index(),
            x='platform',
            y='reads',
            title='各平台平均阅读量对比',
            labels={'platform': '平台', 'reads': '平均阅读量'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # 内容类型对比
    if 'content_type' in content_data.columns:
        st.subheader("内容类型对比")
        
        type_metrics = content_data.groupby('content_type').agg({
            'reads': 'mean',
            'engagement_rate': lambda x: x.mean() if 'engagement_rate' in content_data.columns else None
        }).round(2)
        
        st.dataframe(type_metrics, use_container_width=True)


def show_report_export(content_data, fan_data, comment_data):
    """显示报告导出功能"""
    st.header("报告导出")
    
    if content_data is None:
        st.warning("请先加载数据")
        return
    
    st.subheader("生成运营报告")
    
    # 报告内容选择
    report_sections = st.multiselect(
        "选择报告章节",
        ["数据概览", "内容分析", "粉丝分析", "情感分析", "优化建议"],
        default=["数据概览", "内容分析", "粉丝分析", "情感分析"]
    )
    
    if st.button("生成报告"):
        report = generate_report(content_data, fan_data, comment_data, report_sections)
        
        st.download_button(
            label="下载报告 (Markdown)",
            data=report,
            file_name=f"社交媒体运营报告_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown"
        )
        
        st.markdown("---")
        st.subheader("报告预览")
        st.markdown(report)


def generate_report(content_data, fan_data, comment_data, sections):
    """生成运营报告"""
    report = f"""# 社交媒体运营报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

"""
    
    if "数据概览" in sections:
        report += f"""## 一、数据概览

- 总内容数：{len(content_data)}
- 总阅读量：{content_data['reads'].sum():,}
- 总互动量：{content_data[['likes', 'comments', 'shares']].sum().sum():,}
- 当前粉丝：{fan_data['total_fans'].iloc[-1]:,}

---

"""
    
    if "内容分析" in sections:
        analyzer = ContentAnalyzer(content_data)
        metrics = analyzer.performance_metrics()
        viral = analyzer.identify_viral_content()
        
        report += f"""## 二、内容分析

- 平均阅读量：{content_data['reads'].mean():,.0f}
- 平均互动率：{metrics['engagement_rate'].mean():.2f}%
- 爆款内容数：{len(viral)}

### 爆款内容特征
- 平均标题长度：{len(content_data['title'].iloc[0]) if 'title' in content_data.columns else 'N/A'}字

---

"""
    
    if "粉丝分析" in sections:
        fan_analyzer = FanAnalyzer(fan_data)
        metrics = fan_analyzer.calculate_growth_metrics()
        
        report += f"""## 三、粉丝分析

- 总粉丝数：{metrics.get('total_fans', 0):,}
- 净增粉丝：{metrics.get('net_new_fans', 0):,}
- 日均增长：{metrics.get('avg_daily_growth', 0):.0f}
- 增长率：{metrics.get('growth_rate', 0):.2f}%

---

"""
    
    if "情感分析" in sections and comment_data is not None:
        sentiment_analyzer = SentimentAnalyzer(comment_data)
        sentiment_analyzer.analyze_batch()
        dist = sentiment_analyzer.sentiment_distribution()
        
        report += f"""## 四、情感分析

- 平均情感得分：{dist['avg_score']:.2f}
- 积极评论：{dist['positive']} ({dist['positive_pct']:.1f}%)
- 中性评论：{dist['neutral']} ({dist['neutral_pct']:.1f}%)
- 消极评论：{dist['negative']} ({dist['negative_pct']:.1f}%)

---

"""
    
    if "优化建议" in sections:
        report += f"""## 五、优化建议

### 内容优化
1. 分析爆款内容特征，复制成功模式
2. 在最佳发布时间发布内容
3. 优化标题长度和关键词使用

### 粉丝运营
1. 关注粉丝活跃时段，及时互动
2. 针对粉丝画像调整内容策略
3. 提升粉丝留存率

### 情感管理
1. 及时回应负面评论
2. 放大积极评论影响力
3. 持续监测情感趋势

---

**报告结束**
"""
    
    return report


if __name__ == "__main__":
    main()
