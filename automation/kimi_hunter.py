#!/usr/bin/env python3
"""
Kimi Bounty Hunter - 主程序（集成 program.md 和自我进化）
基于 autoresearch 的 program.md 编程范式
"""
import os
import sys
import json
import yaml
from datetime import datetime
from pathlib import Path

# 加载 program.md 作为系统上下文
PROGRAM_MD_PATH = Path('/root/.openclaw/workspace/AGENT_PROGRAM.md')

def load_program_context() -> str:
    """加载 program.md 作为系统上下文"""
    if PROGRAM_MD_PATH.exists():
        return PROGRAM_MD_PATH.read_text()
    return ""

def get_system_prompt_with_program() -> str:
    """获取包含 program.md 的系统提示"""
    program = load_program_context()
    
    return f"""{program}

---

## 当前执行上下文

你是 Kimi Bounty Hunter，正在执行赏金任务搜索和开发。
请严格按照 AGENT_PROGRAM.md 中定义的工作流和评估标准执行任务。

当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

记住:
1. 每小时搜索新任务
2. 严格评估（货币/赏金/竞争/技术匹配）
3. 合格任务立即开发，无需请示
4. 记录所有结果用于自我进化
5. 保持专业，不在 PR 中暴露 AI 身份

开始执行...
"""

# 将 program 上下文添加到环境，供其他模块使用
os.environ['AGENT_PROGRAM_CONTEXT'] = load_program_context()

# 继续导入其他模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.search_agent import SearchAgent
from agents.analysis_agent import AnalysisAgent
from agents.competition_agent import CompetitionAgent
from agents.value_agent import ValueAgent
from ir.schema import BountyTaskIR

class KimiBountyHunter:
    """
    Kimi Bounty Hunter - 基于 program.md 编程的赏金猎人
    """
    
    def __init__(self):
        # 加载 program.md
        self.program_context = load_program_context()
        print("📝 Loaded AGENT_PROGRAM.md")
        
        # 加载配置
        self.config = self._load_config()
        self.github_token = os.environ.get('GITHUB_TOKEN')
        
        if not self.github_token:
            raise ValueError("GITHUB_TOKEN required")
        
        # 初始化 Agent
        self._init_agents()
        
        # 初始化自我进化
        self._init_self_evolution()
        
        # 统计
        self.stats = {
            'searched': 0,
            'qualified': 0,
            'developed': 0,
            'submitted': 0,
            'errors': []
        }
    
    def _load_config(self) -> dict:
        """加载配置"""
        config_path = Path(__file__).parent / 'config.yaml'
        if config_path.exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        return {}
    
    def _init_agents(self):
        """初始化所有 Agent"""
        print("🚀 Initializing Agents...")
        
        self.search_agent = SearchAgent(
            self.github_token, 
            self.config.get('search', {})
        )
        
        self.analysis_agent = AnalysisAgent(
            config=self.config.get('search', {})
        )
        
        self.competition_agent = CompetitionAgent(
            self.github_token,
            config=self.config.get('filters', {})
        )
        
        self.value_agent = ValueAgent(self.config)
        
        print("✅ All agents initialized")
    
    def _init_self_evolution(self):
        """初始化自我进化系统"""
        from automation.self_evolution import SelfEvolution
        self.evolution = SelfEvolution()
        print("🧠 Self-evolution system ready")
    
    def run(self):
        """运行主循环"""
        print("\n" + "=" * 70)
        print(get_system_prompt_with_program())
        print("=" * 70)
        
        # Step 1: 搜索
        tasks = self._search_tasks()
        self.stats['searched'] = len(tasks)
        
        if not tasks:
            print("❌ No tasks found")
            return self.stats
        
        # Step 2: 评估
        qualified_tasks = self._evaluate_tasks(tasks)
        self.stats['qualified'] = len(qualified_tasks)
        
        if not qualified_tasks:
            print("❌ No qualified tasks")
            return self.stats
        
        # Step 3: 开发
        for task_ir in qualified_tasks[:self.config.get('development', {}).get('max_concurrent', 3)]:
            try:
                self._develop_task(task_ir)
                self.stats['developed'] += 1
            except Exception as e:
                error_msg = f"Development failed for {task_ir.task_id}: {str(e)}"
                print(f"❌ {error_msg}")
                self.stats['errors'].append(error_msg)
                
                # 记录失败
                self.evolution.record_task_completion(
                    task_ir.task_id,
                    task_ir.to_dict(),
                    success=False,
                    failure_reason=str(e)
                )
        
        # Step 4: 如果是晚上8点，运行自我进化
        if datetime.now().hour == 20:
            print("\n🧠 Running self-evolution cycle...")
            self.evolution.run_daily_evolution()
        
        return self.stats
    
    def _search_tasks(self) -> list:
        """搜索任务"""
        print("\n🔍 Step 1: Searching for bounty tasks...")
        
        search_config = self.config.get('search', {})
        query_params = {
            'min_bounty': search_config.get('min_bounty', 10),
            'max_tasks': search_config.get('max_tasks_per_search', 50),
            'languages': search_config.get('languages', [])
        }
        
        tasks = self.search_agent.run(query_params)
        print(f"✅ Found {len(tasks)} tasks")
        
        return [t.to_dict() for t in tasks]
    
    def _evaluate_tasks(self, tasks: list) -> list:
        """评估任务"""
        print("\n📊 Step 2: Evaluating tasks...")
        
        qualified = []
        filters = self.config.get('filters', {})
        
        for task in tasks:
            task_id = task.get('task_id')
            print(f"\n  Evaluating: {task_id}")
            
            # 1. 货币检查
            currency = task.get('bounty', {}).get('currency', '')
            allowed = [c.upper() for c in filters.get('allowed_currencies', [])]
            if currency.upper() not in allowed:
                print(f"    ❌ Skipped: Unsupported currency {currency}")
                continue
            
            # 2. 技术分析
            tech = self.analysis_agent.analyze_task(task)
            if tech.feasibility < 0.5:
                print(f"    ❌ Skipped: Low feasibility ({tech.feasibility:.0%})")
                continue
            
            # 3. 竞争分析
            comp = self.competition_agent.analyze_competition(task)
            high_quality_prs = comp.high_quality_prs
            max_allowed = filters.get('max_open_prs', 3)
            
            if high_quality_prs > max_allowed:
                print(f"    ❌ Skipped: {high_quality_prs} high-quality PRs (max {max_allowed})")
                continue
            
            # 4. 价值评估
            value = self.value_agent.assess_value(task, tech.to_dict(), comp.to_dict())
            if value.value_score < 6.0:
                print(f"    ❌ Skipped: Low value score ({value.value_score})")
                continue
            
            # 检查阻碍
            has_blocker = False
            for blocker in tech.blockers:
                if 'hardware' in blocker.lower() or 'windows' in blocker.lower():
                    print(f"    ❌ Skipped: {blocker}")
                    has_blocker = True
                    break
            
            if has_blocker:
                continue
            
            # 通过所有检查
            ir = BountyTaskIR.from_task_and_analyses(
                task, tech.to_dict(), comp.to_dict(), value.to_dict()
            )
            qualified.append(ir)
            print(f"    ✅ Qualified! Score: {ir.final_score:.1f}")
        
        print(f"\n✅ Qualified tasks: {len(qualified)}")
        return qualified
    
    def _develop_task(self, task_ir: BountyTaskIR):
        """开发任务"""
        print(f"\n🚀 Step 3: Developing {task_ir.task_id}...")
        
        import time
        start_time = time.time()
        
        try:
            # 1. Fork 仓库
            repo = task_ir.repo
            self._fork_repository(repo)
            print(f"  ✅ Forked: {repo}")
            
            # 2. 开发
            result = self._ai_develop(task_ir)
            
            if not result['success']:
                raise Exception(result.get('error', 'Development failed'))
            
            # 3. 开发成功后才创建 JIRA
            jira_key = self._create_jira_task(task_ir)
            print(f"  ✅ JIRA created: {jira_key}")
            
            # 4. 提交 PR
            pr_url = self._submit_pr(task_ir, result)
            print(f"  ✅ PR submitted: {pr_url}")
            
            self.stats['submitted'] += 1
            
            # 5. 更新 JIRA
            self._update_jira(jira_key, pr_url)
            
            # 6. 记录成功
            duration = time.time() - start_time
            task_data = task_ir.to_dict()
            task_data['pr_url'] = pr_url
            
            self.evolution.record_task_completion(
                task_ir.task_id,
                task_data,
                success=True,
                duration=duration
            )
            
        except Exception as e:
            # 记录失败
            duration = time.time() - start_time
            self.evolution.record_task_completion(
                task_ir.task_id,
                task_ir.to_dict(),
                success=False,
                duration=duration,
                failure_reason=str(e)
            )
            raise
    
    def _fork_repository(self, repo: str):
        """Fork 仓库"""
        import requests
        url = f"https://api.github.com/repos/{repo}/forks"
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github+json"
        }
        resp = requests.post(url, headers=headers, timeout=30)
        if resp.status_code not in [202, 422]:
            resp.raise_for_status()
    
    def _ai_develop(self, task_ir: BountyTaskIR) -> dict:
        """AI 开发"""
        import subprocess
        import json
        
        script_path = Path(__file__).parent / 'ai_develop.py'
        
        result = subprocess.run(
            [
                sys.executable, str(script_path),
                '--task', json.dumps(task_ir.to_dict()),
                '--output', '/tmp'
            ],
            capture_output=True,
            text=True,
            timeout=4 * 3600  # 4小时超时
        )
        
        if result.returncode != 0:
            return {'success': False, 'error': result.stderr}
        
        return json.loads(result.stdout)
    
    def _create_jira_task(self, task_ir: BountyTaskIR) -> str:
        """创建 JIRA 任务"""
        import base64
        import requests
        
        jira_config = self.config.get('jira', {})
        jira_token = os.environ.get('JIRA_TOKEN')
        jira_email = os.environ.get('JIRA_EMAIL')
        
        auth_str = base64.b64encode(f"{jira_email}:{jira_token}".encode()).decode()
        
        url = "https://ecosolar.atlassian.net/rest/api/3/issue"
        headers = {
            "Authorization": f"Basic {auth_str}",
            "Content-Type": "application/json"
        }
        
        data = {
            "fields": {
                "project": {"key": jira_config.get('project_key', 'KK')},
                "summary": f"[Bounty] {task_ir.title[:50]} (${task_ir.bounty.amount})",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {"type": "paragraph", "content": [
                            {"type": "text", "text": f"GitHub: {task_ir.url}"}
                        ]},
                        {"type": "paragraph", "content": [
                            {"type": "text", "text": f"Bounty: ${task_ir.bounty.amount} {task_ir.bounty.currency}"}
                        ]}
                    ]
                },
                "issuetype": {"name": "Task"},
                "assignee": {"accountId": jira_config.get('assignee')},
                "labels": jira_config.get('labels', ['bounty'])
            }
        }
        
        resp = requests.post(url, headers=headers, json=data, timeout=15)
        resp.raise_for_status()
        
        return resp.json()['key']
    
    def _submit_pr(self, task_ir: BountyTaskIR, dev_result: dict) -> str:
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
            "body": f"Fixes #{task_ir.issue_number}",
            "head": f"Kiki-bo-zhang:{branch}",
            "base": "master"
        }
        
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        resp.raise_for_status()
        
        return resp.json()['html_url']
    
    def _update_jira(self, jira_key: str, pr_url: str):
        """更新 JIRA"""
        # 简化实现，可以扩展
        pass

def main():
    """主入口"""
    hunter = KimiBountyHunter()
    stats = hunter.run()
    
    print("\n" + "=" * 70)
    print("📊 Daily Summary")
    print("=" * 70)
    print(f"Tasks Searched: {stats['searched']}")
    print(f"Tasks Qualified: {stats['qualified']}")
    print(f"Tasks Developed: {stats['developed']}")
    print(f"PRs Submitted: {stats['submitted']}")
    
    if stats['errors']:
        print(f"\n❌ Errors ({len(stats['errors'])}):")
        for err in stats['errors']:
            print(f"  - {err}")
    
    print("\n✅ Execution completed according to AGENT_PROGRAM.md")

if __name__ == '__main__':
    main()
