"""
CompetitionAgent - 竞争分析 Agent
检查 PR 竞争情况、维护者活跃度等
"""
import requests
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class CompetitionAnalysis:
    """竞争分析结果"""
    open_prs_count: int
    pr_authors: List[str]
    maintainer_active: bool
    last_activity_days: int
    competition_level: str  # low/medium/high
    recommended: bool
    notes: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "open_prs_count": self.open_prs_count,
            "pr_authors": self.pr_authors,
            "maintainer_active": self.maintainer_active,
            "last_activity_days": self.last_activity_days,
            "competition_level": self.competition_level,
            "recommended": self.recommended,
            "notes": self.notes
        }

class CompetitionAgent:
    """竞争分析 Agent - 评估任务竞争情况"""
    
    def __init__(self, github_token: str):
        self.github_token = github_token
        self.headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json"
        }
    
    def analyze_competition(self, task: Dict) -> CompetitionAnalysis:
        """
        分析任务的竞争情况
        
        Args:
            task: BountyTask 字典
        
        Returns:
            CompetitionAnalysis: 竞争分析结果
        """
        repo = task.get('repo', '')
        issue_number = task.get('issue_number', 0)
        
        # 1. 检查相关 PR
        open_prs, pr_authors = self._check_related_prs(repo, issue_number)
        
        # 2. 检查维护者活跃度
        maintainer_active, last_activity = self._check_maintainer_activity(repo)
        
        # 3. 评估竞争级别
        competition_level = self._assess_competition_level(
            open_prs, maintainer_active, last_activity
        )
        
        # 4. 生成建议
        recommended, notes = self._generate_recommendation(
            open_prs, maintainer_active, last_activity, competition_level
        )
        
        return CompetitionAnalysis(
            open_prs_count=open_prs,
            pr_authors=pr_authors,
            maintainer_active=maintainer_active,
            last_activity_days=last_activity,
            competition_level=competition_level,
            recommended=recommended,
            notes=notes
        )
    
    def _check_related_prs(self, repo: str, issue_number: int) -> tuple:
        """检查与 Issue 相关的开放 PR"""
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
            related_count = 0
            authors = []
            
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
                    related_count += 1
                    author = pr.get('user', {}).get('login')
                    if author and author not in authors:
                        authors.append(author)
            
            return related_count, authors
            
        except Exception as e:
            print(f"Warning: Failed to check PRs for {repo}: {e}")
            return 0, []
    
    def _check_maintainer_activity(self, repo: str) -> tuple:
        """检查维护者活跃度"""
        try:
            # 获取最近的 commits
            url = f"https://api.github.com/repos/{repo}/commits"
            params = {"per_page": 5}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            
            commits = response.json()
            
            if not commits:
                return False, 999
            
            # 计算最近一次活动距今多少天
            from datetime import datetime
            
            latest_commit = commits[0]
            commit_date = latest_commit.get('commit', {}).get('committer', {}).get('date', '')
            
            if commit_date:
                commit_time = datetime.fromisoformat(commit_date.replace('Z', '+00:00'))
                now = datetime.now(commit_time.tzinfo)
                days_ago = (now - commit_time).days
                
                # 30天内有活动视为活跃
                return days_ago < 30, days_ago
            
            return False, 999
            
        except Exception as e:
            print(f"Warning: Failed to check maintainer activity for {repo}: {e}")
            return False, 999
    
    def _assess_competition_level(
        self, 
        open_prs: int, 
        maintainer_active: bool, 
        last_activity: int
    ) -> str:
        """评估竞争级别"""
        if open_prs >= 3:
            return 'high'
        elif open_prs >= 1:
            return 'medium'
        elif not maintainer_active and last_activity > 90:
            return 'high'  # 项目可能不活跃
        else:
            return 'low'
    
    def _generate_recommendation(
        self,
        open_prs: int,
        maintainer_active: bool,
        last_activity: int,
        competition_level: str
    ) -> tuple:
        """生成推荐建议"""
        notes = []
        recommended = True
        
        if open_prs > 0:
            notes.append(f"⚠️ Found {open_prs} open PR(s) referencing this issue")
            if open_prs >= 3:
                recommended = False
                notes.append("❌ Too much competition (3+ PRs)")
        else:
            notes.append("✅ No competing PRs found")
        
        if not maintainer_active:
            notes.append(f"⚠️ Repository inactive for {last_activity} days")
            if last_activity > 90:
                recommended = False
                notes.append("❌ Repository may be abandoned")
        else:
            notes.append("✅ Repository is actively maintained")
        
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
            
            # 添加短暂延迟避免 API 限制
            import time
            time.sleep(0.5)
        
        print(f"✅ CompetitionAgent: Completed analysis")
        return results
