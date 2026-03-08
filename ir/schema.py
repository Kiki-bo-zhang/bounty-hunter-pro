"""
IR Schema - 赏金任务中间表示定义
基于 BettaFish 的 IR 设计理念
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class BountyInfo:
    """赏金信息"""
    amount: float
    currency: str
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class TechAnalysisIR:
    """技术分析 IR"""
    tech_match_score: float
    complexity: str
    feasibility: float
    estimated_hours: int
    required_skills: List[str]
    blockers: List[str]
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class CompetitionAnalysisIR:
    """竞争分析 IR"""
    open_prs_count: int
    pr_authors: List[str]
    maintainer_active: bool
    last_activity_days: int
    competition_level: str
    recommended: bool
    notes: List[str]
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class ValueAssessmentIR:
    """价值评估 IR"""
    value_score: float
    risk_level: str
    risk_factors: List[str]
    hourly_rate: float
    recommendation: str
    notes: List[str]
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class BountyTaskIR:
    """
    赏金任务中间表示 (Intermediate Representation)
    
    这是所有 Agent 分析结果的统一表示，支持多格式渲染
    """
    # 基本信息
    task_id: str
    title: str
    url: str
    repo: str
    issue_number: int
    
    # 原始信息
    bounty: BountyInfo
    labels: List[str]
    status: str
    created_at: str
    updated_at: str
    comments_count: int
    body: str
    
    # Agent 分析结果
    tech_analysis: TechAnalysisIR
    competition_analysis: CompetitionAnalysisIR
    value_assessment: ValueAssessmentIR
    
    # 综合评分
    final_score: float
    priority: str  # high/medium/low
    
    # 元数据
    generated_at: str
    version: str = "1.0"
    
    def to_dict(self) -> Dict:
        """转换为字典，用于 JSON 序列化"""
        return {
            "task_id": self.task_id,
            "title": self.title,
            "url": self.url,
            "repo": self.repo,
            "issue_number": self.issue_number,
            "bounty": self.bounty.to_dict(),
            "labels": self.labels,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "comments_count": self.comments_count,
            "body": self.body[:1000] if self.body else "",  # 限制长度
            "analysis": {
                "tech": self.tech_analysis.to_dict(),
                "competition": self.competition_analysis.to_dict(),
                "value": self.value_assessment.to_dict()
            },
            "final_score": round(self.final_score, 1),
            "priority": self.priority,
            "generated_at": self.generated_at,
            "version": self.version
        }
    
    @classmethod
    def from_task_and_analyses(
        cls,
        task: Dict,
        tech_analysis: Dict,
        competition_analysis: Dict,
        value_assessment: Dict
    ) -> 'BountyTaskIR':
        """
        从原始任务和 Agent 分析结果创建 IR
        
        Args:
            task: 原始任务字典
            tech_analysis: AnalysisAgent 结果
            competition_analysis: CompetitionAgent 结果
            value_assessment: ValueAgent 结果
        
        Returns:
            BountyTaskIR: 中间表示对象
        """
        bounty = BountyInfo(
            amount=task.get('bounty', {}).get('amount', 0),
            currency=task.get('bounty', {}).get('currency', 'UNKNOWN')
        )
        
        tech = TechAnalysisIR(
            tech_match_score=tech_analysis.get('tech_match_score', 0),
            complexity=tech_analysis.get('complexity', 'medium'),
            feasibility=tech_analysis.get('feasibility', 0),
            estimated_hours=tech_analysis.get('estimated_hours', 16),
            required_skills=tech_analysis.get('required_skills', []),
            blockers=tech_analysis.get('blockers', [])
        )
        
        comp = CompetitionAnalysisIR(
            open_prs_count=competition_analysis.get('open_prs_count', 0),
            pr_authors=competition_analysis.get('pr_authors', []),
            maintainer_active=competition_analysis.get('maintainer_active', False),
            last_activity_days=competition_analysis.get('last_activity_days', 999),
            competition_level=competition_analysis.get('competition_level', 'unknown'),
            recommended=competition_analysis.get('recommended', False),
            notes=competition_analysis.get('notes', [])
        )
        
        value = ValueAssessmentIR(
            value_score=value_assessment.get('value_score', 0),
            risk_level=value_assessment.get('risk_level', 'high'),
            risk_factors=value_assessment.get('risk_factors', []),
            hourly_rate=value_assessment.get('hourly_rate', 0),
            recommendation=value_assessment.get('recommendation', 'avoid'),
            notes=value_assessment.get('notes', [])
        )
        
        # 计算最终分数
        final_score = cls._calculate_final_score(tech, comp, value)
        
        # 确定优先级
        priority = cls._determine_priority(final_score, value, comp)
        
        return cls(
            task_id=task.get('task_id', ''),
            title=task.get('title', ''),
            url=task.get('url', ''),
            repo=task.get('repo', ''),
            issue_number=task.get('issue_number', 0),
            bounty=bounty,
            labels=task.get('labels', []),
            status=task.get('status', 'open'),
            created_at=task.get('created_at', ''),
            updated_at=task.get('updated_at', ''),
            comments_count=task.get('comments_count', 0),
            body=task.get('body', ''),
            tech_analysis=tech,
            competition_analysis=comp,
            value_assessment=value,
            final_score=final_score,
            priority=priority,
            generated_at=datetime.now().isoformat()
        )
    
    @staticmethod
    def _calculate_final_score(
        tech: TechAnalysisIR,
        comp: CompetitionAnalysisIR,
        value: ValueAssessmentIR
    ) -> float:
        """计算综合分数"""
        # 权重配置
        weights = {
            'value': 0.4,
            'tech': 0.3,
            'competition': 0.3
        }
        
        # 价值分数 (0-10)
        value_score = value.value_score
        
        # 技术匹配分数 (0-10)
        tech_score = tech.tech_match_score * 10
        
        # 竞争分数 (0-10)
        comp_scores = {'low': 10, 'medium': 6, 'high': 2}
        comp_score = comp_scores.get(comp.competition_level, 5)
        if not comp.recommended:
            comp_score -= 3
        
        # 加权计算
        final = (
            value_score * weights['value'] +
            tech_score * weights['tech'] +
            comp_score * weights['competition']
        )
        
        return max(0, min(10, final))
    
    @staticmethod
    def _determine_priority(
        final_score: float,
        value: ValueAssessmentIR,
        comp: CompetitionAnalysisIR
    ) -> str:
        """确定任务优先级"""
        if final_score >= 8 and value.risk_level == 'low' and comp.competition_level == 'low':
            return 'high'
        elif final_score >= 6 and value.risk_level != 'high':
            return 'medium'
        else:
            return 'low'
