#!/usr/bin/env python3
"""
KK-17 自动化赏金猎人主控器
每小时执行：搜索 → 评估 → 开发 → 提交
"""
import os
import sys
import json
import yaml
import time
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.search_agent import SearchAgent
from agents.analysis_agent import AnalysisAgent
from agents.competition_agent import CompetitionAgent
from agents.value_agent import ValueAgent
from ir.schema import BountyTaskIR

class KK17AutoBountyHunter:
    """KK-17 自动化赏金猎人"""
    
    def __init__(self):
        self.config = self._load_config()
        self.github_token = os.environ.get('GITHUB_TOKEN')
        self.jira_token = os.environ.get('JIRA_TOKEN')
        
        if not self.github_token:
            raise ValueError("GITHUB_TOKEN required")
        
        # 初始化 Agent
        self.search_agent = SearchAgent(self.github_token, self.config.get('search', {}))
        self.analysis_agent = AnalysisAgent(config=self.config.get('search', {}))
        self.competition_agent = CompetitionAgent(
            self.github_token, 
            config=self.config.get('filters', {})
        )
        self.value_agent = ValueAgent(self.config)
        
        # 统计
        self.stats = {
            'searched': 0,
            'qualified': 0,
            'developed': 0,
            'submitted': 0,
            'errors': []
        }
    
    def _load_config(self) -> Dict:
        """加载配置"""
        config_path = Path(__file__).parent / 'config.yaml'
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def run_hourly_cycle(self):
        """执行每小时周期"""
        print("=" * 70)
        print(f"🎯 KK-17 Auto Bounty Hunter - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 70)
        
        # Step 1: 搜索
        tasks = self._search_tasks()
        self.stats['searched'] = len(tasks)
        
        if not tasks:
            print("❌ No tasks found")
            return self.stats
        
        # Step 2: 评估筛选
        qualified_tasks = self._evaluate_tasks(tasks)
        self.stats['qualified'] = len(qualified_tasks)
        
        if not qualified_tasks:
            print("❌ No qualified tasks")
            return self.stats
        
        # Step 3: 自动开发
        for task_ir in qualified_tasks[:self.config['development']['max_concurrent']]:
            try:
                self._auto_develop(task_ir)
                self.stats['developed'] += 1
            except Exception as e:
                error_msg = f"Development failed for {task_ir.task_id}: {str(e)}"
                print(f"❌ {error_msg}")
                self.stats['errors'].append(error_msg)
        
        return self.stats
    
    def _search_tasks(self) -> List[Dict]:
        """搜索赏金任务"""
        print("\n🔍 Step 1: Searching for bounty tasks...")
        
        search_config = self.config['search']
        query_params = {
            'min_bounty': search_config['min_bounty'],
            'max_tasks': search_config['max_tasks_per_search'],
            'languages': search_config.get('languages', [])
        }
        
        tasks = self.search_agent.run(query_params)
        print(f"✅ Found {len(tasks)} tasks")
        
        return [t.to_dict() for t in tasks]
    
    def _evaluate_tasks(self, tasks: List[Dict]) -> List[BountyTaskIR]:
        """评估并筛选任务"""
        print("\n📊 Step 2: Evaluating tasks...")
        
        qualified = []
        filters = self.config['filters']
        
        for task in tasks:
            task_id = task.get('task_id')
            print(f"\n  Evaluating: {task_id}")
            
            # 1. 货币检查
            currency = task.get('bounty', {}).get('currency', '')
            if currency.upper() not in [c.upper() for c in filters['allowed_currencies']]:
                print(f"    ❌ Skipped: Unsupported currency {currency}")
                continue
            
            # 2. 技术分析
            tech = self.analysis_agent.analyze_task(task)
            if tech.feasibility < 0.5:
                print(f"    ❌ Skipped: Low feasibility ({tech.feasibility:.0%})")
                continue
            
            # 3. 竞争分析（含PR质量检查）
            comp = self.competition_agent.analyze_competition(task)
            
            # 使用高质量PR数量判断竞争（而非总PR数）
            high_quality_prs = comp.high_quality_prs
            max_allowed_prs = filters['max_open_prs']  # 现在是 3
            
            if high_quality_prs > max_allowed_prs:
                print(f"    ❌ Skipped: Has {high_quality_prs} high-quality competing PRs (max {max_allowed_prs})")
                continue
            elif high_quality_prs > 0:
                print(f"    ⚠️ Warning: Has {high_quality_prs} high-quality PR(s), but within limit")
            
            # 显示PR质量详情
            if comp.low_quality_prs > 0:
                print(f"    ℹ️  {comp.low_quality_prs} low-quality PR(s) - not a threat")
            
            # 4. 价值评估
            value = self.value_agent.assess_value(task, tech.to_dict(), comp.to_dict())
            if value.value_score < 6.0:
                print(f"    ❌ Skipped: Low value score ({value.value_score})")
                continue
            
            # 检查阻碍
            if tech.blockers:
                for blocker in tech.blockers:
                    if 'hardware' in blocker.lower() or 'windows' in blocker.lower():
                        print(f"    ❌ Skipped: Has blocker - {blocker}")
                        break
                else:
                    # 通过所有检查
                    ir = BountyTaskIR.from_task_and_analyses(
                        task, tech.to_dict(), comp.to_dict(), value.to_dict()
                    )
                    qualified.append(ir)
                    print(f"    ✅ Qualified! Score: {ir.final_score:.1f}")
            else:
                # 通过所有检查
                ir = BountyTaskIR.from_task_and_analyses(
                    task, tech.to_dict(), comp.to_dict(), value.to_dict()
                )
                qualified.append(ir)
                print(f"    ✅ Qualified! Score: {ir.final_score:.1f}")
        
        print(f"\n✅ Qualified tasks: {len(qualified)}")
        return qualified
    
    def _auto_develop(self, task_ir: BountyTaskIR):
        """自动开发任务"""
        print(f"\n🚀 Step 3: Auto-developing {task_ir.task_id}...")
        
        # 1. 创建 JIRA 任务
        jira_key = self._create_jira_task(task_ir)
        print(f"  ✅ JIRA created: {jira_key}")
        
        # 2. Fork 仓库
        repo = task_ir.repo
        self._fork_repository(repo)
        print(f"  ✅ Forked: {repo}")
        
        # 3. 调用 AI 开发 Agent
        result = self._ai_develop(task_ir)
        
        if result['success']:
            # 4. 提交 PR
            pr_url = self._submit_pr(task_ir, result)
            print(f"  ✅ PR submitted: {pr_url}")
            self.stats['submitted'] += 1
            
            # 5. 更新 JIRA
            self._update_jira(jira_key, pr_url)
        else:
            raise Exception(f"Development failed: {result.get('error')}")
    
    def _create_jira_task(self, task_ir: BountyTaskIR) -> str:
        """创建 JIRA 任务"""
        import base64
        import requests
        
        jira_config = self.config['jira']
        
        auth_str = base64.b64encode(
            f"{os.environ.get('JIRA_EMAIL')}:{self.jira_token}".encode()
        ).decode()
        
        url = "https://ecosolar.atlassian.net/rest/api/3/issue"
        headers = {
            "Authorization": f"Basic {auth_str}",
            "Content-Type": "application/json"
        }
        
        data = {
            "fields": {
                "project": {"key": jira_config['project_key']},
                "summary": f"[AUTO][Bounty] {task_ir.title[:50]} (${task_ir.bounty.amount})",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {"type": "paragraph", "content": [
                            {"type": "text", "text": f"GitHub: {task_ir.url}"}
                        ]},
                        {"type": "paragraph", "content": [
                            {"type": "text", "text": f"Bounty: ${task_ir.bounty.amount} {task_ir.bounty.currency}"}
                        ]},
                        {"type": "paragraph", "content": [
                            {"type": "text", "text": f"Auto-generated by KK-17 Bounty Hunter"}
                        ]}
                    ]
                },
                "issuetype": {"name": "Task"},
                "assignee": {"accountId": jira_config['assignee']},
                "labels": jira_config['labels']
            }
        }
        
        resp = requests.post(url, headers=headers, json=data, timeout=15)
        resp.raise_for_status()
        
        return resp.json()['key']
    
    def _fork_repository(self, repo: str):
        """Fork 仓库"""
        import requests
        
        url = f"https://api.github.com/repos/{repo}/forks"
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github+json"
        }
        
        resp = requests.post(url, headers=headers, timeout=30)
        # 如果已 fork 会返回 422，这是正常的
        if resp.status_code not in [202, 422]:
            resp.raise_for_status()
    
    def _ai_develop(self, task_ir: BountyTaskIR) -> Dict:
        """AI 自动开发"""
        # 这里调用 AI 开发子流程
        # 简化版：创建开发脚本并执行
        
        script_path = Path(__file__).parent / 'ai_develop.py'
        
        result = subprocess.run(
            [
                sys.executable, str(script_path),
                '--task', json.dumps(task_ir.to_dict()),
                '--output', str(Path(__file__).parent / 'queue')
            ],
            capture_output=True,
            text=True,
            timeout=self.config['development']['time_limit_hours'] * 3600
        )
        
        if result.returncode != 0:
            return {'success': False, 'error': result.stderr}
        
        return json.loads(result.stdout)
    
    def _submit_pr(self, task_ir: BountyTaskIR, dev_result: Dict) -> str:
        """提交 PR"""
        import requests
        
        repo = task_ir.repo
        branch = dev_result.get('branch', 'fix/auto-generated')
        
        url = f"https://api.github.com/repos/{repo}/pulls"
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github+json"
        }
        
        data = {
            "title": f"fix: {task_ir.title[:50]} (#{task_ir.issue_number})",
            "body": self.config['github']['pr_template'].format(
                description=f"Auto-generated fix for {task_ir.task_id}",
                changes="- See commit history for details",
                issue_number=task_ir.issue_number
            ),
            "head": f"Kiki-bo-zhang:{branch}",
            "base": "master"
        }
        
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        resp.raise_for_status()
        
        return resp.json()['html_url']
    
    def _update_jira(self, jira_key: str, pr_url: str):
        """更新 JIRA 状态"""
        # 简化：添加评论
        pass
    
    def send_daily_report(self):
        """发送每日汇报邮件"""
        from datetime import datetime
        
        report = f"""
# KK-17 Daily Bounty Hunter Report

**Date**: {datetime.now().strftime('%Y-%m-%d')}

## Statistics

| Metric | Count |
|--------|-------|
| Tasks Searched | {self.stats['searched']} |
| Tasks Qualified | {self.stats['qualified']} |
| Tasks Developed | {self.stats['developed']} |
| PRs Submitted | {self.stats['submitted']} |

## Target Progress

Daily Goal: 10 tasks
Completed: {self.stats['submitted']}
Progress: {self.stats['submitted'] * 10}%

## Errors

"""
        if self.stats['errors']:
            for error in self.stats['errors']:
                report += f"- {error}\n"
        else:
            report += "No errors today.\n"
        
        # 发送邮件
        self._send_email("KK-17 Daily Bounty Report", report)
    
    def _send_email(self, subject: str, body: str):
        """发送邮件"""
        import requests
        
        email_config = self.config['email']
        
        url = "https://api.agentmail.to/v0/inboxes/kiki@agentmail.to/messages/send"
        headers = {
            "Authorization": f"Bearer {os.environ.get('AGENTMAIL_API_KEY')}",
            "Content-Type": "application/json"
        }
        
        data = {
            "to": email_config['recipient'],
            "subject": subject,
            "text": body
        }
        
        resp = requests.post(url, headers=headers, json=data, timeout=15)
        resp.raise_for_status()
        
        print(f"📧 Daily report sent to {email_config['recipient']}")

def main():
    """主入口"""
    hunter = KK17AutoBountyHunter()
    stats = hunter.run_hourly_cycle()
    
    # 如果是晚上 8 点，发送日报
    if datetime.now().hour == 20:
        hunter.send_daily_report()
    
    return stats

if __name__ == '__main__':
    main()
