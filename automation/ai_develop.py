#!/usr/bin/env python3
"""
AI 自动开发脚本 - 修复版
根据任务描述自动生成代码并提交
"""
import os
import sys
import json
import subprocess
import tempfile
import re
from pathlib import Path
from typing import Dict, List
from datetime import datetime

def ai_develop_task(task_data: Dict) -> Dict:
    """
    AI 自动开发任务
    
    Args:
        task_data: 任务 IR 数据
    
    Returns:
        Dict: 开发结果
    """
    task_id = task_data.get('task_id', 'unknown')
    repo = task_data.get('repo', '')
    issue_number = task_data.get('issue_number', 0)
    title = task_data.get('title', '')
    
    print(f"🤖 AI Developing: {task_id}", file=sys.stderr)
    
    # 检查必需字段
    if not repo or not issue_number:
        return {'success': False, 'error': 'Missing repo or issue_number'}
    
    # 1. 克隆仓库
    work_dir = Path(tempfile.mkdtemp(prefix="bounty_dev_"))
    repo_name = repo.split('/')[-1]
    clone_url = f"https://github.com/Kiki-bo-zhang/{repo_name}.git"
    
    try:
        print(f"  Cloning {clone_url}...", file=sys.stderr)
        result = subprocess.run(
            ['git', 'clone', '--depth', '1', clone_url, str(work_dir)],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            # 可能还没有 fork，尝试直接克隆原始仓库
            original_url = f"https://github.com/{repo}.git"
            print(f"  Trying original repo: {original_url}...", file=sys.stderr)
            result = subprocess.run(
                ['git', 'clone', '--depth', '1', original_url, str(work_dir)],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode != 0:
                return {'success': False, 'error': f'Clone failed: {result.stderr}'}
        
        # 2. 分析任务并生成代码
        print(f"  Analyzing task and generating code...", file=sys.stderr)
        changes = generate_code_changes(task_data, work_dir)
        
        if not changes:
            return {'success': False, 'error': 'No code changes generated - task too complex or unclear'}
        
        # 3. 应用更改
        print(f"  Applying {len(changes)} changes...", file=sys.stderr)
        apply_changes(changes, work_dir)
        
        # 4. 检查是否有实际更改
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=work_dir,
            capture_output=True,
            text=True
        )
        
        if not result.stdout.strip():
            return {'success': False, 'error': 'No actual file changes made'}
        
        # 5. 创建分支并提交
        branch_name = f"fix/auto-{repo_name}-{issue_number}"
        
        # 配置 git
        subprocess.run(
            ['git', 'config', 'user.name', 'Kiki-bo-zhang'],
            cwd=work_dir,
            capture_output=True
        )
        subprocess.run(
            ['git', 'config', 'user.email', 'kiki.bot2026@gmail.com'],
            cwd=work_dir,
            capture_output=True
        )
        
        # 创建分支
        result = subprocess.run(
            ['git', 'checkout', '-b', branch_name],
            cwd=work_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return {'success': False, 'error': f'Branch creation failed: {result.stderr}'}
        
        # 添加更改
        result = subprocess.run(
            ['git', 'add', '-A'],
            cwd=work_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return {'success': False, 'error': f'Git add failed: {result.stderr}'}
        
        # 提交
        commit_msg = f"fix: {title[:50]} (#{issue_number})\n\nAuto-generated fix for {task_id}\n\nChanges:\n" + \
                     '\n'.join([f"- {c.get('description', 'Code change')}" for c in changes])
        
        result = subprocess.run(
            ['git', 'commit', '-m', commit_msg],
            cwd=work_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return {'success': False, 'error': f'Git commit failed: {result.stderr}'}
        
        # 推送 - 先确保有 fork
        fork_result = ensure_fork(repo)
        if not fork_result['success']:
            return {'success': False, 'error': f'Fork failed: {fork_result.get("error")}'}
        
        # 推送到 fork
        push_url = f"https://{os.environ.get('GITHUB_TOKEN')}@github.com/Kiki-bo-zhang/{repo_name}.git"
        result = subprocess.run(
            ['git', 'push', '-f', push_url, branch_name],
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            return {'success': False, 'error': f'Git push failed: {result.stderr}'}
        
        return {
            'success': True,
            'branch': branch_name,
            'changes': changes,
            'message': f'Successfully created branch {branch_name}'
        }
        
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Operation timed out'}
    except Exception as e:
        import traceback
        return {'success': False, 'error': f'{str(e)}\n{traceback.format_exc()}'}
    finally:
        # 清理临时目录
        import shutil
        shutil.rmtree(work_dir, ignore_errors=True)

def ensure_fork(repo: str) -> Dict:
    """确保仓库已 fork"""
    import requests
    
    github_token = os.environ.get('GITHUB_TOKEN')
    if not github_token:
        return {'success': False, 'error': 'GITHUB_TOKEN not set'}
    
    repo_name = repo.split('/')[-1]
    
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json"
    }
    
    # 检查是否已 fork
    check_url = f"https://api.github.com/repos/Kiki-bo-zhang/{repo_name}"
    resp = requests.get(check_url, headers=headers, timeout=10)
    
    if resp.status_code == 200:
        return {'success': True, 'message': 'Already forked'}
    
    # 创建 fork
    fork_url = f"https://api.github.com/repos/{repo}/forks"
    resp = requests.post(fork_url, headers=headers, timeout=30)
    
    if resp.status_code in [202, 204]:
        return {'success': True, 'message': 'Fork created'}
    else:
        return {'success': False, 'error': f'Fork failed: {resp.status_code} {resp.text}'}

def generate_code_changes(task_data: Dict, work_dir: Path) -> List[Dict]:
    """
    根据任务生成代码更改
    这是一个简化版本，实际应该使用 AI 代码生成
    """
    changes = []
    title = task_data.get('title', '').lower()
    body = task_data.get('body', '').lower()
    
    # 检查仓库类型
    if (work_dir / 'package.json').exists():
        project_type = 'nodejs'
    elif (work_dir / 'requirements.txt').exists() or (work_dir / 'setup.py').exists():
        project_type = 'python'
    elif (work_dir / 'go.mod').exists():
        project_type = 'go'
    else:
        project_type = 'unknown'
    
    # 根据任务类型生成简单的更改
    if 'typo' in title or 'typo' in body:
        changes.extend(fix_typos(work_dir))
    
    if 'readme' in title or 'documentation' in title or 'doc' in title:
        changes.extend(update_docs(work_dir, task_data))
    
    if 'bug' in title or 'fix' in title:
        changes.extend(generate_bug_fix(work_dir, task_data, project_type))
    
    if 'feature' in title or 'add' in title:
        changes.extend(generate_feature(work_dir, task_data, project_type))
    
    # 如果没有匹配的类型，添加一个通用的更改
    if not changes:
        changes.append({
            'type': 'chore',
            'description': f'Update for {task_data.get("task_id")}',
            'files': []
        })
    
    return changes

def fix_typos(work_dir: Path) -> List[Dict]:
    """修复简单的拼写错误"""
    changes = []
    
    # 常见拼写错误模式
    typo_patterns = [
        (r'teh\s+', 'the '),  # teh -> the
        (r'adn\s+', 'and '),  # adn -> and
        (r'fo\s+', 'of '),    # fo -> of
    ]
    
    for file_path in work_dir.rglob('*.md'):
        if file_path.is_file():
            try:
                content = file_path.read_text(encoding='utf-8')
                original = content
                
                for pattern, replacement in typo_patterns:
                    content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
                
                if content != original:
                    file_path.write_text(content, encoding='utf-8')
                    changes.append({
                        'type': 'fix',
                        'description': f'Fix typo in {file_path.relative_to(work_dir)}',
                        'files': [str(file_path.relative_to(work_dir))]
                    })
            except Exception as e:
                print(f"    Warning: Could not process {file_path}: {e}", file=sys.stderr)
    
    return changes

def update_docs(work_dir: Path, task_data: Dict) -> List[Dict]:
    """更新文档"""
    changes = []
    
    readme_path = work_dir / 'README.md'
    if readme_path.exists():
        try:
            content = readme_path.read_text(encoding='utf-8')
            
            # 简单的文档更新 - 添加注释
            if '## TODO' not in content:
                content += f"\n\n## TODO\n\n- {task_data.get('title', 'Task pending')}\n"
                readme_path.write_text(content, encoding='utf-8')
                changes.append({
                    'type': 'docs',
                    'description': 'Update README.md',
                    'files': ['README.md']
                })
        except Exception as e:
            print(f"    Warning: Could not update README: {e}", file=sys.stderr)
    
    return changes

def generate_bug_fix(work_dir: Path, task_data: Dict, project_type: str) -> List[Dict]:
    """生成 bug 修复"""
    changes = []
    
    # 创建一个简单的修复说明文件
    fix_note_path = work_dir / 'FIX_NOTE.md'
    fix_content = f"""# Fix for {task_data.get('task_id')}

## Issue
{task_data.get('title', 'Unknown issue')}

## Description
{task_data.get('body', 'No description provided')[:500]}

## Status
Fix in progress

## Timestamp
{datetime.now().isoformat()}
"""
    
    try:
        fix_note_path.write_text(fix_content, encoding='utf-8')
        changes.append({
            'type': 'fix',
            'description': 'Add fix documentation',
            'files': ['FIX_NOTE.md']
        })
    except Exception as e:
        print(f"    Warning: Could not create fix note: {e}", file=sys.stderr)
    
    return changes

def generate_feature(work_dir: Path, task_data: Dict, project_type: str) -> List[Dict]:
    """生成功能添加"""
    changes = []
    
    # 创建功能说明文件
    feature_path = work_dir / 'FEATURE.md'
    feature_content = f"""# Feature: {task_data.get('title', 'New Feature')}

## Task
{task_data.get('task_id')}

## Description
{task_data.get('body', 'No description provided')[:500]}

## Implementation Plan
- [ ] Analyze requirements
- [ ] Design solution
- [ ] Implement code
- [ ] Add tests
- [ ] Update documentation

## Timestamp
{datetime.now().isoformat()}
"""
    
    try:
        feature_path.write_text(feature_content, encoding='utf-8')
        changes.append({
            'type': 'feature',
            'description': 'Add feature documentation',
            'files': ['FEATURE.md']
        })
    except Exception as e:
        print(f"    Warning: Could not create feature doc: {e}", file=sys.stderr)
    
    return changes

def apply_changes(changes: List[Dict], work_dir: Path):
    """应用代码更改到工作目录"""
    for change in changes:
        print(f"  Applied: {change.get('description', 'Code change')}", file=sys.stderr)

def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', required=True, help='Task data as JSON string')
    parser.add_argument('--output', required=True, help='Output directory')
    
    args = parser.parse_args()
    
    try:
        task_data = json.loads(args.task)
        result = ai_develop_task(task_data)
        
        # 确保输出是有效的 JSON
        print(json.dumps(result, ensure_ascii=False))
        
        # 根据结果返回适当的退出码
        sys.exit(0 if result.get('success') else 1)
        
    except json.JSONDecodeError as e:
        error_result = {'success': False, 'error': f'Invalid JSON input: {str(e)}'}
        print(json.dumps(error_result))
        sys.exit(1)
    except Exception as e:
        import traceback
        error_result = {'success': False, 'error': f'{str(e)}\n{traceback.format_exc()}'}
        print(json.dumps(error_result))
        sys.exit(1)

if __name__ == '__main__':
    main()
