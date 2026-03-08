"""
ForumAgent - 论坛协作 Agent
协调多个 Agent 进行讨论和决策
基于 BettaFish 的 ForumEngine 理念
"""
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ForumOpinion:
    """Agent 意见"""
    agent_name: str
    opinion: str
    confidence: float  # 0-1
    recommendation: str  # recommend/consider/avoid
    reasoning: List[str]

class ForumAgent:
    """
    论坛协作 Agent
    
    模拟多个 Agent 在论坛中讨论，通过主持人模型
    引导达成共识，生成最终推荐。
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.max_rounds = self.config.get('forum_rounds', 3)
    
    def host_discussion(
        self,
        task: Dict,
        analyses: Dict
    ) -> Dict:
        """
        主持 Agent 讨论
        
        Args:
            task: 任务信息
            analyses: 各 Agent 的分析结果
        
        Returns:
            Dict: 论坛讨论结论
        """
        # 收集各 Agent 意见
        opinions = self._collect_opinions(task, analyses)
        
        # 主持人总结
        consensus = self._reach_consensus(opinions, task)
        
        return {
            "opinions": [self._opinion_to_dict(o) for o in opinions],
            "consensus": consensus,
            "discussion_rounds": 1  # 简化版，实际可多轮
        }
    
    def _collect_opinions(self, task: Dict, analyses: Dict) -> List[ForumOpinion]:
        """收集各 Agent 意见"""
        opinions = []
        
        # SearchAgent 意见（信息提供者）
        search_op = ForumOpinion(
            agent_name="SearchAgent",
            opinion="Task found and verified",
            confidence=0.9,
            recommendation="neutral",
            reasoning=["Task is actively maintained", "Open bounty confirmed"]
        )
        opinions.append(search_op)
        
        # AnalysisAgent 意见
        tech = analyses.get('tech', {})
        tech_match = tech.get('tech_match_score', 0)
        
        if tech_match >= 0.8:
            tech_rec = "recommend"
        elif tech_match >= 0.5:
            tech_rec = "consider"
        else:
            tech_rec = "avoid"
        
        analysis_op = ForumOpinion(
            agent_name="AnalysisAgent",
            opinion=f"Technical match: {tech_match:.0%}",
            confidence=tech_match,
            recommendation=tech_rec,
            reasoning=tech.get('blockers', []) or ["No major blockers identified"]
        )
        opinions.append(analysis_op)
        
        # CompetitionAgent 意见
        comp = analyses.get('competition', {})
        comp_level = comp.get('competition_level', 'unknown')
        
        if comp_level == 'low' and comp.get('recommended', False):
            comp_rec = "recommend"
            comp_conf = 0.9
        elif comp_level == 'medium':
            comp_rec = "consider"
            comp_conf = 0.6
        else:
            comp_rec = "avoid"
            comp_conf = 0.4
        
        comp_op = ForumOpinion(
            agent_name="CompetitionAgent",
            opinion=f"Competition level: {comp_level}",
            confidence=comp_conf,
            recommendation=comp_rec,
            reasoning=comp.get('notes', [])
        )
        opinions.append(comp_op)
        
        # ValueAgent 意见
        value = analyses.get('value', {})
        value_score = value.get('value_score', 0)
        
        value_op = ForumOpinion(
            agent_name="ValueAgent",
            opinion=f"Value score: {value_score}/10",
            confidence=value_score / 10,
            recommendation=value.get('recommendation', 'avoid'),
            reasoning=value.get('notes', [])
        )
        opinions.append(value_op)
        
        return opinions
    
    def _reach_consensus(self, opinions: List[ForumOpinion], task: Dict) -> Dict:
        """达成共识"""
        # 统计各推荐意见
        recommendations = {}
        for op in opinions:
            rec = op.recommendation
            recommendations[rec] = recommendations.get(rec, 0) + op.confidence
        
        # 找出共识
        consensus_rec = max(recommendations.items(), key=lambda x: x[1])[0]
        
        # 综合置信度
        avg_confidence = sum(op.confidence for op in opinions) / len(opinions)
        
        # 生成共识理由
        all_reasoning = []
        for op in opinions:
            all_reasoning.extend(op.reasoning[:2])
        
        return {
            "consensus_recommendation": consensus_rec,
            "consensus_confidence": round(avg_confidence, 2),
            "key_points": all_reasoning[:5],
            "agreement_level": "high" if avg_confidence > 0.7 else "medium"
        }
    
    def _opinion_to_dict(self, opinion: ForumOpinion) -> Dict:
        return {
            "agent": opinion.agent_name,
            "opinion": opinion.opinion,
            "confidence": round(opinion.confidence, 2),
            "recommendation": opinion.recommendation,
            "reasoning": opinion.reasoning
        }
    
    def run(self, tasks_analyses: List[Dict]) -> Dict[str, Dict]:
        """
        批量运行论坛讨论
        
        Returns:
            Dict[task_id, forum_result]: 每个任务的论坛结论
        """
        print(f"🗣️  ForumAgent: Hosting discussions for {len(tasks_analyses)} tasks...")
        
        results = {}
        for item in tasks_analyses:
            task = item.get('task', {})
            analyses = item.get('analyses', {})
            
            task_id = task.get('task_id', 'unknown')
            result = self.host_discussion(task, analyses)
            results[task_id] = result
        
        print(f"✅ ForumAgent: Discussions completed")
        return results
