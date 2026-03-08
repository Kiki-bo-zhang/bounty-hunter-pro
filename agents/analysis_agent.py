"""
AnalysisAgent - 技术分析 Agent
评估任务的技术匹配度和实现可行性
"""
from typing import Dict, List
from dataclasses import dataclass
import re

@dataclass
class TechAnalysis:
    """技术分析结果"""
    tech_match_score: float  # 0-1 技术匹配度
    complexity: str  # low/medium/high
    feasibility: float  # 0-1 可行性
    estimated_hours: int  # 预估工时
    required_skills: List[str]
    blockers: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "tech_match_score": round(self.tech_match_score, 2),
            "complexity": self.complexity,
            "feasibility": round(self.feasibility, 2),
            "estimated_hours": self.estimated_hours,
            "required_skills": self.required_skills,
            "blockers": self.blockers
        }

class AnalysisAgent:
    """分析 Agent - 评估任务技术可行性"""
    
    def __init__(self, my_skills: List[str] = None, config: Dict = None):
        """
        Args:
            my_skills: 我掌握的技术栈列表
            config: 配置参数
        """
        self.my_skills = my_skills or [
            'python', 'javascript', 'typescript', 'go', 
            'react', 'vue', 'nodejs', 'sql'
        ]
        self.config = config or {}
        
        # 复杂度关键词映射
        self.complexity_keywords = {
            'low': ['simple', 'easy', 'minor', 'fix', 'typo', 'doc', 'readme'],
            'high': ['refactor', 'architecture', 'redesign', 'complex', 'difficult', 
                     'database migration', 'schema change', 'api redesign']
        }
    
    def analyze_task(self, task: Dict, repo_info: Dict = None) -> TechAnalysis:
        """
        分析单个任务的技术可行性
        
        Args:
            task: BountyTask 字典
            repo_info: 仓库信息（可选）
        
        Returns:
            TechAnalysis: 技术分析结果
        """
        title = task.get('title', '')
        body = task.get('body', '')
        labels = task.get('labels', [])
        repo = task.get('repo', '')
        
        text = f"{title} {body}".lower()
        
        # 1. 检测技术栈
        detected_tech = self._detect_tech_stack(text, labels, repo)
        
        # 2. 计算技术匹配度
        tech_match = self._calculate_tech_match(detected_tech)
        
        # 3. 评估复杂度
        complexity = self._assess_complexity(text, labels)
        
        # 4. 估算工时
        estimated_hours = self._estimate_hours(complexity, text)
        
        # 5. 检查潜在阻碍
        blockers = self._identify_blockers(text, repo_info)
        
        # 6. 计算可行性
        feasibility = self._calculate_feasibility(
            tech_match, complexity, blockers
        )
        
        return TechAnalysis(
            tech_match_score=tech_match,
            complexity=complexity,
            feasibility=feasibility,
            estimated_hours=estimated_hours,
            required_skills=detected_tech,
            blockers=blockers
        )
    
    def _detect_tech_stack(self, text: str, labels: List[str], repo: str) -> List[str]:
        """检测任务涉及的技术栈"""
        tech_keywords = {
            'python': ['python', 'django', 'flask', 'fastapi', 'pandas', 'numpy'],
            'javascript': ['javascript', 'js', 'nodejs', 'node.js', 'express'],
            'typescript': ['typescript', 'ts', 'angular'],
            'react': ['react', 'reactjs', 'jsx'],
            'vue': ['vue', 'vuejs', 'nuxt'],
            'go': ['golang', 'go'],
            'rust': ['rust', 'cargo'],
            'cpp': ['c++', 'cpp', 'cplusplus'],
            'sql': ['sql', 'postgresql', 'mysql', 'sqlite'],
            'docker': ['docker', 'container'],
            'kubernetes': ['kubernetes', 'k8s'],
            'aws': ['aws', 'amazon web services', 's3', 'lambda'],
            'react-native': ['react native', 'react-native', 'mobile app']
        }
        
        detected = []
        text_lower = text.lower()
        
        for tech, keywords in tech_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                detected.append(tech)
        
        # 从标签检测
        for label in labels:
            label_lower = label.lower()
            for tech in tech_keywords.keys():
                if tech in label_lower and tech not in detected:
                    detected.append(tech)
        
        return detected
    
    def _calculate_tech_match(self, detected_tech: List[str]) -> float:
        """计算技术匹配度"""
        if not detected_tech:
            return 0.5  # 未知技术，中性评分
        
        matched = sum(1 for tech in detected_tech if tech in self.my_skills)
        return matched / len(detected_tech)
    
    def _assess_complexity(self, text: str, labels: List[str]) -> str:
        """评估任务复杂度"""
        text_lower = text.lower()
        
        # 检查标签
        for label in labels:
            label_lower = label.lower()
            if any(kw in label_lower for kw in self.complexity_keywords['low']):
                return 'low'
            if any(kw in label_lower for kw in self.complexity_keywords['high']):
                return 'high'
        
        # 检查文本
        low_count = sum(1 for kw in self.complexity_keywords['low'] if kw in text_lower)
        high_count = sum(1 for kw in self.complexity_keywords['high'] if kw in text_lower)
        
        # 检查其他指标
        if 'database' in text_lower and ('migration' in text_lower or 'schema' in text_lower):
            return 'high'
        if 'refactor' in text_lower or 'redesign' in text_lower:
            return 'high'
        
        if high_count > low_count:
            return 'high'
        elif low_count > high_count:
            return 'low'
        else:
            return 'medium'
    
    def _estimate_hours(self, complexity: str, text: str) -> int:
        """预估工时"""
        base_hours = {
            'low': 4,
            'medium': 16,
            'high': 40
        }
        
        hours = base_hours.get(complexity, 16)
        
        # 根据文本长度微调
        if len(text) > 2000:
            hours = int(hours * 1.3)
        
        return hours
    
    def _identify_blockers(self, text: str, repo_info: Dict = None) -> List[str]:
        """识别潜在阻碍"""
        blockers = []
        text_lower = text.lower()
        
        # 检查特定阻碍
        if 'windows' in text_lower and 'wsl' not in text_lower:
            blockers.append("Requires Windows environment")
        
        if 'hardware' in text_lower or 'device' in text_lower:
            blockers.append("Requires specific hardware")
        
        if 'macos' in text_lower or 'mac os' in text_lower:
            blockers.append("Requires macOS")
        
        if 'api key' in text_lower or 'apikey' in text_lower:
            blockers.append("Requires API key")
        
        if ' paid ' in text_lower or 'subscription' in text_lower:
            blockers.append("May require paid service")
        
        return blockers
    
    def _calculate_feasibility(
        self, 
        tech_match: float, 
        complexity: str, 
        blockers: List[str]
    ) -> float:
        """计算可行性分数"""
        base_score = tech_match
        
        # 复杂度调整
        complexity_penalty = {
            'low': 0.0,
            'medium': -0.1,
            'high': -0.2
        }
        base_score += complexity_penalty.get(complexity, 0)
        
        # 阻碍调整
        base_score -= len(blockers) * 0.1
        
        return max(0.0, min(1.0, base_score))
    
    def run(self, tasks: List[Dict]) -> Dict[str, TechAnalysis]:
        """
        批量分析任务
        
        Returns:
            Dict[task_id, TechAnalysis]: 分析结果映射
        """
        print(f"🔍 AnalysisAgent: Analyzing {len(tasks)} tasks...")
        
        results = {}
        for task in tasks:
            task_id = task.get('task_id')
            analysis = self.analyze_task(task)
            results[task_id] = analysis
        
        print(f"✅ AnalysisAgent: Completed analysis")
        return results
