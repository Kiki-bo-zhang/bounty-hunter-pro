"""
CompetitionAgent - 竞争分析 Agent (增强版)
检查 PR 竞争情况、PR 质量、维护者活跃度等
"""
import requests
from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CompetitionAnalysis:
    """竞争分析结果"""
    open_prs_count: int
    high_quality_prs: int  # 高质量PR数量
    low_quality_prs: int   # 低质量PR数量
    pr_authors: List[str]
    pr_details: List[Dict]  # PR详情列表
    maintainer_active: bool
    last_activity_days: int
    competition_level: str  # low/medium/high
    recommended: bool
    notes: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "open_prs_count": self.open_prs_count,
            "high_quality_prs": self.high_quality_prs,
            "low_quality_prs": self.low_quality_prs,
            "pr_authors": self.pr_authors,
            "pr_details": self.pr_details,
            "maintainer_active": self.maintainer_active,
            "last_activity_days": self.last_activity_days,
            "competition_level": self.competition_level,
            "recommended": self.recommended,
            "notes": self.notes
        }

class CompetitionAgent:
    """竞争分析 Agent - 评估任务竞争情况（支持PR质量检查）"""
    
    def __init__(self, github_token: str, config: Dict = None):
        self.github_token = github_token
        self.headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json"
        }
        self.config = config or {}
        # PR质量阈值配置
        self.pr_quality_config = self.config.get('pr_quality_threshold', {
            'stale_days': 7,
            'min_description_length': 50,
            'skip_drafts': True
        })
    
    def analyze_competition(self, task: Dict) -> CompetitionAnalysis:
        """
        分析任务的竞争情况（含PR质量检查）
        
        Args:
            task: BountyTask 字典
        
        Returns:
            CompetitionAnalysis: 竞争分析结果
        """
        repo = task.get('repo', '')
        issue_number = task.get('issue_number', 0)
        
        # 1. 检查相关 PR（含详情）
        all_prs, pr_details = self._check_related_prs_with_details(repo, issue_number)
        
        # 2. 评估PR质量
        high_quality_prs, low_quality_prs, pr_quality_notes = self._assess_pr_quality(
            pr_details
        )
        
        # 3. 提取作者列表
        pr_authors = list(set(pr['author'] for pr in pr_details if pr.get('author')))
        
        # 4. 检查维护者活跃度
        maintainer_active, last_activity = self._check_maintainer_activity(repo)
        
        # 5. 评估竞争级别（基于高质量PR数量）
        competition_level = self._assess_competition_level(
            high_quality_prs, low_quality_prs, maintainer_active, last_activity
        )
        
        # 6. 生成建议
        recommended, notes = self._generate_recommendation(
            all_prs, high_quality_prs, low_quality_prs, 
            maintainer_active, last_activity, competition_level, pr_quality_notes
        )
        
        return CompetitionAnalysis(
            open_prs_count=all_prs,
            high_quality_prs=high_quality_prs,
            low_quality_prs=low_quality_prs,
            pr_authors=pr_authors,
            pr_details=pr_details,
            maintainer_active=maintainer_active,
            last_activity_days=last_activity,
            competition_level=competition_level,
            recommended=recommended,
            notes=notes
        )
    
    def _check_related_prs_with_details(self, repo: str, issue_number: int) -> tuple:
        """检查与 Issue 相关的开放 PR，返回详细信息"""
        try:
            url = f"https://api.github.com/repos/{repo}/pulls"
            params = {
                "state": "open",
                "per_page": 100
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            
            prs = response.json()
            
            # 查找引用该 Issue 的 PR
            related_prs = []
            
            for pr in prs:
                # 检查标题和正文是否包含 Issue 编号
                title = pr.get('title', '').lower()
                body = pr.get('body', '') or ''
                body_lower = body.lower()
                
                issue_refs = [
                    f"#{issue_number}",
                    f"fixes #{issue_number}",
                    f"closes #{issue_number}",
                    f"resolve #{issue_number}"
                ]
                
                if any(ref in title or ref in body_lower for ref in issue_refs):
                    pr_detail = {
                        'number': pr.get('number'),
                        'title': pr.get('title'),
                        'author': pr.get('user', {}).get('login'),
                        'created_at': pr.get('created_at'),
                        'updated_at': pr.get('updated_at'),
                        'body': pr.get('body', ''),
                        'draft': pr.get('draft', False),
                        'additions': pr.get('additions', 0),
                        'deletions': pr.get('deletions', 0),
                        'changed_files': pr.get('changed_files', 0)
                    }
                    related_prs.append(pr_detail)
            
            return len(related_prs), related_prs
            
        except Exception as e:
            print(f"Warning: Failed to check PRs for {repo}: {e}")
            return 0, []
    
    def _assess_pr_quality(self, pr_details: List[Dict]) -> tuple:
        """
        评估PR质量
        
        返回：(高质量PR数量, 低质量PR数量, 质量评估说明列表)
        """
        high_quality = []
        low_quality = []
        notes = []
        
        stale_days = self.pr_quality_config.get('stale_days', 7)
        min_desc_len = self.pr_quality_config.get('min_description_length', 50)
        skip_drafts = self.pr_quality_config.get('skip_drafts', True)
        
        for pr in pr_details:
            quality_score = 100
            quality_issues = []
            
            # 检查1: 是否为 Draft
            if pr.get('draft') and skip_drafts:
                quality_score -= 30
                quality_issues.append("is draft")
            
            # 检查2: PR年龄（最后更新时间）
            updated_at = pr.get('updated_at', '')
            if updated_at:
                updated_time = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                now = datetime.now(updated_time.tzinfo)
                days_since_update = (now - updated_time).days
                
                if days_since_update > stale_days:
                    quality_score -= 40
                    quality_issues.append(f"stale ({days_since_update} days)")
            
            # 检查3: 描述长度
            body = pr.get('body', '') or ''
            if len(body) < min_desc_len:
                quality_score -= 20
                quality_issues.append(f"short description ({len(body)} chars)")
            
            # 检查4: 代码改动量（过少可能不完整）
            if pr.get('changed_files', 0) == 0:
                quality_score -= 50
                quality_issues.append("no file changes")
            elif pr.get('changed_files', 0) < 2:
                quality_score -= 10
                quality_issues.append("minimal changes")
            
            # 分类
            if quality_score >= 70:
                high_quality.append(pr)
            else:
                low_quality.append(pr)
                notes.append(f"PR #{pr['number']}: low quality ({', '.join(quality_issues)})")
        
        return len(high_quality), len(low_quality), notes
    
    def _check_maintainer_activity(self, repo: str) -> tuple:
        """检查维护者活跃度"""
        try:
            url = f"https://api.github.com/repos/{repo}/commits"
            params = {"per_page": 5}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            
            commits = response.json()
            
            if not commits:
                return False, 999
            
            latest_commit = commits[0]
            commit_date = latest_commit.get('commit', {}).get('committer', {}).get('date', '')
            
            if commit_date:
                commit_time = datetime.fromisoformat(commit_date.replace('Z', '+00:00'))
                now = datetime.now(commit_time.tzinfo)
                days_ago = (now - commit_time).days
                
                return days_ago < 30, days_ago
            
            return False, 999
            
        except Exception as e:
            print(f"Warning: Failed to check maintainer activity for {repo}: {e}")
            return False, 999
    
    def _assess_competition_level(
        self, 
        high_quality_prs: int,
        low_quality_prs: int,
        maintainer_active: bool, 
        last_activity: int
    ) -> str:
        """评估竞争级别（基于高质量PR数量）"""
        # 主要基于高质量PR判断竞争
        if high_quality_prs >= 3:
            return 'high'
        elif high_quality_prs >= 1:
            return 'medium'
        # 如果只有低质量PR，竞争较低
        elif low_quality_prs > 0:
            return 'low'  # 低质量PR不构成真正竞争
        elif not maintainer_active and last_activity > 90:
            return 'high'  # 项目可能不活跃
        else:
            return 'low'
    
    def _generate_recommendation(
        self,
        all_prs: int,
        high_quality_prs: int,
        low_quality_prs: int,
        maintainer_active: bool,
        last_activity: int,
        competition_level: str,
        pr_quality_notes: List[str]
    ) -> tuple:
        """生成推荐建议"""
        notes = []
        recommended = True
        
        # PR统计
        if all_prs > 0:
            notes.append(f"📊 Found {all_prs} PR(s): {high_quality_prs} high-quality, {low_quality_prs} low-quality")
            
            if high_quality_prs >= 3:
                recommended = False
                notes.append("❌ Too many high-quality competing PRs (3+)")
            elif high_quality_prs > 0:
                notes.append(f"⚠️ {high_quality_prs} high-quality PR(s) - strong competition")
            elif low_quality_prs > 0:
                notes.append("✅ Only low-quality PRs - opportunity exists")
        else:
            notes.append("✅ No competing PRs found")
        
        # 添加PR质量详情
        if pr_quality_notes:
            notes.append("📋 Low-quality PR reasons:")
            for note in pr_quality_notes[:3]:  # 最多显示3个
                notes.append(f"  - {note}")
        
        # 维护者活跃度
        if not maintainer_active:
            notes.append(f"⚠️ Repository inactive for {last_activity} days")
            if last_activity > 90:
                recommended = False
                notes.append("❌ Repository may be abandoned")
        else:
            notes.append("✅ Repository is actively maintained")
        
        # 竞争级别总结
        if competition_level == 'high':
            notes.append("❌ High competition - not recommended")
        elif competition_level == 'medium':
            notes.append("⚠️ Medium competition - proceed with caution")
        else:
            notes.append("✅ Low competition - good opportunity")
        
        return recommended, notes
    
    def run(self, tasks: List[Dict]) -> Dict[str, CompetitionAnalysis]:
        """批量分析竞争情况"""
        print(f"🔍 CompetitionAgent: Analyzing competition for {len(tasks)} tasks...")
        
        results = {}
        for i, task in enumerate(tasks):
            task_id = task.get('task_id')
            print(f"  [{i+1}/{len(tasks)}] Checking {task_id}...")
            
            analysis = self.analyze_competition(task)
            results[task_id] = analysis
            
            # 显示结果摘要
            print(f"    PRs: {analysis.open_prs_count} total, "
                  f"{analysis.high_quality_prs} high-quality, "
                  f"{analysis.low_quality_prs} low-quality")
            
            # 添加短暂延迟避免 API 限制
            import time
            time.sleep(0.5)
        
        print(f"✅ CompetitionAgent: Completed analysis")
        return results
