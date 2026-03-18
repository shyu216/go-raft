#!/usr/bin/env python3
"""
Raft God View - 可视化 Raft 集群运行状态
=========================================
功能：
- 显示所有节点状态 (Leader/Follower/Candidate)
- 实时显示 Term、Vote、Log 信息
- 支持添加新节点
- 支持 Kill 节点
- 显示集群拓扑
"""

import json
import os
import sys
from flask import Flask, render_template_string, jsonify, request
from threading import Thread
import threading

# gRPC 相关（可选，用于实际连接 Raft 节点）
try:
    import grpc
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tests', 'raft'))
    import raft_pb2
    import raft_pb2_grpc
    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    print("提示: gRPC 未安装，仅运行模拟模式")

# ========== 状态管理 ==========

class RaftCluster:
    """Raft 集群管理器"""
    
    def __init__(self):
        self.nodes = {}  # node_id -> NodeInfo
        self.lock = threading.Lock()
        self.processes = {}  # node_id -> subprocess
        self.port_allocator = range(9000, 9100)
        self.used_ports = set()
        
    def allocate_port(self):
        for port in self.port_allocator:
            if port not in self.used_ports:
                self.used_ports.add(port)
                return port
        raise Exception("无可用端口")
    
    def release_port(self, port):
        self.used_ports.discard(port)
        
    def add_node(self, node_id=None):
        """添加新节点到集群"""
        with self.lock:
            if node_id is None:
                node_id = len(self.nodes)
            
            port = self.allocate_port()
            
            # 构建节点端口映射
            ports_str = ",".join(str(n.port) for n in self.nodes.values())
            ports_str += "," + str(port) if ports_str else str(port)
            
            node_info = NodeInfo(
                node_id=node_id,
                port=port,
                role="Follower",
                term=0,
                voted_for=None,
                log_count=0,
                is_alive=True
            )
            self.nodes[node_id] = node_info
            return node_info
            
    def kill_node(self, node_id):
        """Kill 节点"""
        with self.lock:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                node.is_alive = False
                if node_id in self.processes:
                    self.processes[node_id].terminate()
                    del self.processes[node_id]
                return True
            return False
            
    def get_status(self):
        """获取集群状态"""
        with self.lock:
            return {
                "nodes": [
                    {
                        "id": n.node_id,
                        "port": n.port,
                        "role": n.role,
                        "term": n.term,
                        "voted_for": n.voted_for,
                        "log_count": n.log_count,
                        "is_alive": n.is_alive,
                        "commit_index": n.commit_index,
                        "last_contact": n.last_contact
                    }
                    for n in self.nodes.values()
                ],
                "leader": next((n.node_id for n in self.nodes.values() if n.role == "Leader"), None),
                "total_nodes": len(self.nodes),
                "alive_nodes": sum(1 for n in self.nodes.values() if n.is_alive)
            }

class NodeInfo:
    def __init__(self, node_id, port, role, term, voted_for, log_count, is_alive):
        self.node_id = node_id
        self.port = port
        self.role = role
        self.term = term
        self.voted_for = voted_for
        self.log_count = log_count
        self.is_alive = is_alive
        self.commit_index = 0
        self.last_contact = None

# 全局集群
cluster = RaftCluster()

# ========== Flask App ==========

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Raft God View 🦞</title>
    <meta charset="utf-8">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #eee;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        
        h1 {
            text-align: center;
            padding: 20px;
            font-size: 2.5em;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .toolbar {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        
        button {
            padding: 12px 24px;
            font-size: 16px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: bold;
        }
        
        .btn-add {
            background: linear-gradient(135deg, #00d9ff, #0099ff);
            color: #fff;
        }
        
        .btn-kill {
            background: linear-gradient(135deg, #ff6b6b, #ee5a5a);
            color: #fff;
        }
        
        .btn-refresh {
            background: linear-gradient(135deg, #4ecdc4, #44a08d);
            color: #fff;
        }
        
        button:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(0,0,0,0.3); }
        
        .status-bar {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-bottom: 30px;
            padding: 15px;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
        }
        
        .stat { text-align: center; }
        .stat-value { font-size: 2em; font-weight: bold; }
        .stat-label { opacity: 0.7; }
        
        .leader-badge {
            background: linear-gradient(135deg, #ffd700, #ffaa00);
            color: #000;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
        }
        
        .nodes-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
        }
        
        .node-card {
            background: rgba(255,255,255,0.08);
            border-radius: 15px;
            padding: 20px;
            border: 2px solid transparent;
            transition: all 0.3s;
        }
        
        .node-card:hover { transform: scale(1.02); }
        
        .node-card.dead {
            opacity: 0.5;
            border-color: #ff4757;
        }
        
        .node-card.leader { border-color: #ffd700; }
        .node-card.candidate { border-color: #ff6b6b; }
        
        .node-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .node-id {
            font-size: 1.5em;
            font-weight: bold;
        }
        
        .role-badge {
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.9em;
        }
        
        .role-follower { background: #4ecdc4; color: #000; }
        .role-leader { background: #ffd700; color: #000; }
        .role-candidate { background: #ff6b6b; color: #fff; }
        
        .node-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        
        .stat-item {
            background: rgba(0,0,0,0.2);
            padding: 10px;
            border-radius: 8px;
        }
        
        .stat-item label { display: block; opacity: 0.6; font-size: 0.8em; }
        .stat-item span { font-size: 1.2em; font-weight: bold; }
        
        .topology {
            margin-top: 30px;
            padding: 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
        }
        
        .topology h2 { margin-bottom: 15px; }
        
        .topology-svg {
            width: 100%;
            height: 300px;
        }
        
        .log-viewer {
            margin-top: 30px;
            padding: 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
        }
        
        .log-entries {
            max-height: 300px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 0.9em;
        }
        
        .log-entry {
            padding: 5px 10px;
            border-left: 3px solid #4ecdc4;
            margin: 5px 0;
            background: rgba(0,0,0,0.2);
        }
        
        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 15px 25px;
            background: #4ecdc4;
            color: #000;
            border-radius: 10px;
            font-weight: bold;
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from { transform: translateX(100%); }
            to { transform: translateX(0); }
        }
        
        .kill-modal {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.8);
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        
        .kill-modal.active { display: flex; }
        
        .modal-content {
            background: #1a1a2e;
            padding: 30px;
            border-radius: 15px;
            text-align: center;
        }
        
        .modal-content select {
            padding: 10px;
            font-size: 16px;
            margin: 10px;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🫧 Raft God View</h1>
        
        <div class="toolbar">
            <button class="btn-add" onclick="addNode()">➕ Add Node</button>
            <button class="btn-kill" onclick="showKillModal()">💀 Kill Node</button>
            <button class="btn-refresh" onclick="refreshStatus()">🔄 Refresh</button>
        </div>
        
        <div class="status-bar">
            <div class="stat">
                <div class="stat-value" id="totalNodes">0</div>
                <div class="stat-label">Total Nodes</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="aliveNodes">0</div>
                <div class="stat-label">Alive</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="leaderId">-</div>
                <div class="stat-label">Leader</div>
            </div>
        </div>
        
        <div class="nodes-grid" id="nodesGrid">
            <!-- 节点卡片将在这里动态生成 -->
        </div>
        
        <div class="topology">
            <h2>🔗 Cluster Topology</h2>
            <svg class="topology-svg" id="topologySvg">
                <!-- 拓扑图将在这里动态生成 -->
            </svg>
        </div>
    </div>
    
    <div class="kill-modal" id="killModal">
        <div class="modal-content">
            <h2>💀 Kill Node</h2>
            <p>Select a node to kill:</p>
            <select id="killSelect"></select>
            <br><br>
            <button class="btn-kill" onclick="killNode()">Confirm Kill</button>
            <button onclick="hideKillModal()">Cancel</button>
        </div>
    </div>
    
    <div id="toast" class="toast" style="display:none;"></div>
    
    <script>
        let currentStatus = null;
        
        async function refreshStatus() {
            try {
                const res = await fetch('/api/status');
                currentStatus = await res.json();
                renderStatus();
            } catch(e) {
                showToast('Failed to fetch status');
            }
        }
        
        function renderStatus() {
            document.getElementById('totalNodes').textContent = currentStatus.total_nodes;
            document.getElementById('aliveNodes').textContent = currentStatus.alive_nodes;
            document.getElementById('leaderId').textContent = currentStatus.leader ?? 'None';
            
            const grid = document.getElementById('nodesGrid');
            grid.innerHTML = '';
            
            currentStatus.nodes.forEach(node => {
                const card = document.createElement('div');
                card.className = `node-card ${node.role.toLowerCase()} ${node.is_alive ? '' : 'dead'}`;
                
                card.innerHTML = `
                    <div class="node-header">
                        <span class="node-id">Node ${node.id}</span>
                        <span class="role-badge role-${node.role.toLowerCase()}">${node.role}</span>
                    </div>
                    <div class="node-stats">
                        <div class="stat-item">
                            <label>Port</label>
                            <span>${node.port}</span>
                        </div>
                        <div class="stat-item">
                            <label>Term</label>
                            <span>${node.term}</span>
                        </div>
                        <div class="stat-item">
                            <label>Voted For</label>
                            <span>${node.voted_for ?? '-'}</span>
                        </div>
                        <div class="stat-item">
                            <label>Log Entries</label>
                            <span>${node.log_count}</span>
                        </div>
                    </div>
                `;
                grid.appendChild(card);
            });
            
            renderTopology();
        }
        
        function renderTopology() {
            const svg = document.getElementById('topologySvg');
            const nodes = currentStatus.nodes;
            const centerX = 400, centerY = 150;
            const radius = 120;
            
            let html = '';
            
            // 绘制连接线
            const leader = nodes.find(n => n.role === 'Leader');
            nodes.forEach(node => {
                if (leader && node.id !== leader.id) {
                    const angle = (nodes.indexOf(node) / (nodes.length - 1)) * 2 * Math.PI;
                    const x = centerX + radius * Math.cos(angle);
                    const y = centerY + radius * Math.sin(angle);
                    html += `<line x1="${centerX}" y1="${centerY}" x2="${x}" y2="${y}" 
                             stroke="${node.role === 'Leader' ? '#ffd700' : '#4ecdc4'}" stroke-width="2" opacity="0.5"/>`;
                }
            });
            
            // 绘制节点圆
            nodes.forEach((node, idx) => {
                const angle = (idx / nodes.length) * 2 * Math.PI - Math.PI/2;
                const x = centerX + radius * Math.cos(angle);
                const y = centerY + radius * Math.sin(angle);
                const color = node.role === 'Leader' ? '#ffd700' : 
                             node.role === 'Candidate' ? '#ff6b6b' : '#4ecdc4';
                
                html += `<circle cx="${x}" cy="${y}" r="30" fill="${color}" opacity="${node.is_alive ? 1 : 0.3}"/>`;
                html += `<text x="${x}" y="${y+5}" text-anchor="middle" fill="#000" font-weight="bold">${node.id}</text>`;
            });
            
            svg.innerHTML = html;
        }
        
        async function addNode() {
            try {
                const res = await fetch('/api/node/add', { method: 'POST' });
                const data = await res.json();
                showToast(data.message || 'Node added');
                refreshStatus();
            } catch(e) {
                showToast('Failed to add node');
            }
        }
        
        function showKillModal() {
            const select = document.getElementById('killSelect');
            select.innerHTML = currentStatus.nodes
                .filter(n => n.is_alive)
                .map(n => `<option value="${n.id}">Node ${n.id} (${n.role})</option>`)
                .join('');
            document.getElementById('killModal').classList.add('active');
        }
        
        function hideKillModal() {
            document.getElementById('killModal').classList.remove('active');
        }
        
        async function killNode() {
            const nodeId = parseInt(document.getElementById('killSelect').value);
            try {
                const res = await fetch(`/api/node/${nodeId}/kill`, { method: 'POST' });
                const data = await res.json();
                showToast(data.message || 'Node killed');
                hideKillModal();
                refreshStatus();
            } catch(e) {
                showToast('Failed to kill node');
            }
        }
        
        function showToast(msg) {
            const toast = document.getElementById('toast');
            toast.textContent = msg;
            toast.style.display = 'block';
            setTimeout(() => toast.style.display = 'none', 2000);
        }
        
        // 自动刷新
        refreshStatus();
        setInterval(refreshStatus, 3000);
    </script>
</body>
</html>
'''

# ========== API 路由 ==========

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def get_status():
    return jsonify(cluster.get_status())

@app.route('/api/node/add', methods=['POST'])
def add_node():
    try:
        node_info = cluster.add_node()
        return jsonify({
            'success': True,
            'message': f'Node {node_info.node_id} added on port {node_info.port}'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/node/<int:node_id>/kill', methods=['POST'])
def kill_node(node_id):
    success = cluster.kill_node(node_id)
    if success:
        return jsonify({'success': True, 'message': f'Node {node_id} killed'})
    return jsonify({'success': False, 'message': 'Node not found'})

# ========== 模拟数据 (用于演示) ==========

def init_demo_cluster():
    """初始化演示集群"""
    for i in range(3):
        cluster.add_node(i)
    
    # 模拟一些状态
    with cluster.lock:
        if 0 in cluster.nodes:
            cluster.nodes[0].role = "Leader"
            cluster.nodes[0].term = 5
        if 1 in cluster.nodes:
            cluster.nodes[1].role = "Follower"
            cluster.nodes[1].term = 5
            cluster.nodes[1].voted_for = 0
        if 2 in cluster.nodes:
            cluster.nodes[2].role = "Follower"
            cluster.nodes[2].term = 5

if __name__ == '__main__':
    init_demo_cluster()
    
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║          🫧 Raft God View - 启动成功!                      ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  访问地址: http://localhost:5000                           ║
    ║                                                           ║
    ║  功能:                                                    ║
    ║   • 查看所有节点状态 (Leader/Follower/Candidate)          ║
    ║   • 实时显示 Term、Voted For、Log 信息                    ║
    ║   • 可视化集群拓扑                                        ║
    ║   • 添加新节点                                            ║
    ║   • Kill 节点                                             ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
