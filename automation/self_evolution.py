#!/usr/bin/env python3
"""
自我进化循环 - 每日分析成功/失败模式并优化策略
基于 autoresearch 的自我改进理念
"""
import os
import sys
import json
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

class SelfEvolution:
    """自我进化系统"""
    
    def __init__(self):
        self.workspace = Path('/root/.openclaw/workspace')
        self.memory_dir = self.workspace / 'memory'
        self.program_file = self.workspace / 'AGENT_PROGRAM.md'
        self.config_file = self.workspace / 'projects/bounty-hunter-pro/automation/config.yaml'
        
        # 确保目录存在
        self.memory_dir.mkdir(exist_ok=True)
        (self.memory_dir / 'completed').mkdir(exist_ok=True)
        (self.memory_dir / 'failed').mkdir(exist_ok=True)
        (self.memory_dir / 'patterns').mkdir(exist_ok=True)
    
    def run_daily_evolution(self):
        """运行每日进化循环"""
        print("=" * 60)
        print(f"🧠 Self Evolution Cycle - {datetime.now().strftime('%Y-%m-%d')}")
        print("=" * 60)
        
        # 1. 读取今日数据
        completed, failed = self._read_daily_tasks()
        
        if not completed and not failed:
            print("\n⚠️  No tasks recorded today, skipping evolution")
            return
        
        print(f"\n📊 Today: {len(completed)} completed, {len(failed)} failed")
        
        # 2. 分析模式
        patterns = self._analyze_patterns(completed, failed)
        
        # 3. 提取经验
        insights = self._extract_insights(patterns)
        
        # 4. 更新 program.md
        if insights:
            self._update_program_md(insights)
        
        # 5. 更新配置
        self._update_config(insights)
        
        # 6. 保存分析报告
        self._save_analysis_report(completed, failed, patterns, insights)
        
        print("\n✅ Evolution cycle completed")
    
    def _read_daily_tasks(self) -> Tuple[List[Dict], List[Dict]]:
        """读取今日完成的任务"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        completed = []
        failed = []
        
        # 读取 completed 目录
        completed_dir = self.memory_dir / 'completed'
        for f in completed_dir.glob('*.json'):
            try:
                data = json.loads(f.read_text())
                if data.get('date') == today:
                    completed.append(data)
            except:
                pass
        
        # 读取 failed 目录
        failed_dir = self.memory_dir / 'failed'
        for f in failed_dir.glob('*.json'):
            try:
                data = json.loads(f.read_text())
                if data.get('date') == today:
                    failed.append(data)
            except:
                pass
        
        return completed, failed
    
    def _analyze_patterns(self, completed: List[Dict], failed: List[Dict]) -> Dict:
        """分析成功/失败模式"""
        patterns = {
            'success_by_language': {},
            'success_by_bounty_range': {},
            'failure_reasons': {},
            'avg_completion_time': 0,
            'avg_bounty': 0
        }
        
        # 分析成功的任务
        total_time = 0
        total_bounty = 0
        
        for task in completed:
            lang = task.get('language', 'unknown')
            patterns['success_by_language'][lang] = patterns['success_by_language'].get(lang, 0) + 1
            
            bounty = task.get('bounty_amount', 0)
            total_bounty += bounty
            
            # 赏金范围分类
            if bounty < 50:
                range_key = 'low($10-50)'
            elif bounty < 200:
                range_key = 'medium($50-200)'
            else:
                range_key = 'high($200+)'
            
            patterns['success_by_bounty_range'][range_key] = patterns['success_by_bounty_range'].get(range_key, 0) + 1
            
            total_time += task.get('development_time', 0)
        
        # 分析失败的任务
        for task in failed:
            reason = task.get('failure_reason', 'unknown')
            patterns['failure_reasons'][reason] = patterns['failure_reasons'].get(reason, 0) + 1
        
        # 计算平均值
        if completed:
            patterns['avg_completion_time'] = total_time / len(completed)
            patterns['avg_bounty'] = total_bounty / len(completed)
        
        return patterns
    
    def _extract_insights(self, patterns: Dict) -> List[Dict]:
        """提取改进见解"""
        insights = []
        
        # 洞察 1: 最佳技术栈
        if patterns['success_by_language']:
            best_lang = max(patterns['success_by_language'], key=patterns['success_by_language'].get)
            insights.append({
                'type': 'tech_stack',
                'finding': f"{best_lang} has highest success rate",
                'action': f"Prioritize {best_lang} tasks",
                'priority': 'high'
            })
        
        # 洞察 2: 最佳赏金范围
        if patterns['success_by_bounty_range']:
            best_range = max(patterns['success_by_bounty_range'], key=patterns['success_by_bounty_range'].get)
            insights.append({
                'type': 'bounty_range',
                'finding': f"{best_range} tasks have best success rate",
                'action': f"Focus on {best_range} range",
                'priority': 'medium'
            })
        
        # 洞察 3: 常见失败原因
        if patterns['failure_reasons']:
            top_failure = max(patterns['failure_reasons'], key=patterns['failure_reasons'].get)
            insights.append({
                'type': 'failure_pattern',
                'finding': f"Most common failure: {top_failure}",
                'action': f"Avoid tasks with {top_failure} risk",
                'priority': 'high'
            })
        
        # 洞察 4: 时薪效率
        if patterns['avg_bounty'] > 0 and patterns['avg_completion_time'] > 0:
            hourly_rate = patterns['avg_bounty'] / (patterns['avg_completion_time'] / 3600)
            if hourly_rate < 10:
                insights.append({
                    'type': 'efficiency',
                    'finding': f"Low hourly rate: ${hourly_rate:.2f}/h",
                    'action': "Increase minimum bounty threshold or reduce dev time",
                    'priority': 'high'
                })
            elif hourly_rate > 30:
                insights.append({
                    'type': 'efficiency',
                    'finding': f"Good hourly rate: ${hourly_rate:.2f}/h",
                    'action': "Continue current strategy",
                    'priority': 'low'
                })
        
        return insights
    
    def _update_program_md(self, insights: List[Dict]):
        """更新 program.md 文件"""
        print("\n📝 Updating AGENT_PROGRAM.md...")
        
        try:
            content = self.program_file.read_text()
            
            # 找到策略部分并更新
            strategy_section = "## 🎯 当前策略 (Current Strategy)\n\n### 技术栈优先级"
            
            if strategy_section in content:
                # 提取技术栈洞察
                tech_insights = [i for i in insights if i['type'] == 'tech_stack']
                if tech_insights:
                    # 这里可以更新技术栈优先级
                    print(f"  - Tech stack insight: {tech_insights[0]['finding']}")
            
            # 添加版本记录
            today = datetime.now().strftime('%Y-%m-%d')
            version_line = f"| v1.x | {today} | Auto-updated based on daily analysis |"
            
            # 检查是否已有今日记录
            if today not in content:
                # 在版本记录表末尾添加
                content = content.replace(
                    "*下次评估: 每日 20:00*",
                    f"*下次评估: 每日 20:00*\n\n| v1.{datetime.now().strftime('%m%d')} | {today} | Auto-evolution update |"
                )
                
                self.program_file.write_text(content)
                print("  ✅ Program.md updated")
            else:
                print("  ⏭️  Already updated today")
                
        except Exception as e:
            print(f"  ❌ Error updating program.md: {e}")
    
    def _update_config(self, insights: List[Dict]):
        """更新配置文件"""
        print("\n⚙️  Updating config.yaml...")
        
        try:
            # 读取当前配置
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = yaml.safe_load(f)
            else:
                config = {}
            
            # 根据洞察调整配置
            bounty_insights = [i for i in insights if i['type'] == 'bounty_range']
            efficiency_insights = [i for i in insights if i['type'] == 'efficiency']
            
            # 如果时薪太低，提高最低赏金门槛
            for insight in efficiency_insights:
                if 'Low hourly rate' in insight['finding']:
                    current_min = config.get('search', {}).get('min_bounty', 10)
                    new_min = min(current_min + 5, 50)  # 最高到50
                    config.setdefault('search', {})['min_bounty'] = new_min
                    print(f"  - Increased min_bounty to ${new_min}")
            
            # 保存配置
            with open(self.config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            print("  ✅ Config updated")
            
        except Exception as e:
            print(f"  ❌ Error updating config: {e}")
    
    def _save_analysis_report(self, completed: List[Dict], failed: List[Dict], 
                             patterns: Dict, insights: List[Dict]):
        """保存分析报告"""
        today = datetime.now().strftime('%Y-%m-%d')
        report_file = self.memory_dir / 'patterns' / f'analysis_{today}.json'
        
        report = {
            'date': today,
            'completed_count': len(completed),
            'failed_count': len(failed),
            'patterns': patterns,
            'insights': insights,
            'generated_at': datetime.now().isoformat()
        }
        
        report_file.write_text(json.dumps(report, indent=2))
        print(f"\n📄 Analysis report saved: {report_file}")
    
    def record_task_completion(self, task_id: str, task_data: Dict, success: bool, 
                              duration: float = 0, failure_reason: str = None):
        """记录任务完成状态"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        record = {
            'task_id': task_id,
            'date': today,
            'timestamp': datetime.now().isoformat(),
            'bounty_amount': task_data.get('bounty', {}).get('amount', 0),
            'currency': task_data.get('bounty', {}).get('currency', 'USD'),
            'language': self._detect_language(task_data),
            'development_time': duration
        }
        
        if success:
            record['pr_url'] = task_data.get('pr_url')
            record_file = self.memory_dir / 'completed' / f'{task_id.replace("/", "-")}.json'
        else:
            record['failure_reason'] = failure_reason or 'unknown'
            record_file = self.memory_dir / 'failed' / f'{task_id.replace("/", "-")}.json'
        
        record_file.write_text(json.dumps(record, indent=2))
    
    def _detect_language(self, task_data: Dict) -> str:
        """检测任务主要语言"""
        repo = task_data.get('repo', '')
        title = task_data.get('title', '').lower()
        
        # 从仓库名或标题推断
        if 'python' in repo or 'python' in title:
            return 'python'
        elif 'js' in repo or 'javascript' in title or 'node' in title:
            return 'javascript'
        elif 'ts' in repo or 'typescript' in title:
            return 'typescript'
        elif 'go' in repo or 'golang' in title:
            return 'go'
        elif 'rust' in repo:
            return 'rust'
        
        return 'unknown'

def main():
    """主入口"""
    evolution = SelfEvolution()
    evolution.run_daily_evolution()

if __name__ == '__main__':
    main()
