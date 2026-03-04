"""
粉丝分析模块 - Fan Analyzer
负责分析粉丝增长趋势、活跃时段和用户画像
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta


class FanAnalyzer:
    """粉丝数据分析器"""
    
    def __init__(self, data: pd.DataFrame = None):
        """
        初始化粉丝分析器
        
        Args:
            data: 包含粉丝数据的 DataFrame
        """
        self.data = data
    
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
    
    def analyze_growth_trend(self) -> pd.DataFrame:
        """
        分析粉丝增长趋势
        
        Returns:
            包含增长趋势的 DataFrame
        """
        if self.data is None:
            raise ValueError("请先加载数据")
        
        df = self.data.copy()
        
        if 'date' not in df.columns and 'datetime' not in df.columns:
            raise ValueError("数据中缺少日期列")
        
        date_col = 'date' if 'date' in df.columns else 'datetime'
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col)
        
        # 计算累计粉丝数
        if 'new_fans' in df.columns:
            df['total_fans'] = df['new_fans'].cumsum()
        
        # 计算增长率
        if 'total_fans' in df.columns:
            df['growth_rate'] = df['total_fans'].pct_change() * 100
        
        return df
    
    def calculate_growth_metrics(self) -> Dict:
        """
        计算增长指标
        
        Returns:
            包含增长指标的字典
        """
        df = self.analyze_growth_trend()
        
        metrics = {}
        
        if 'total_fans' in df.columns:
            metrics['total_fans'] = df['total_fans'].iloc[-1]
            metrics['net_new_fans'] = df['total_fans'].iloc[-1] - df['total_fans'].iloc[0]
            metrics['avg_daily_growth'] = df['total_fans'].diff().mean()
            metrics['max_daily_growth'] = df['total_fans'].diff().max()
            
            # 计算增长率
            if len(df) > 1:
                start_fans = df['total_fans'].iloc[0]
                end_fans = df['total_fans'].iloc[-1]
                days = (df['date'].iloc[-1] - df['date'].iloc[0]).days
                if days > 0 and start_fans > 0:
                    metrics['growth_rate'] = ((end_fans - start_fans) / start_fans) * 100 / days
                else:
                    metrics['growth_rate'] = 0
        
        if 'new_fans' in df.columns:
            metrics['avg_new_fans_per_day'] = df['new_fans'].mean()
            metrics['total_new_fans'] = df['new_fans'].sum()
        
        if 'unfollows' in df.columns:
            metrics['total_unfollows'] = df['unfollows'].sum()
            metrics['avg_unfollows_per_day'] = df['unfollows'].mean()
            metrics['retention_rate'] = (1 - df['unfollows'].sum() / df['new_fans'].sum()) * 100 if df['new_fans'].sum() > 0 else 100
        
        return metrics
    
    def analyze_active_hours(self) -> Dict:
        """
        分析粉丝活跃时段
        
        Returns:
            活跃时段分析结果
        """
        if self.data is None:
            raise ValueError("请先加载数据")
        
        df = self.data.copy()
        
        if 'active_time' not in df.columns and 'datetime' not in df.columns:
            raise ValueError("数据中缺少时间列")
        
        time_col = 'active_time' if 'active_time' in df.columns else 'datetime'
        df[time_col] = pd.to_datetime(df[time_col])
        df['hour'] = df[time_col].dt.hour
        
        # 按小时统计活跃度
        hourly_activity = df.groupby('hour').agg({
            'interactions': 'sum' if 'interactions' in df.columns else 'size',
            'comments': 'sum' if 'comments' in df.columns else lambda x: 0,
            'likes': 'sum' if 'likes' in df.columns else lambda x: 0
        }).reset_index()
        
        # 找出最活跃时段
        peak_hour = hourly_activity.loc[hourly_activity.iloc[:, 1].idxmax(), 'hour']
        
        # 活跃度分布
        hourly_activity['percentage'] = hourly_activity.iloc[:, 1] / hourly_activity.iloc[:, 1].sum() * 100
        
        return {
            'peak_hour': int(peak_hour),
            'hourly_activity': hourly_activity,
            'top_3_hours': hourly_activity.nlargest(3, hourly_activity.columns[1])['hour'].tolist()
        }
    
    def analyze_demographics(self) -> Dict:
        """
        分析粉丝画像（年龄、性别、地域等）
        
        Returns:
            粉丝画像分析结果
        """
        if self.data is None:
            raise ValueError("请先加载数据")
        
        df = self.data.copy()
        demographics = {}
        
        # 性别分布
        if 'gender' in df.columns:
            demographics['gender_dist'] = df['gender'].value_counts().to_dict()
            demographics['gender_dist_percent'] = (df['gender'].value_counts() / len(df) * 100).round(2).to_dict()
        
        # 年龄分布
        if 'age' in df.columns:
            demographics['age_avg'] = df['age'].mean()
            demographics['age_median'] = df['age'].median()
            demographics['age_min'] = df['age'].min()
            demographics['age_max'] = df['age'].max()
            
            # 年龄段分布
            bins = [0, 18, 25, 35, 45, 60, 100]
            labels = ['<18', '18-25', '26-35', '36-45', '46-60', '60+']
            df['age_group'] = pd.cut(df['age'], bins=bins, labels=labels)
            demographics['age_group_dist'] = df['age_group'].value_counts().to_dict()
        
        # 地域分布
        if 'city' in df.columns:
            demographics['top_cities'] = df['city'].value_counts().head(10).to_dict()
        
        if 'province' in df.columns:
            demographics['top_provinces'] = df['province'].value_counts().head(10).to_dict()
        
        return demographics
    
    def create_growth_chart(self) -> go.Figure:
        """
        创建粉丝增长趋势图
        
        Returns:
            Plotly 图形对象
        """
        df = self.analyze_growth_trend()
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['total_fans'],
            mode='lines+markers',
            name='粉丝总数',
            line=dict(color='#1f77b4', width=2)
        ))
        
        if 'new_fans' in df.columns:
            fig.add_trace(go.Bar(
                x=df['date'],
                y=df['new_fans'],
                name='新增粉丝',
                marker_color='#2ca02c',
                opacity=0.5,
                yaxis='y2'
            ))
        
        fig.update_layout(
            title='粉丝增长趋势',
            xaxis_title='日期',
            yaxis_title='粉丝总数',
            yaxis2=dict(title='新增粉丝', overlaying='y', side='right'),
            legend=dict(x=0, y=1.1, orientation='h'),
            height=500,
            hovermode='x unified'
        )
        
        return fig
    
    def create_demographics_chart(self, demographic_type: str = 'gender') -> go.Figure:
        """
        创建粉丝画像图表
        
        Args:
            demographic_type: 画像类型 ('gender', 'age', 'city')
            
        Returns:
            Plotly 图形对象
        """
        demo_data = self.analyze_demographics()
        
        if demographic_type == 'gender' and 'gender_dist' in demo_data:
            fig = px.pie(
                values=list(demo_data['gender_dist'].values()),
                names=list(demo_data['gender_dist'].keys()),
                title='粉丝性别分布'
            )
        elif demographic_type == 'age' and 'age_group_dist' in demo_data:
            fig = px.bar(
                x=list(demo_data['age_group_dist'].keys()),
                y=list(demo_data['age_group_dist'].values()),
                title='粉丝年龄段分布',
                labels={'x': '年龄段', 'y': '人数'}
            )
        elif demographic_type == 'city' and 'top_cities' in demo_data:
            fig = px.bar(
                x=list(demo_data['top_cities'].values()),
                y=list(demo_data['top_cities'].keys()),
                orientation='h',
                title='粉丝城市 TOP10',
                labels={'x': '人数', 'y': '城市'}
            )
        else:
            fig = go.Figure()
            fig.add_annotation(text="暂无数据", xref="paper", yref="paper", x=0.5, y=0.5)
        
        return fig
    
    def retention_analysis(self) -> Dict:
        """
        粉丝留存分析
        
        Returns:
            留存分析结果
        """
        if self.data is None or 'cohort' not in self.data.columns:
            raise ValueError("数据中缺少队列信息")
        
        df = self.data.copy()
        
        # 按队列分析留存
        cohort_data = df.groupby(['cohort', 'period'])['active_fans'].sum().unstack()
        
        # 计算留存率
        retention_rates = cohort_data.div(cohort_data.iloc[:, 0], axis=0) * 100
        
        return {
            'cohort_data': cohort_data,
            'retention_rates': retention_rates,
            'avg_retention_rate': retention_rates.mean().mean()
        }


def test_fan_analyzer():
    """测试粉丝分析器"""
    # 创建测试数据
    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    test_data = pd.DataFrame({
        'date': dates,
        'new_fans': np.random.randint(50, 500, 30),
        'unfollows': np.random.randint(10, 100, 30),
        'total_fans': np.random.randint(10000, 50000, 30),
        'interactions': np.random.randint(100, 5000, 30),
        'gender': np.random.choice(['男', '女'], 30),
        'age': np.random.randint(18, 60, 30),
        'city': np.random.choice(['北京', '上海', '广州', '深圳', '杭州'], 30)
    })
    
    analyzer = FanAnalyzer(test_data)
    
    # 测试各项功能
    growth_df = analyzer.analyze_growth_trend()
    assert len(growth_df) == 30, "增长趋势分析失败"
    
    metrics = analyzer.calculate_growth_metrics()
    assert 'total_fans' in metrics, "增长指标计算失败"
    
    demo = analyzer.analyze_demographics()
    assert 'gender_dist' in demo, "画像分析失败"
    
    print("✓ 粉丝分析器测试通过")
    return True


if __name__ == "__main__":
    test_fan_analyzer()
