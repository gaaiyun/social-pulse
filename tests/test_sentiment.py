"""
情感分析模块单元测试
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentiment_analyzer import SentimentAnalyzer


@pytest.fixture
def sample_comment_data():
    """创建示例评论数据"""
    comments = [
        '太棒了，非常喜欢！', '一般般吧', '质量很差，失望', '超级好用，推荐！',
        '还不错', '完全不值', '很好的体验', '态度太差了',
        '物流很快', '用了一次就坏了', '会回购的', '客服很耐心',
        '包装精美', '性价比很高', '失望透顶', '超出预期',
        '平平无奇', '强烈推荐', '不要买', '非常满意'
    ]
    dates = pd.date_range('2024-01-01', periods=20, freq='D')
    
    return pd.DataFrame({
        'comment': comments,
        'date': dates.strftime('%Y-%m-%d'),
        'content_id': range(1, 21),
        'platform': np.random.choice(['微信', '微博', '抖音', '小红书'], 20)
    })


class TestSentimentAnalyzer:
    """情感分析器测试类"""
    
    def test_init(self, sample_comment_data):
        """测试初始化"""
        analyzer = SentimentAnalyzer(sample_comment_data)
        assert analyzer.data is not None
        assert len(analyzer.data) == 20
    
    def test_clean_text(self):
        """测试文本清洗"""
        analyzer = SentimentAnalyzer()
        
        # 测试 URL 移除
        assert 'http' not in analyzer.clean_text('看看这个 http://example.com')
        
        # 测试@提及移除
        assert '@' not in analyzer.clean_text('@用户 你好')
        
        # 测试空值处理
        assert analyzer.clean_text(None) == ''
        assert analyzer.clean_text('') == ''
    
    def test_analyze_sentiment(self):
        """测试单条情感分析"""
        analyzer = SentimentAnalyzer()
        
        # 测试积极情感
        positive_score = analyzer.analyze_sentiment('非常好，太棒了！')
        assert positive_score > 0.5
        
        # 测试消极情感
        negative_score = analyzer.analyze_sentiment('太差了，很失望')
        assert negative_score < 0.5
    
    def test_analyze_batch(self, sample_comment_data):
        """测试批量情感分析"""
        analyzer = SentimentAnalyzer(sample_comment_data)
        df = analyzer.analyze_batch()
        
        assert len(df) == 20
        assert 'sentiment_score' in df.columns
        assert 'sentiment_label' in df.columns
        assert all(df['sentiment_score'] >= 0)
        assert all(df['sentiment_score'] <= 1)
    
    def test_sentiment_distribution(self, sample_comment_data):
        """测试情感分布统计"""
        analyzer = SentimentAnalyzer(sample_comment_data)
        analyzer.analyze_batch()
        dist = analyzer.sentiment_distribution()
        
        assert 'positive' in dist
        assert 'neutral' in dist
        assert 'negative' in dist
        assert 'total' in dist
        assert dist['total'] == 20
        assert 'avg_score' in dist
    
    def test_sentiment_trend(self, sample_comment_data):
        """测试情感趋势分析"""
        analyzer = SentimentAnalyzer(sample_comment_data)
        analyzer.analyze_batch()
        trend = analyzer.sentiment_trend()
        
        assert len(trend) > 0
        assert 'date' in trend.columns
        assert 'avg_score' in trend.columns
    
    def test_create_sentiment_chart(self, sample_comment_data):
        """测试情感图表创建"""
        analyzer = SentimentAnalyzer(sample_comment_data)
        analyzer.analyze_batch()
        fig = analyzer.create_sentiment_chart()
        
        assert fig is not None
        assert len(fig.data) > 0
    
    def test_generate_report(self, sample_comment_data):
        """测试报告生成"""
        analyzer = SentimentAnalyzer(sample_comment_data)
        analyzer.analyze_batch()
        report = analyzer.generate_report()
        
        assert '情感分析报告' in report
        assert '总评论数' in report
        assert '平均情感得分' in report
    
    def test_extract_negative_feedback(self, sample_comment_data):
        """测试负面反馈提取"""
        analyzer = SentimentAnalyzer(sample_comment_data)
        analyzer.analyze_batch()
        negative = analyzer.extract_negative_feedback()
        
        assert len(negative) <= 20
        if len(negative) > 0:
            assert all(negative['sentiment_score'] <= 0.4)
    
    def test_load_data_none(self):
        """测试空数据初始化"""
        analyzer = SentimentAnalyzer()
        assert analyzer.data is None
    
    def test_analyze_batch_no_data(self):
        """测试无数据时批量分析"""
        analyzer = SentimentAnalyzer()
        with pytest.raises(ValueError):
            analyzer.analyze_batch()
    
    def test_sentiment_cache(self):
        """测试情感分析缓存"""
        analyzer = SentimentAnalyzer()
        
        text = '测试文本'
        score1 = analyzer.analyze_sentiment(text)
        score2 = analyzer.analyze_sentiment(text)
        
        assert score1 == score2  # 缓存命中


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
