"""
ReportAgent - 报告生成 Agent
基于 IR 中间表示生成多格式报告
"""
import json
from typing import Dict, List
from datetime import datetime
from ir.schema import BountyTaskIR

class ReportAgent:
    """报告生成 Agent - 将 IR 渲染为多格式输出"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.output_dir = self.config.get('output_dir', './reports')
    
    def generate_report(
        self, 
        tasks_ir: List[BountyTaskIR], 
        format: str = 'markdown',
        title: str = "Bounty Hunter Report"
    ) -> str:
        """
        生成报告
        
        Args:
            tasks_ir: IR 任务列表
            format: 输出格式 (markdown/json/html)
            title: 报告标题
        
        Returns:
            str: 报告内容或文件路径
        """
        # 按优先级和分数排序
        sorted_tasks = sorted(
            tasks_ir, 
            key=lambda x: (x.priority != 'high', -x.final_score)
        )
        
        if format == 'markdown':
            return self._render_markdown(sorted_tasks, title)
        elif format == 'json':
            return self._render_json(sorted_tasks, title)
        elif format == 'html':
            return self._render_html(sorted_tasks, title)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _render_markdown(self, tasks: List[BountyTaskIR], title: str) -> str:
        """渲染 Markdown 报告"""
        lines = []
        
        # 标题
        lines.append(f"# {title}")
        lines.append(f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"**Tasks Found**: {len(tasks)}")
        lines.append("\n---\n")
        
        # 摘要
        high_priority = [t for t in tasks if t.priority == 'high']
        if high_priority:
            lines.append(f"## 🎯 High Priority Tasks ({len(high_priority)})")
            lines.append("\nThese tasks are strongly recommended based on value, tech match, and low competition.\n")
        
        # 任务详情
        for i, task in enumerate(tasks, 1):
            lines.extend(self._render_task_markdown(task, i))
        
        # 统计
        lines.extend(self._render_statistics(tasks))
        
        return "\n".join(lines)
    
    def _render_task_markdown(self, task: BountyTaskIR, index: int) -> List[str]:
        """渲染单个任务的 Markdown"""
        lines = []
        
        # 任务标题和优先级徽章
        priority_emoji = {'high': '🔥', 'medium': '⚡', 'low': '💤'}
        emoji = priority_emoji.get(task.priority, '📋')
        
        lines.append(f"\n## {emoji} {index}. {task.title}")
        lines.append(f"\n**Task ID**: [{task.task_id}]({task.url})")
        
        # 基本信息
        lines.append(f"\n### 💰 Bounty")
        lines.append(f"- **Amount**: ${task.bounty.amount:,.2f} {task.bounty.currency}")
        lines.append(f"- **Hourly Rate**: ${task.value_assessment.hourly_rate:.2f}/h")
        
        # 分析结果
        lines.append(f"\n### 📊 Analysis")
        
        # 技术分析
        tech = task.tech_analysis
        lines.append(f"\n**Technical**:")
        lines.append(f"- Match Score: {tech.tech_match_score:.0%}")
        lines.append(f"- Complexity: {tech.complexity}")
        lines.append(f"- Feasibility: {tech.feasibility:.0%}")
        lines.append(f"- Est. Hours: {tech.estimated_hours}h")
        if tech.required_skills:
            lines.append(f"- Skills: {', '.join(tech.required_skills[:5])}")
        if tech.blockers:
            lines.append(f"- ⚠️ Blockers: {', '.join(tech.blockers)}")
        
        # 竞争分析
        comp = task.competition_analysis
        lines.append(f"\n**Competition**:")
        lines.append(f"- Open PRs: {comp.open_prs_count}")
        lines.append(f"- Competition Level: {comp.competition_level}")
        lines.append(f"- Maintainer Active: {'✅' if comp.maintainer_active else '❌'}")
        if comp.notes:
            lines.append(f"- Notes:")
            for note in comp.notes[:3]:
                lines.append(f"  - {note}")
        
        # 价值评估
        value = task.value_assessment
        lines.append(f"\n**Value Assessment**:")
        lines.append(f"- Score: {value.value_score}/10")
        lines.append(f"- Risk Level: {value.risk_level}")
        lines.append(f"- Recommendation: {value.recommendation}")
        if value.risk_factors:
            lines.append(f"- Risk Factors: {', '.join(value.risk_factors[:3])}")
        
        # 综合评分
        lines.append(f"\n### 🎯 Final Score: {task.final_score:.1f}/10")
        lines.append(f"**Priority**: {task.priority.upper()}")
        
        lines.append("\n---\n")
        
        return lines
    
    def _render_statistics(self, tasks: List[BountyTaskIR]) -> List[str]:
        """渲染统计信息"""
        lines = []
        
        lines.append("\n## 📈 Statistics")
        
        # 优先级分布
        priority_counts = {}
        for t in tasks:
            priority_counts[t.priority] = priority_counts.get(t.priority, 0) + 1
        
        lines.append(f"\n### Priority Distribution")
        for p in ['high', 'medium', 'low']:
            count = priority_counts.get(p, 0)
            lines.append(f"- {p.capitalize()}: {count}")
        
        # 赏金统计
        total_bounty = sum(t.bounty.amount for t in tasks)
        avg_bounty = total_bounty / len(tasks) if tasks else 0
        
        lines.append(f"\n### Bounty Statistics")
        lines.append(f"- Total Potential: ${total_bounty:,.2f}")
        lines.append(f"- Average: ${avg_bounty:,.2f}")
        
        # 风险统计
        risk_counts = {}
        for t in tasks:
            risk_counts[t.value_assessment.risk_level] = risk_counts.get(
                t.value_assessment.risk_level, 0
            ) + 1
        
        lines.append(f"\n### Risk Distribution")
        for r in ['low', 'medium', 'high']:
            count = risk_counts.get(r, 0)
            lines.append(f"- {r.capitalize()} Risk: {count}")
        
        return lines
    
    def _render_json(self, tasks: List[BountyTaskIR], title: str) -> str:
        """渲染 JSON 报告"""
        data = {
            "title": title,
            "generated_at": datetime.now().isoformat(),
            "total_tasks": len(tasks),
            "tasks": [task.to_dict() for task in tasks],
            "statistics": self._calculate_statistics(tasks)
        }
        
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def _render_html(self, tasks: List[BountyTaskIR], title: str) -> str:
        """渲染 HTML 报告"""
        # 简化版 HTML，可以扩展为完整模板
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; border-bottom: 1px solid #ddd; padding-bottom: 10px; }}
        .task {{ background: #f9f9f9; padding: 15px; margin: 15px 0; border-radius: 5px; }}
        .high {{ border-left: 4px solid #ff6b6b; }}
        .medium {{ border-left: 4px solid #feca57; }}
        .low {{ border-left: 4px solid #48dbfb; }}
        .score {{ font-size: 24px; font-weight: bold; color: #5f27cd; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f1f1f1; }}
    </style>
</head>
<body>
    <h1>🎯 {title}</h1>
    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    <p><strong>Total Tasks:</strong> {len(tasks)}</p>
    
    <h2>Recommended Tasks</h2>
"""
        
        for task in tasks:
            priority_class = task.priority
            html += f"""
    <div class="task {priority_class}">
        <h3><a href="{task.url}" target="_blank">{task.title}</a></h3>
        <p><strong>Bounty:</strong> ${task.bounty.amount:,.2f} {task.bounty.currency}</p>
        <p><strong>Tech Match:</strong> {task.tech_analysis.tech_match_score:.0%}</p>
        <p><strong>Competition:</strong> {task.competition_analysis.competition_level}</p>
        <p class="score">Score: {task.final_score:.1f}/10</p>
    </div>
"""
        
        html += """
</body>
</html>"""
        
        return html
    
    def _calculate_statistics(self, tasks: List[BountyTaskIR]) -> Dict:
        """计算统计数据"""
        if not tasks:
            return {}
        
        priority_counts = {}
        risk_counts = {}
        total_bounty = 0
        
        for t in tasks:
            priority_counts[t.priority] = priority_counts.get(t.priority, 0) + 1
            risk_counts[t.value_assessment.risk_level] = risk_counts.get(
                t.value_assessment.risk_level, 0
            ) + 1
            total_bounty += t.bounty.amount
        
        return {
            "priority_distribution": priority_counts,
            "risk_distribution": risk_counts,
            "total_bounty": round(total_bounty, 2),
            "average_bounty": round(total_bounty / len(tasks), 2),
            "average_score": round(sum(t.final_score for t in tasks) / len(tasks), 1)
        }
    
    def save_report(self, content: str, filename: str) -> str:
        """保存报告到文件"""
        import os
        
        os.makedirs(self.output_dir, exist_ok=True)
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Report saved: {filepath}")
        return filepath
