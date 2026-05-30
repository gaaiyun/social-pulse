"""
情感分析模块 - Sentiment Analyzer
使用 SnowNLP 分析评论情感倾向
"""

import sys
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from snownlp import SnowNLP
import plotly.express as px
import plotly.graph_objects as go
import re


class SentimentAnalyzer:
    """评论情感分析器"""
    
    def __init__(self, data: pd.DataFrame = None):
        """
        初始化情感分析器
        
        Args:
            data: 包含评论数据的 DataFrame
        """
        self.data = data
        self.sentiment_cache = {}
    
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
    
    def clean_text(self, text: str) -> str:
        """
        清洗文本
        
        Args:
            text: 原始文本
            
        Returns:
            清洗后的文本
        """
        if not isinstance(text, str):
            return ""
        
        # 移除 URL
        text = re.sub(r'http[s]?://\S+', '', text)
        # 移除@提及
        text = re.sub(r'@\S+', '', text)
        # 移除特殊字符和表情
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
        # 移除多余空格
        text = ' '.join(text.split())
        
        return text
    
    def analyze_sentiment(self, text: str) -> float:
        """
        分析单条文本的情感得分
        
        Args:
            text: 待分析的文本
            
        Returns:
            情感得分 (0-1, 越接近 1 越积极)
        """
        if not text or not isinstance(text, str):
            return 0.5
        
        # 使用缓存避免重复计算
        if text in self.sentiment_cache:
            return self.sentiment_cache[text]
        
        try:
            s = SnowNLP(text)
            score = s.sentiments
            self.sentiment_cache[text] = score
            return score
        except Exception as e:
            print(f"情感分析失败：{e}")
            return 0.5
    
    def analyze_batch(self, comment_col: str = 'comment') -> pd.DataFrame:
        """
        批量分析情感
        
        Args:
            comment_col: 评论列名
            
        Returns:
            包含情感得分的 DataFrame
        """
        if self.data is None:
            raise ValueError("请先加载数据")
        
        if comment_col not in self.data.columns:
            raise ValueError(f"数据中缺少列：{comment_col}")
        
        df = self.data.copy()
        
        # 清洗文本
        df['cleaned_comment'] = df[comment_col].apply(self.clean_text)
        
        # 分析情感（进度提示走 stderr，避免污染 stdout 的结构化输出）
        print("正在分析情感...", file=sys.stderr)
        df['sentiment_score'] = df['cleaned_comment'].apply(self.analyze_sentiment)
        
        # 情感分类
        df['sentiment_label'] = df['sentiment_score'].apply(self._classify_sentiment)
        
        # 更新 self.data
        self.data = df
        
        return self.data
    
    def _classify_sentiment(self, score: float) -> str:
        """
        将情感得分分类
        
        Args:
            score: 情感得分
            
        Returns:
            情感标签
        """
        if score >= 0.6:
            return '积极'
        elif score <= 0.4:
            return '消极'
        else:
            return '中性'
    
    def sentiment_distribution(self) -> Dict:
        """
        情感分布统计
        
        Returns:
            情感分布字典
        """
        if self.data is None or 'sentiment_score' not in self.data.columns:
            self.analyze_batch()
        
        df = self.data
        
        # 确保 sentiment_score 列存在
        if 'sentiment_score' not in df.columns:
            return {
                'positive': 0,
                'neutral': 0,
                'negative': 0,
                'positive_pct': 0,
                'neutral_pct': 0,
                'negative_pct': 0,
                'avg_score': 0.5,
                'total': 0
            }
        
        distribution = {
            'positive': (df['sentiment_score'] >= 0.6).sum(),
            'neutral': ((df['sentiment_score'] < 0.6) & (df['sentiment_score'] > 0.4)).sum(),
            'negative': (df['sentiment_score'] <= 0.4).sum(),
            'positive_pct': (df['sentiment_score'] >= 0.6).mean() * 100,
            'neutral_pct': ((df['sentiment_score'] < 0.6) & (df['sentiment_score'] > 0.4)).mean() * 100,
            'negative_pct': (df['sentiment_score'] <= 0.4).mean() * 100,
            'avg_score': df['sentiment_score'].mean()
        }
        
        distribution['total'] = distribution['positive'] + distribution['neutral'] + distribution['negative']
        
        return distribution
    
    def sentiment_trend(self, time_col: str = 'date') -> pd.DataFrame:
        """
        分析情感趋势
        
        Args:
            time_col: 时间列名
            
        Returns:
            情感趋势 DataFrame
        """
        if self.data is None or time_col not in self.data.columns:
            raise ValueError(f"数据中缺少时间列：{time_col}")
        
        df = self.data.copy()
        df[time_col] = pd.to_datetime(df[time_col])
        
        # 按日期分组
        daily_sentiment = df.groupby(df[time_col].dt.date).agg({
            'sentiment_score': ['mean', 'std', 'count'],
            'sentiment_label': lambda x: (x == '积极').sum() / len(x) * 100
        }).reset_index()
        
        daily_sentiment.columns = ['date', 'avg_score', 'score_std', 'comment_count', 'positive_rate']
        
        return daily_sentiment
    
    def keyword_sentiment(self, keywords: List[str], comment_col: str = 'comment') -> Dict:
        """
        分析关键词相关的情感
        
        Args:
            keywords: 关键词列表
            comment_col: 评论列名
            
        Returns:
            关键词情感字典
        """
        if self.data is None:
            raise ValueError("请先加载数据")
        
        df = self.data
        if comment_col not in df.columns:
            raise ValueError(f"数据中缺少列：{comment_col}")
        
        keyword_sentiments = {}
        
        for keyword in keywords:
            # 筛选包含关键词的评论
            mask = df[comment_col].str.contains(keyword, na=False, case=False)
            keyword_comments = df[mask]
            
            if len(keyword_comments) > 0:
                keyword_sentiments[keyword] = {
                    'count': len(keyword_comments),
                    'avg_score': keyword_comments['sentiment_score'].mean(),
                    'positive_rate': (keyword_comments['sentiment_score'] >= 0.6).mean() * 100,
                    'negative_rate': (keyword_comments['sentiment_score'] <= 0.4).mean() * 100
                }
        
        return keyword_sentiments
    
    def create_sentiment_chart(self) -> go.Figure:
        """
        创建情感分布图
        
        Returns:
            Plotly 图形对象
        """
        dist = self.sentiment_distribution()
        
        fig = go.Figure()
        
        fig.add_trace(go.Pie(
            labels=['积极', '中性', '消极'],
            values=[dist['positive'], dist['neutral'], dist['negative']],
            marker_colors=['#2ca02c', '#1f77b4', '#d62728'],
            hole=0.3
        ))
        
        fig.update_layout(
            title='评论情感分布',
            height=500,
            annotations=[dict(text=f'平均分：{dist["avg_score"]:.2f}', x=0.5, y=0.5, font_size=15, showarrow=False)]
        )
        
        return fig
    
    def create_trend_chart(self, time_col: str = 'date') -> go.Figure:
        """
        创建情感趋势图
        
        Args:
            time_col: 时间列名
            
        Returns:
            Plotly 图形对象
        """
        trend_df = self.sentiment_trend(time_col)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=trend_df['date'],
            y=trend_df['avg_score'],
            mode='lines+markers',
            name='平均情感分',
            line=dict(color='#1f77b4', width=2)
        ))
        
        fig.add_trace(go.Bar(
            x=trend_df['date'],
            y=trend_df['comment_count'],
            name='评论数',
            marker_color='#2ca02c',
            opacity=0.5,
            yaxis='y2'
        ))
        
        fig.update_layout(
            title='情感趋势',
            xaxis_title='日期',
            yaxis_title='情感得分',
            yaxis2=dict(title='评论数', overlaying='y', side='right'),
            legend=dict(x=0, y=1.1, orientation='h'),
            height=500,
            hovermode='x unified'
        )
        
        return fig
    
    def extract_negative_feedback(self, threshold: float = 0.4, top_n: int = 20) -> pd.DataFrame:
        """
        提取负面反馈
        
        Args:
            threshold: 负面阈值
            top_n: 返回数量
            
        Returns:
            负面评论 DataFrame
        """
        if self.data is None:
            raise ValueError("请先加载数据")
        
        df = self.data
        
        negative_comments = df[df['sentiment_score'] <= threshold].copy()
        negative_comments = negative_comments.sort_values('sentiment_score')
        
        return negative_comments.head(top_n)
    
    def generate_report(self) -> str:
        """
        生成情感分析报告
        
        Returns:
            报告文本
        """
        dist = self.sentiment_distribution()
        
        report = f"""
## 情感分析报告

### 总体概况
- 总评论数：{dist['total']}
- 平均情感得分：{dist['avg_score']:.2f}

### 情感分布
- 积极评论：{dist['positive']} ({dist['positive_pct']:.1f}%)
- 中性评论：{dist['neutral']} ({dist['neutral_pct']:.1f}%)
- 消极评论：{dist['negative']} ({dist['negative_pct']:.1f}%)

### 分析结论
"""
        if dist['avg_score'] > 0.6:
            report += "整体评论情感偏向积极，用户对内容满意度较高。\n"
        elif dist['avg_score'] < 0.4:
            report += "整体评论情感偏向消极，需要关注用户反馈并改进。\n"
        else:
            report += "整体评论情感中性，用户反馈较为平淡。\n"
        
        if dist['negative_pct'] > 30:
            report += f"注意：消极评论占比{dist['negative_pct']:.1f}%，建议重点关注负面反馈。\n"
        
        return report


def test_sentiment_analyzer():
    """测试情感分析器"""
    # 创建测试数据
    test_data = pd.DataFrame({
        'comment': [
            '这个产品太好了，非常喜欢！',
            '一般般吧，没什么特别的',
            '质量太差了，非常失望',
            '超级棒，强烈推荐给大家',
            '还行，符合预期',
            '完全不值这个价格',
            '很好的体验，会回购',
            '客服态度很差',
            '物流很快，包装完好',
            '用了一次就坏了'
        ],
        'date': pd.date_range('2024-01-01', periods=10, freq='D')
    })
    
    analyzer = SentimentAnalyzer(test_data)
    
    # 测试情感分析
    df = analyzer.analyze_batch()
    assert len(df) == 10, "批量分析失败"
    assert 'sentiment_score' in df.columns, "缺少情感得分列"
    assert 'sentiment_label' in df.columns, "缺少情感标签列"
    
    # 测试分布
    dist = analyzer.sentiment_distribution()
    assert 'positive' in dist, "分布统计失败"
    assert dist['total'] == 10, "总数计算错误"
    
    # 测试报告
    report = analyzer.generate_report()
    assert '情感分析报告' in report, "报告生成失败"
    
    print("[OK] 情感分析器测试通过")
    return True


if __name__ == "__main__":
    test_sentiment_analyzer()
