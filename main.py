"""
Bounty Hunter Pro - 主入口
多 Agent 协作的赏金任务搜索与分析系统
"""
import os
import sys
import argparse
from typing import Dict, List
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.search_agent import SearchAgent
from agents.analysis_agent import AnalysisAgent
from agents.competition_agent import CompetitionAgent
from agents.value_agent import ValueAgent
from agents.report_agent import ReportAgent
from ir.schema import BountyTaskIR

class BountyHunterPro:
    """赏金猎人主控制器"""
    
    def __init__(self, github_token: str, config: Dict = None):
        """
        初始化系统
        
        Args:
            github_token: GitHub API Token
            config: 配置参数
        """
        self.config = config or {}
        
        # 初始化所有 Agent
        print("🚀 Initializing Bounty Hunter Pro...")
        print("  - SearchAgent")
        self.search_agent = SearchAgent(github_token, config)
        
        print("  - AnalysisAgent")
        self.analysis_agent = AnalysisAgent(
            my_skills=config.get('my_skills'),
            config=config
        )
        
        print("  - CompetitionAgent")
        self.competition_agent = CompetitionAgent(github_token)
        
        print("  - ValueAgent")
        self.value_agent = ValueAgent(config)
        
        print("  - ReportAgent")
        self.report_agent = ReportAgent(config)
        
        print("✅ All agents initialized\n")
    
    def run(self, query_params: Dict) -> str:
        """
        运行完整的赏金搜索流程
        
        Args:
            query_params: 查询参数
                - keywords: 关键词列表
                - languages: 编程语言列表
                - min_bounty: 最小赏金金额
                - max_tasks: 最大任务数
                - format: 输出格式
        
        Returns:
            str: 报告文件路径或内容
        """
        print("=" * 60)
        print("🎯 BOUNTY HUNTER PRO - Starting Search")
        print("=" * 60)
        
        # Step 1: Search
        print("\n🔍 Step 1: Searching for bounty tasks...")
        tasks = self.search_agent.run(query_params)
        
        if not tasks:
            print("❌ No bounty tasks found matching criteria")
            return ""
        
        print(f"✅ Found {len(tasks)} tasks")
        
        # Step 2: Analysis
        print("\n📊 Step 2: Analyzing tasks...")
        task_dicts = [t.to_dict() for t in tasks]
        
        tech_analyses = self.analysis_agent.run(task_dicts)
        print(f"✅ Technical analysis completed for {len(tech_analyses)} tasks")
        
        # Step 3: Competition Analysis
        print("\n⚔️  Step 3: Analyzing competition...")
        competition_analyses = self.competition_agent.run(task_dicts)
        print(f"✅ Competition analysis completed")
        
        # Step 4: Value Assessment
        print("\n💰 Step 4: Assessing value...")
        value_assessments = self.value_agent.run(
            task_dicts, tech_analyses, competition_analyses
        )
        print(f"✅ Value assessment completed")
        
        # Step 5: Generate IR
        print("\n🔄 Step 5: Generating IR (Intermediate Representation)...")
        tasks_ir = []
        for task in tasks:
            task_id = task.task_id
            tech = tech_analyses.get(task_id, {})
            comp = competition_analyses.get(task_id, {})
            value = value_assessments.get(task_id, {})
            
            ir = BountyTaskIR.from_task_and_analyses(
                task.to_dict(), tech, comp, value
            )
            tasks_ir.append(ir)
        
        print(f"✅ IR generated for {len(tasks_ir)} tasks")
        
        # Step 6: Generate Report
        print("\n📄 Step 6: Generating report...")
        format_type = query_params.get('format', 'markdown')
        title = f"Bounty Hunter Report - {datetime.now().strftime('%Y-%m-%d')}"
        
        report_content = self.report_agent.generate_report(
            tasks_ir, format=format_type, title=title
        )
        
        # Step 7: Save Report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"bounty_report_{timestamp}.{format_type}"
        
        if format_type == 'json':
            filename = f"bounty_report_{timestamp}.json"
        elif format_type == 'html':
            filename = f"bounty_report_{timestamp}.html"
        else:
            filename = f"bounty_report_{timestamp}.md"
        
        filepath = self.report_agent.save_report(report_content, filename)
        
        # Summary
        print("\n" + "=" * 60)
        print("✅ SEARCH COMPLETE")
        print("=" * 60)
        print(f"\n📊 Summary:")
        print(f"  - Tasks analyzed: {len(tasks_ir)}")
        print(f"  - High priority: {sum(1 for t in tasks_ir if t.priority == 'high')}")
        print(f"  - Medium priority: {sum(1 for t in tasks_ir if t.priority == 'medium')}")
        print(f"  - Low priority: {sum(1 for t in tasks_ir if t.priority == 'low')}")
        print(f"\n📄 Report saved: {filepath}")
        
        return filepath

def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description='Bounty Hunter Pro - Multi-Agent Bounty Task Search System'
    )
    
    parser.add_argument(
        '--keywords', '-k',
        nargs='+',
        help='Search keywords (e.g., python javascript)'
    )
    
    parser.add_argument(
        '--languages', '-l',
        nargs='+',
        help='Programming languages (e.g., python go javascript)'
    )
    
    parser.add_argument(
        '--min-bounty', '-m',
        type=int,
        default=20,
        help='Minimum bounty amount (default: 20)'
    )
    
    parser.add_argument(
        '--max-tasks', '-n',
        type=int,
        default=50,
        help='Maximum tasks to analyze (default: 50)'
    )
    
    parser.add_argument(
        '--format', '-f',
        choices=['markdown', 'json', 'html'],
        default='markdown',
        help='Output format (default: markdown)'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        default='./reports',
        help='Output directory (default: ./reports)'
    )
    
    parser.add_argument(
        '--token', '-t',
        help='GitHub API Token (or set GITHUB_TOKEN env var)'
    )
    
    parser.add_argument(
        '--skills', '-s',
        nargs='+',
        default=['python', 'javascript', 'typescript', 'go', 'react'],
        help='Your technical skills (for matching)'
    )
    
    args = parser.parse_args()
    
    # 获取 GitHub Token
    github_token = args.token or os.environ.get('GITHUB_TOKEN')
    
    if not github_token:
        print("❌ Error: GitHub Token required")
        print("   Set GITHUB_TOKEN environment variable or use --token")
        sys.exit(1)
    
    # 构建配置
    config = {
        'min_bounty': args.min_bounty,
        'max_tasks_per_run': args.max_tasks,
        'my_skills': args.skills,
        'output_dir': args.output_dir
    }
    
    query_params = {
        'keywords': args.keywords or [],
        'languages': args.languages or [],
        'min_bounty': args.min_bounty,
        'max_tasks': args.max_tasks,
        'format': args.format
    }
    
    # 运行系统
    try:
        hunter = BountyHunterPro(github_token, config)
        report_path = hunter.run(query_params)
        
        if report_path:
            print(f"\n🎉 Done! Check your report at: {report_path}")
        else:
            print("\n⚠️  No tasks found matching your criteria")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
