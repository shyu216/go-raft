# Go-Raft 项目运行指南

## 项目结构

```
go-raft/
├── yourCode/main.go       # 核心 Raft 实现 (需要完成的代码)
├── raft.proto             # gRPC 定义
├── raft/raft.pb.go        # 生成的 gRPC 代码
├── tests/rafttest/        # 测试框架
│   └── rafttest.go
├── tests/raft/           # 生成的 protobuf
└── scripts/              # 测试脚本
```

## 依赖问题

项目使用 `cuhk/asgn/raft` 作为包名，需要创建正确的 go.mod。

## 快速运行方式

### 方式一：使用封装脚本 (推荐)

```bash
cd /home/gem/workspace/agent/workspace/go-raft

# 创建 go.mod 并运行测试
./scripts/run_raft.sh
```

### 方式二：手动运行

```bash
# 1. 设置依赖
cd tests
go mod init cuhk/tests
go mod tidy

# 2. 返回主目录并创建 go.mod
cd ..
go mod init cuhk/asgn
go mod tidy

# 3. 运行测试
# 需要先启动 proxy 和 raft 节点...
```

## God View 可视化方案

设计思路：
1. 每个 Raft 节点暴露状态 API
2. God View 作为控制面板显示所有节点
3. 支持动态添加/删除节点
4. 实时显示 leader/follower/candidate 状态
