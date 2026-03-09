#!/bin/bash
# KK-17 赏金猎人启动脚本
# 确保环境变量正确加载

# 加载环境变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../.env"

# 检查必要环境变量
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ Error: GITHUB_TOKEN not set"
    exit 1
fi

# 启动赏金猎人（使用集成 program.md 和自我进化的新版本）
cd "$SCRIPT_DIR/.."
python3 automation/kimi_hunter.py >> automation/logs/hourly.log 2>&1
