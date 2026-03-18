#!/bin/bash
# Fork and PR script for go-raft

echo "=========================================="
echo "  🦞 Go-Raft God View PR Helper"
echo "=========================================="
echo ""
echo "由于环境中没有 gh CLI，请手动完成以下步骤："
echo ""
echo "1️⃣  手动 Fork 仓库:"
echo "   访问: https://github.com/shyu216/go-raft/fork"
echo "   点击 'Create fork'"
echo ""
echo "2️⃣  添加你的 remote (替换 YOUR_USERNAME):"
echo "   git remote add mine https://github.com/YOUR_USERNAME/go-raft.git"
echo ""
echo "3️⃣  推送代码:"
echo "   git checkout -b god-view"
echo "   git add god_view.py RUN.md"
echo "   git commit -m 'Add God View visualization for Raft cluster'"
echo "   git push mine god-view"
echo ""
echo "4️⃣  创建 PR:"
echo "   访问: https://github.com/shyu216/go-raft/compare"
echo "   选择你的分支 god-view 创建 PR"
echo ""
echo "=========================================="
echo "  或者... 直接访问以下链接创建 PR:"
echo "=========================================="
echo ""
echo "PR 标题建议: Add God View visualization for Raft cluster"
echo ""
echo "PR 内容建议:"
cat << 'EOF'
## Description

Add a web-based God View visualization for the Raft cluster with the following features:

- Display all node states (Leader/Follower/Candidate) in real-time
- Show Term, Voted For, Log count for each node
- Visualize cluster topology
- Support adding new nodes
- Support killing nodes
- Auto-refresh every 3 seconds

## Files Changed

- `god_view.py` - Flask-based web UI for cluster visualization
- `RUN.md` - Running guide for the project

## Usage

```bash
python3 god_view.py
# Visit http://localhost:5000
```

## Screenshots

[Add screenshots if available]
EOF
