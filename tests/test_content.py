"""
内容分析模块单元测试
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_analyzer import ContentAnalyzer


@pytest.fixture
def sample_content_data():
    """创建示例内容数据"""
    return pd.DataFrame({
        'content_id': range(1, 101),
        'title': [f'测试标题{i}' for i in range(1, 101)],
        'reads': np.random.randint(1000, 100000, 100),
        'likes': np.random.randint(100, 10000, 100),
        'comments': np.random.randint(10, 1000, 100),
        'shares': np.random.randint(5, 500, 100),
        'publish_time': pd.date_range('2024-01-01', periods=100, freq='h'),
        'content_type': np.random.choice(['图文', '视频', '直播'], 100),
        'keywords': ['科技,AI' if i % 2 == 0 else '生活，日常' for i in range(100)]
    })


class TestContentAnalyzer:
    """内容分析器测试类"""
    
    def test_init(self, sample_content_data):
        """测试初始化"""
        analyzer = ContentAnalyzer(sample_content_data)
        assert analyzer.data is not None
        assert len(analyzer.data) == 100
    
    def test_calculate_engagement_rate(self, sample_content_data):
        """测试互动率计算"""
        analyzer = ContentAnalyzer(sample_content_data)
        df = analyzer.calculate_engagement_rate()
        
        assert 'engagement_rate' in df.columns
        assert len(df) == 100
        assert all(df['engagement_rate'] >= 0)
    
    def test_identify_viral_content(self, sample_content_data):
        """测试爆款内容识别"""
        analyzer = ContentAnalyzer(sample_content_data)
        viral = analyzer.identify_viral_content(top_percent=0.2)
        
        assert len(viral) <= 20  # 前 20%
        assert len(viral) > 0
    
    def test_performance_metrics(self, sample_content_data):
        """测试表现指标计算"""
        analyzer = ContentAnalyzer(sample_content_data)
        metrics = analyzer.performance_metrics()
        
        assert len(metrics) == 100
        assert 'engagement_rate' in metrics.columns
        assert 'like_rate' in metrics.columns
        assert 'comment_rate' in metrics.columns
        assert 'share_rate' in metrics.columns
    
    def test_analyze_content_features(self, sample_content_data):
        """测试内容特征分析"""
        analyzer = ContentAnalyzer(sample_content_data)
        features = analyzer.analyze_content_features()
        
        assert 'viral_title_avg_length' in features
        assert 'normal_title_avg_length' in features
    
    def test_time_analysis(self, sample_content_data):
        """测试时间分析"""
        analyzer = ContentAnalyzer(sample_content_data)
        time_analysis = analyzer.time_analysis()
        
        assert 'best_hour' in time_analysis
        assert 'best_day' in time_analysis
        assert 0 <= time_analysis['best_hour'] <= 23
        assert 0 <= time_analysis['best_day'] <= 6
    
    def test_create_performance_chart(self, sample_content_data):
        """测试图表创建"""
        analyzer = ContentAnalyzer(sample_content_data)
        fig = analyzer.create_performance_chart()
        
        assert fig is not None
        assert len(fig.data) > 0
    
    def test_load_data_none(self):
        """测试空数据初始化"""
        analyzer = ContentAnalyzer()
        assert analyzer.data is None
    
    def test_calculate_engagement_rate_no_data(self):
        """测试无数据时计算互动率"""
        analyzer = ContentAnalyzer()
        with pytest.raises(ValueError):
            analyzer.calculate_engagement_rate()
    
    def test_viral_content_threshold(self, sample_content_data):
        """测试爆款阈值"""
        analyzer = ContentAnalyzer(sample_content_data)
        
        viral_10 = analyzer.identify_viral_content(top_percent=0.1)
        viral_20 = analyzer.identify_viral_content(top_percent=0.2)
        
        assert len(viral_10) <= len(viral_20)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
