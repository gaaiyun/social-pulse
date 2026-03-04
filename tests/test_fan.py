"""
粉丝分析模块单元测试
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fan_analyzer import FanAnalyzer


@pytest.fixture
def sample_fan_data():
    """创建示例粉丝数据"""
    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    return pd.DataFrame({
        'date': dates.strftime('%Y-%m-%d'),
        'new_fans': np.random.randint(50, 500, 30),
        'unfollows': np.random.randint(10, 100, 30),
        'total_fans': np.cumsum(np.random.randint(50, 500, 30)) + 10000,
        'interactions': np.random.randint(100, 5000, 30),
        'gender': np.random.choice(['男', '女'], 30),
        'age': np.random.randint(18, 60, 30),
        'city': np.random.choice(['北京', '上海', '广州', '深圳', '杭州'], 30)
    })


class TestFanAnalyzer:
    """粉丝分析器测试类"""
    
    def test_init(self, sample_fan_data):
        """测试初始化"""
        analyzer = FanAnalyzer(sample_fan_data)
        assert analyzer.data is not None
        assert len(analyzer.data) == 30
    
    def test_analyze_growth_trend(self, sample_fan_data):
        """测试增长趋势分析"""
        analyzer = FanAnalyzer(sample_fan_data)
        df = analyzer.analyze_growth_trend()
        
        assert len(df) == 30
        assert 'date' in df.columns or 'datetime' in df.columns
    
    def test_calculate_growth_metrics(self, sample_fan_data):
        """测试增长指标计算"""
        analyzer = FanAnalyzer(sample_fan_data)
        metrics = analyzer.calculate_growth_metrics()
        
        assert 'total_fans' in metrics
        assert 'net_new_fans' in metrics
        assert metrics['total_fans'] > 0
    
    def test_analyze_demographics(self, sample_fan_data):
        """测试人口统计特征分析"""
        analyzer = FanAnalyzer(sample_fan_data)
        demo = analyzer.analyze_demographics()
        
        assert 'gender_dist' in demo
        assert 'age_avg' in demo
        assert 'top_cities' in demo
    
    def test_create_growth_chart(self, sample_fan_data):
        """测试增长图表创建"""
        analyzer = FanAnalyzer(sample_fan_data)
        fig = analyzer.create_growth_chart()
        
        assert fig is not None
        assert len(fig.data) > 0
    
    def test_create_demographics_chart(self, sample_fan_data):
        """测试人口统计图表创建"""
        analyzer = FanAnalyzer(sample_fan_data)
        
        fig_gender = analyzer.create_demographics_chart('gender')
        assert fig_gender is not None
        
        fig_age = analyzer.create_demographics_chart('age')
        assert fig_age is not None
    
    def test_load_data_none(self):
        """测试空数据初始化"""
        analyzer = FanAnalyzer()
        assert analyzer.data is None
    
    def test_analyze_growth_trend_no_data(self):
        """测试无数据时分析增长趋势"""
        analyzer = FanAnalyzer()
        with pytest.raises(ValueError):
            analyzer.analyze_growth_trend()
    
    def test_growth_metrics_calculation(self, sample_fan_data):
        """测试增长指标计算逻辑"""
        analyzer = FanAnalyzer(sample_fan_data)
        metrics = analyzer.calculate_growth_metrics()
        
        # 验证指标合理性
        assert metrics['total_fans'] >= metrics['net_new_fans']
        assert metrics['avg_daily_growth'] >= 0
    
    def test_demographics_age_groups(self, sample_fan_data):
        """测试年龄分组"""
        analyzer = FanAnalyzer(sample_fan_data)
        demo = analyzer.analyze_demographics()
        
        assert 'age_group_dist' in demo
        assert len(demo['age_group_dist']) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
