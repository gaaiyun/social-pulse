"""
内容分析模块 - Content Analyzer
负责分析社交媒体内容的表现数据，识别爆款内容特征
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import plotly.express as px
import plotly.graph_objects as go


class ContentAnalyzer:
    """社交媒体内容分析器"""
    
    def __init__(self, data: pd.DataFrame = None):
        """
        初始化内容分析器
        
        Args:
            data: 包含内容数据的 DataFrame
        """
        self.data = data
        self.viral_threshold = 0.8  # 爆款内容阈值（前 20%）
    
    def load_data(self, file_path: str) -> pd.DataFrame:
        """
        从文件加载数据
        
        Args:
            file_path: CSV 或 Excel 文件路径
            
        Returns:
            加载的 DataFrame
        """
        if file_path.endswith('.csv'):
            self.data = pd.read_csv(file_path)
        elif file_path.endswith(('.xlsx', '.xls')):
            self.data = pd.read_excel(file_path)
        else:
            raise ValueError("不支持的文件格式，请使用 CSV 或 Excel")
        
        return self.data
    
    def calculate_engagement_rate(self) -> pd.DataFrame:
        """
        计算互动率（点赞 + 评论 + 转发）/ 阅读量
        
        Returns:
            包含互动率的 DataFrame
        """
        if self.data is None:
            raise ValueError("请先加载数据")
        
        df = self.data.copy()
        
        # 确保必要的列存在
        required_cols = ['reads', 'likes']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"缺少必要的列：{col}")

        for col in ('comments', 'shares'):
            if col not in df.columns:
                df[col] = 0
        
        # 计算互动率
        engagement = df['likes'] + df['comments'] + df['shares']
        df['engagement_rate'] = (
            engagement.div(df['reads'].replace(0, np.nan)).fillna(0) * 100
        )
        
        return df
    
    def identify_viral_content(self, top_percent: float = 0.2) -> pd.DataFrame:
        """
        识别爆款内容
        
        Args:
            top_percent: 前百分之多少的内容算作爆款
            
        Returns:
            爆款内容 DataFrame
        """
        if self.data is None:
            raise ValueError("请先加载数据")
        
        df = self.calculate_engagement_rate()
        
        # 按互动率排序
        threshold = df['engagement_rate'].quantile(1 - top_percent)
        viral_content = df[df['engagement_rate'] >= threshold].copy()
        
        return viral_content
    
    def analyze_content_features(self) -> Dict:
        """
        分析爆款内容的特征
        
        Returns:
            包含特征分析的字典
        """
        viral_content = self.identify_viral_content().copy()
        normal_content = self.data[~self.data.index.isin(viral_content.index)].copy()

        features = {}

        # 分析标题长度
        if 'title' in viral_content.columns:
            features['viral_title_avg_length'] = viral_content['title'].str.len().mean()
            features['normal_title_avg_length'] = normal_content['title'].str.len().mean()

        # 分析发布时间
        if 'publish_time' in viral_content.columns:
            viral_content['hour'] = pd.to_datetime(viral_content['publish_time']).dt.hour
            normal_content['hour'] = pd.to_datetime(normal_content['publish_time']).dt.hour
            features['viral_peak_hours'] = viral_content['hour'].mode().tolist()
            features['normal_peak_hours'] = normal_content['hour'].mode().tolist()
        
        # 分析内容类型
        if 'content_type' in viral_content.columns:
            features['viral_content_type_dist'] = viral_content['content_type'].value_counts().to_dict()
            features['normal_content_type_dist'] = normal_content['content_type'].value_counts().to_dict()
        
        # 分析关键词
        if 'keywords' in viral_content.columns:
            features['viral_common_keywords'] = self._extract_common_keywords(viral_content['keywords'])
            features['normal_common_keywords'] = self._extract_common_keywords(normal_content['keywords'])
        
        return features
    
    def _extract_common_keywords(self, keywords_series: pd.Series) -> List[str]:
        """提取常见关键词"""
        all_keywords = []
        for keywords in keywords_series.dropna():
            if isinstance(keywords, str):
                all_keywords.extend([k.strip() for k in keywords.split(',')])
        
        keyword_counts = pd.Series(all_keywords).value_counts()
        return keyword_counts.head(10).index.tolist()
    
    def performance_metrics(self) -> pd.DataFrame:
        """
        计算内容表现指标
        
        Returns:
            包含各项指标的 DataFrame
        """
        if self.data is None:
            raise ValueError("请先加载数据")
        
        df = self.calculate_engagement_rate()
        
        # 计算各项指标
        metrics = pd.DataFrame({
            'content_id': df['content_id'] if 'content_id' in df.columns else df.index,
            'reads': df['reads'],
            'likes': df['likes'],
            'comments': df['comments'],
            'shares': df['shares'],
            'engagement_rate': df['engagement_rate'],
            'like_rate': df['likes'].div(df['reads'].replace(0, np.nan)).fillna(0) * 100,
            'comment_rate': df['comments'].div(df['reads'].replace(0, np.nan)).fillna(0) * 100,
            'share_rate': df['shares'].div(df['reads'].replace(0, np.nan)).fillna(0) * 100
        })
        
        return metrics
    
    def create_performance_chart(self) -> go.Figure:
        """
        创建内容表现图表
        
        Returns:
            Plotly 图形对象
        """
        if self.data is None:
            raise ValueError("请先加载数据")
        
        df = self.performance_metrics()
        
        # 按阅读量排序，取前 20 个
        top_content = df.nlargest(20, 'reads')
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='阅读量',
            x=top_content['content_id'],
            y=top_content['reads'],
            marker_color='#1f77b4'
        ))
        
        fig.add_trace(go.Scatter(
            name='互动率',
            x=top_content['content_id'],
            y=top_content['engagement_rate'],
            marker_color='#ff7f0e',
            yaxis='y2'
        ))
        
        fig.update_layout(
            title='内容表现 TOP20',
            xaxis_title='内容 ID',
            yaxis_title='阅读量',
            yaxis2=dict(title='互动率 (%)', overlaying='y', side='right'),
            legend=dict(x=0, y=1.1, orientation='h'),
            height=500
        )
        
        return fig
    
    def time_analysis(self) -> Dict:
        """
        分析最佳发布时间
        
        Returns:
            时间分析结果字典
        """
        if self.data is None or 'publish_time' not in self.data.columns:
            raise ValueError("数据中缺少发布时间列")
        
        df = self.data.copy()
        df['datetime'] = pd.to_datetime(df['publish_time'])
        df['hour'] = df['datetime'].dt.hour
        df['dayofweek'] = df['datetime'].dt.dayofweek
        
        # 计算互动率（如果还没有）
        if 'engagement_rate' not in df.columns:
            df['engagement_rate'] = (df['likes'] + df['comments'] + df['shares']) / df['reads'].replace(0, 1) * 100
        
        # 按小时分析
        hourly_perf = df.groupby('hour').agg({
            'reads': 'mean',
            'likes': 'mean',
            'engagement_rate': 'mean'
        }).reset_index()
        
        # 按星期分析
        weekly_perf = df.groupby('dayofweek').agg({
            'reads': 'mean',
            'likes': 'mean'
        }).reset_index()
        
        best_hour = hourly_perf.loc[hourly_perf['reads'].idxmax(), 'hour']
        best_day = weekly_perf.loc[weekly_perf['reads'].idxmax(), 'dayofweek']
        
        return {
            'best_hour': int(best_hour),
            'best_day': int(best_day),
            'hourly_performance': hourly_perf,
            'weekly_performance': weekly_perf
        }


def test_content_analyzer():
    """测试内容分析器"""
    # 创建测试数据
    test_data = pd.DataFrame({
        'content_id': range(1, 101),
        'title': [f'测试标题{i}' for i in range(1, 101)],
        'reads': np.random.randint(1000, 100000, 100),
        'likes': np.random.randint(100, 10000, 100),
        'comments': np.random.randint(10, 1000, 100),
        'shares': np.random.randint(5, 500, 100),
        'publish_time': pd.date_range('2024-01-01', periods=100, freq='H'),
        'content_type': np.random.choice(['图文', '视频', '直播'], 100),
        'keywords': ['科技，AI' if i % 2 == 0 else '生活，日常' for i in range(100)]
    })
    
    analyzer = ContentAnalyzer(test_data)
    
    # 测试各项功能
    metrics = analyzer.performance_metrics()
    assert len(metrics) == 100, "指标计算失败"
    assert 'engagement_rate' in metrics.columns, "缺少互动率列"
    
    viral = analyzer.identify_viral_content()
    assert len(viral) <= 20, "爆款内容识别失败"
    
    features = analyzer.analyze_content_features()
    assert 'viral_title_avg_length' in features, "特征分析失败"
    
    print("[OK] 内容分析器测试通过")
    return True


if __name__ == "__main__":
    test_content_analyzer()
