"""
SearchAgent - 多平台赏金任务搜索 Agent
"""
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import time

@dataclass
class BountyTask:
    """赏金任务数据类"""
    task_id: str
    title: str
    url: str
    repo: str
    issue_number: int
    bounty_amount: float
    currency: str
    labels: List[str]
    status: str
    created_at: str
    updated_at: str
    comments_count: int
    body: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "url": self.url,
            "repo": self.repo,
            "issue_number": self.issue_number,
            "bounty": {
                "amount": self.bounty_amount,
                "currency": self.currency
            },
            "labels": self.labels,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "comments_count": self.comments_count,
            "body": self.body[:500] if self.body else ""
        }

class SearchAgent:
    """搜索 Agent - 负责多平台赏金任务搜索"""
    
    def __init__(self, github_token: str, config: Dict = None):
        self.github_token = github_token
        self.headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json"
        }
        self.config = config or {}
        self.min_bounty = self.config.get('min_bounty', 20)
        self.max_tasks = self.config.get('max_tasks_per_run', 50)
    
    def search_github_bounties(
        self, 
        keywords: List[str] = None,
        languages: List[str] = None,
        min_bounty: int = None
    ) -> List[BountyTask]:
        """
        搜索 GitHub 上的赏金任务
        
        Args:
            keywords: 搜索关键词列表
            languages: 编程语言过滤
            min_bounty: 最小赏金金额
        
        Returns:
            List[BountyTask]: 赏金任务列表
        """
        min_bounty = min_bounty or self.min_bounty
        tasks = []
        
        # 构建搜索查询
        query_parts = ["label:bounty", "is:open", f"updated:>{self._get_date_limit()}"]
        
        if languages:
            for lang in languages:
                query_parts.append(f"language:{lang}")
        
        query = " ".join(query_parts)
        
        try:
            # GitHub Search API
            url = "https://api.github.com/search/issues"
            params = {
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": min(self.max_tasks, 100)
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            items = data.get('items', [])
            
            for item in items:
                task = self._parse_github_issue(item)
                if task and task.bounty_amount >= min_bounty:
                    tasks.append(task)
            
            print(f"✅ SearchAgent: Found {len(tasks)} bounty tasks")
            return tasks
            
        except Exception as e:
            print(f"❌ SearchAgent Error: {e}")
            return []
    
    def _parse_github_issue(self, item: Dict) -> Optional[BountyTask]:
        """解析 GitHub Issue 为 BountyTask"""
        try:
            # 提取赏金金额
            bounty_amount, currency = self._extract_bounty_info(item)
            
            if bounty_amount < self.min_bounty:
                return None
            
            repo_url = item.get('repository_url', '')
            repo = repo_url.replace('https://api.github.com/repos/', '') if repo_url else ''
            issue_number = item.get('number', 0)
            
            return BountyTask(
                task_id=f"{repo}#{issue_number}",
                title=item.get('title', ''),
                url=item.get('html_url', ''),
                repo=repo,
                issue_number=issue_number,
                bounty_amount=bounty_amount,
                currency=currency,
                labels=[label['name'] for label in item.get('labels', [])],
                status=item.get('state', 'open'),
                created_at=item.get('created_at', ''),
                updated_at=item.get('updated_at', ''),
                comments_count=item.get('comments', 0),
                body=item.get('body', '')
            )
        except Exception as e:
            print(f"Warning: Failed to parse issue: {e}")
            return None
    
    def _extract_bounty_info(self, item: Dict) -> tuple:
        """从 Issue 中提取赏金信息"""
        labels = item.get('labels', [])
        
        # 从标签中提取赏金
        for label in labels:
            name = label.get('name', '')
            if name.startswith('$'):
                try:
                    amount = float(name.replace('$', '').replace(',', ''))
                    return amount, 'USD'
                except:
                    pass
            elif 'bounty' in name.lower():
                # 尝试从标题或正文提取
                title = item.get('title', '')
                body = item.get('body', '')
                
                import re
                # 匹配 $100 或 100 USD 等格式
                patterns = [
                    r'\$(\d+(?:,\d+)*)',
                    r'(\d+(?:,\d)*)\s*USD',
                    r'Bounty:\s*\$(\d+)'
                ]
                
                for text in [title, body]:
                    for pattern in patterns:
                        match = re.search(pattern, text)
                        if match:
                            try:
                                amount = float(match.group(1).replace(',', ''))
                                return amount, 'USD'
                            except:
                                pass
        
        return 0, 'UNKNOWN'
    
    def _get_date_limit(self) -> str:
        """获取搜索日期限制（最近6个月）"""
        from datetime import datetime, timedelta
        date_limit = datetime.now() - timedelta(days=180)
        return date_limit.strftime('%Y-%m-%d')
    
    def run(self, query_params: Dict = None) -> List[BountyTask]:
        """
        执行搜索任务
        
        Returns:
            List[BountyTask]: 搜索到的赏金任务
        """
        query_params = query_params or {}
        
        print("🔍 SearchAgent: Starting bounty search...")
        
        tasks = self.search_github_bounties(
            keywords=query_params.get('keywords'),
            languages=query_params.get('languages'),
            min_bounty=query_params.get('min_bounty')
        )
        
        return tasks
