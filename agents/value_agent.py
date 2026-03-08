"""
ValueAgent - 价值评估 Agent
评估赏金任务的性价比和风险
"""
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class ValueAssessment:
    """价值评估结果"""
    value_score: float  # 0-10 价值分数
    risk_level: str  # low/medium/high
    risk_factors: List[str]
    hourly_rate: float  # 预估时薪
    recommendation: str  # strongly_recommend/recommend/consider/avoid
    notes: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "value_score": round(self.value_score, 1),
            "risk_level": self.risk_level,
            "risk_factors": self.risk_factors,
            "hourly_rate": round(self.hourly_rate, 2),
            "recommendation": self.recommendation,
            "notes": self.notes
        }

class ValueAgent:
    """价值评估 Agent - 评估赏金任务性价比"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.min_acceptable_rate = self.config.get('min_hourly_rate', 10)
    
    def assess_value(
        self, 
        task: Dict, 
        tech_analysis: Dict = None, 
        competition_analysis: Dict = None
    ) -> ValueAssessment:
        """
        评估任务价值
        
        Args:
            task: BountyTask 字典
            tech_analysis: 技术分析结果（可选）
            competition_analysis: 竞争分析结果（可选）
        
        Returns:
            ValueAssessment: 价值评估结果
        """
        bounty = task.get('bounty', {})
        amount = bounty.get('amount', 0)
        currency = bounty.get('currency', 'USD')
        
        # 1. 标准化赏金金额（转换为 USD 估算）
        usd_amount = self._normalize_to_usd(amount, currency)
        
        # 2. 估算工时
        estimated_hours = self._get_estimated_hours(tech_analysis)
        
        # 3. 计算时薪
        hourly_rate = usd_amount / estimated_hours if estimated_hours > 0 else 0
        
        # 4. 识别风险因素
        risk_factors = self._identify_risk_factors(task, currency)
        
        # 5. 评估风险级别
        risk_level = self._assess_risk_level(risk_factors, competition_analysis)
        
        # 6. 计算价值分数
        value_score = self._calculate_value_score(
            usd_amount, hourly_rate, risk_level, competition_analysis
        )
        
        # 7. 生成推荐
        recommendation, notes = self._generate_recommendation(
            value_score, hourly_rate, risk_level, risk_factors
        )
        
        return ValueAssessment(
            value_score=value_score,
            risk_level=risk_level,
            risk_factors=risk_factors,
            hourly_rate=hourly_rate,
            recommendation=recommendation,
            notes=notes
        )
    
    def _normalize_to_usd(self, amount: float, currency: str) -> float:
        """将其他货币转换为 USD 估算"""
        # 简化汇率（实际应使用实时汇率 API）
        rates = {
            'USD': 1.0,
            'USDC': 1.0,
            'EUR': 1.08,
            'GBP': 1.27,
            'CNY': 0.14,
            'JPY': 0.0067,
            'RTC': 0.10,  # RustChain Token
            'LTD': 0.005,  # La Tanda Token (假设)
        }
        
        rate = rates.get(currency.upper(), 1.0)
        return amount * rate
    
    def _get_estimated_hours(self, tech_analysis=None) -> int:
        """获取预估工时 - 支持传入字典或对象"""
        if tech_analysis is None:
            return 16
        
        # 处理可能是字典或对象的情况
        if isinstance(tech_analysis, dict):
            return tech_analysis.get('estimated_hours', 16)
        else:
            # 假设是 TechAnalysis 对象
            return getattr(tech_analysis, 'estimated_hours', 16)
    
    def _identify_risk_factors(self, task: Dict, currency: str) -> List[str]:
        """识别风险因素"""
        risks = []
        
        # 货币风险
        stable_currencies = ['USD', 'USDC', 'EUR', 'GBP']
        if currency not in stable_currencies:
            if currency in ['RTC', 'LTD', 'KARMA']:
                risks.append(f"Token payment ({currency}) - value may fluctuate")
            else:
                risks.append(f"Non-standard currency: {currency}")
        
        # 金额风险
        bounty = task.get('bounty', {})
        amount = bounty.get('amount', 0)
        if amount < 20:
            risks.append("Low bounty amount (< $20)")
        
        # 项目风险
        repo = task.get('repo', '')
        if not repo:
            risks.append("Unknown repository")
        
        # 检查问题年龄
        created_at = task.get('created_at', '')
        if created_at:
            from datetime import datetime
            try:
                created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                now = datetime.now(created.tzinfo)
                age_days = (now - created).days
                
                if age_days > 365:
                    risks.append(f"Very old issue ({age_days} days) - may be abandoned")
                elif age_days > 180:
                    risks.append(f"Old issue ({age_days} days)")
            except:
                pass
        
        return risks
    
    def _assess_risk_level(
        self, 
        risk_factors: List[str], 
        competition_analysis = None
    ) -> str:
        """评估风险级别 - 支持传入字典或对象"""
        score = 0
        
        # 风险因素评分
        for risk in risk_factors:
            if 'Token' in risk or 'fluctuate' in risk:
                score += 2
            elif 'Low bounty' in risk:
                score += 1
            elif 'old issue' in risk.lower():
                score += 1
            elif 'abandoned' in risk.lower():
                score += 3
        
        # 竞争因素 - 处理对象或字典
        if competition_analysis:
            if isinstance(competition_analysis, dict):
                recommended = competition_analysis.get('recommended', True)
                comp_level = competition_analysis.get('competition_level')
            else:
                recommended = getattr(competition_analysis, 'recommended', True)
                comp_level = getattr(competition_analysis, 'competition_level', None)
            
            if not recommended:
                score += 2
            if comp_level == 'high':
                score += 2
        
        if score >= 4:
            return 'high'
        elif score >= 2:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_value_score(
        self,
        amount: float,
        hourly_rate: float,
        risk_level: str,
        competition_analysis = None
    ) -> float:
        """计算价值分数 (0-10) - 支持传入字典或对象"""
        # 基础分数基于时薪
        if hourly_rate >= 50:
            base_score = 10
        elif hourly_rate >= 30:
            base_score = 8
        elif hourly_rate >= 20:
            base_score = 6
        elif hourly_rate >= 10:
            base_score = 4
        else:
            base_score = 2
        
        # 金额加分
        if amount >= 200:
            base_score += 1
        elif amount >= 100:
            base_score += 0.5
        
        # 风险调整
        risk_penalty = {'low': 0, 'medium': -1, 'high': -2}
        base_score += risk_penalty.get(risk_level, 0)
        
        # 竞争调整 - 处理对象或字典
        if competition_analysis:
            if isinstance(competition_analysis, dict):
                comp_level = competition_analysis.get('competition_level')
            else:
                comp_level = getattr(competition_analysis, 'competition_level', None)
            
            if comp_level == 'low':
                base_score += 0.5
            elif comp_level == 'high':
                base_score -= 1
        
        return max(0, min(10, base_score))
    
    def _generate_recommendation(
        self,
        value_score: float,
        hourly_rate: float,
        risk_level: str,
        risk_factors: List[str]
    ) -> tuple:
        """生成推荐建议"""
        notes = []
        
        # 时薪建议
        if hourly_rate >= 50:
            notes.append(f"✅ Excellent hourly rate: ${hourly_rate:.2f}/h")
            recommendation = 'strongly_recommend'
        elif hourly_rate >= 30:
            notes.append(f"✅ Good hourly rate: ${hourly_rate:.2f}/h")
            recommendation = 'recommend'
        elif hourly_rate >= self.min_acceptable_rate:
            notes.append(f"⚠️ Acceptable hourly rate: ${hourly_rate:.2f}/h")
            recommendation = 'consider'
        else:
            notes.append(f"❌ Low hourly rate: ${hourly_rate:.2f}/h")
            recommendation = 'avoid'
        
        # 风险建议
        if risk_level == 'high':
            notes.append("❌ High risk factors identified")
            if recommendation != 'avoid':
                recommendation = 'avoid'
        elif risk_level == 'medium':
            notes.append("⚠️ Medium risk - proceed with caution")
        else:
            notes.append("✅ Low risk")
        
        # 列出具体风险
        if risk_factors:
            notes.append("Risk factors:")
            for risk in risk_factors:
                notes.append(f"  - {risk}")
        
        return recommendation, notes
    
    def run(
        self, 
        tasks: List[Dict], 
        tech_analyses: Dict = None, 
        competition_analyses: Dict = None
    ) -> Dict[str, ValueAssessment]:
        """批量评估价值"""
        print(f"💰 ValueAgent: Assessing value for {len(tasks)} tasks...")
        
        results = {}
        for task in tasks:
            task_id = task.get('task_id')
            tech = tech_analyses.get(task_id) if tech_analyses else None
            comp = competition_analyses.get(task_id) if competition_analyses else None
            
            assessment = self.assess_value(task, tech, comp)
            results[task_id] = assessment
        
        print(f"✅ ValueAgent: Completed assessment")
        return results
