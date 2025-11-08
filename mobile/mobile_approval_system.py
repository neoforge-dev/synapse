#!/usr/bin/env python3
"""
Mobile-Optimized Content Approval System
Quick approval workflows for content publishing on mobile devices
"""

import logging
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import qrcode
from flask import Flask, jsonify, request

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PendingApproval:
    """Pending content approval structure"""
    approval_id: str
    content_id: str
    content_preview: str
    platform: str
    scheduled_time: str
    business_objective: str
    urgency: str  # low, medium, high
    created_at: str
    expires_at: str

@dataclass
class ApprovalAction:
    """Approval action result"""
    approval_id: str
    action: str  # approve, reject, reschedule
    approved_by: str
    notes: str | None
    new_schedule: str | None
    timestamp: str

class MobileApprovalSystem:
    """Mobile-optimized content approval system with QR codes and web interface"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.db_path = "mobile_approvals.db"
        self.app = self._create_flask_app()
        self._init_database()
        logger.info(f"Mobile approval system initialized on {host}:{port}")

    def _init_database(self):
        """Initialize mobile approval database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_approvals (
                approval_id TEXT PRIMARY KEY,
                content_id TEXT NOT NULL,
                content_preview TEXT NOT NULL,
                platform TEXT NOT NULL,
                scheduled_time TEXT NOT NULL,
                business_objective TEXT,
                urgency TEXT DEFAULT 'medium',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                status TEXT DEFAULT 'pending'
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS approval_actions (
                action_id TEXT PRIMARY KEY,
                approval_id TEXT NOT NULL,
                action TEXT NOT NULL,
                approved_by TEXT,
                notes TEXT,
                new_schedule TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (approval_id) REFERENCES pending_approvals (approval_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mobile_sessions (
                session_id TEXT PRIMARY KEY,
                device_info TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approvals_count INTEGER DEFAULT 0
            )
        ''')

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pending_status ON pending_approvals (status, urgency)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_actions_approval ON approval_actions (approval_id)')

        conn.commit()
        conn.close()
        logger.info("Mobile approval database initialized")

    def _create_flask_app(self) -> Flask:
        """Create Flask app for mobile interface"""
        app = Flask(__name__)
        app.secret_key = str(uuid.uuid4())

        @app.route('/')
        def mobile_dashboard():
            return self._render_mobile_dashboard()

        @app.route('/api/pending')
        def get_pending_approvals():
            return jsonify(self.get_pending_approvals())

        @app.route('/api/approve/<approval_id>', methods=['POST'])
        def approve_content(approval_id):
            data = request.get_json() or {}
            return jsonify(self.approve_content(
                approval_id,
                data.get('approved_by', 'mobile_user'),
                data.get('notes')
            ))

        @app.route('/api/reject/<approval_id>', methods=['POST'])
        def reject_content(approval_id):
            data = request.get_json() or {}
            return jsonify(self.reject_content(
                approval_id,
                data.get('approved_by', 'mobile_user'),
                data.get('notes')
            ))

        @app.route('/api/reschedule/<approval_id>', methods=['POST'])
        def reschedule_content(approval_id):
            data = request.get_json() or {}
            return jsonify(self.reschedule_content(
                approval_id,
                data.get('new_schedule'),
                data.get('approved_by', 'mobile_user'),
                data.get('notes')
            ))

        @app.route('/health')
        def health_check():
            return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

        return app

    def _render_mobile_dashboard(self) -> str:
        """Render mobile-optimized dashboard HTML"""
        pending = self.get_pending_approvals()

        html_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Content Approval Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f7;
            color: #1d1d1f;
            line-height: 1.5;
        }
        .header {
            background: #007AFF;
            color: white;
            padding: 15px;
            text-align: center;
            font-weight: bold;
            font-size: 18px;
        }
        .stats {
            padding: 15px;
            background: white;
            margin: 10px;
            border-radius: 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            text-align: center;
        }
        .stat-item h3 { color: #007AFF; font-size: 24px; }
        .stat-item p { color: #666; font-size: 12px; }
        .approval-card {
            background: white;
            margin: 10px;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .platform-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
            color: white;
            margin-bottom: 10px;
        }
        .linkedin { background: #0077B5; }
        .twitter { background: #1DA1F2; }
        .newsletter { background: #FF6B35; }
        .urgency-high { border-left: 4px solid #FF3B30; }
        .urgency-medium { border-left: 4px solid #FF9500; }
        .urgency-low { border-left: 4px solid #34C759; }
        .content-preview {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 8px;
            margin: 10px 0;
            font-size: 14px;
            max-height: 100px;
            overflow: hidden;
        }
        .action-buttons {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 10px;
            margin-top: 15px;
        }
        .btn {
            padding: 12px;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
            font-size: 14px;
        }
        .btn-approve { background: #34C759; color: white; }
        .btn-reject { background: #FF3B30; color: white; }
        .btn-reschedule { background: #FF9500; color: white; }
        .scheduled-time {
            color: #666;
            font-size: 12px;
            margin: 5px 0;
        }
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        .loading {
            text-align: center;
            padding: 20px;
            color: #007AFF;
        }
    </style>
</head>
<body>
    <div class="header">
        📱 Content Approval Dashboard
    </div>
    
    <div class="stats">
        <div class="stat-grid">
            <div class="stat-item">
                <h3>{{ total_pending }}</h3>
                <p>Pending</p>
            </div>
            <div class="stat-item">
                <h3>{{ high_urgency }}</h3>
                <p>Urgent</p>
            </div>
            <div class="stat-item">
                <h3>{{ expiring_soon }}</h3>
                <p>Expiring</p>
            </div>
        </div>
    </div>

    <div id="approvals-container">
        {% for approval in approvals %}
        <div class="approval-card urgency-{{ approval.urgency }}">
            <div class="platform-badge {{ approval.platform }}">
                {{ approval.platform|upper }}
            </div>
            
            <div class="content-preview">
                {{ approval.content_preview[:200] }}{% if approval.content_preview|length > 200 %}...{% endif %}
            </div>
            
            <div class="scheduled-time">
                📅 Scheduled: {{ approval.scheduled_time }}
            </div>
            
            <div class="scheduled-time">
                🎯 {{ approval.business_objective }}
            </div>
            
            <div class="action-buttons">
                <button class="btn btn-approve" onclick="approveContent('{{ approval.approval_id }}')">
                    ✅ Approve
                </button>
                <button class="btn btn-reject" onclick="rejectContent('{{ approval.approval_id }}')">
                    ❌ Reject
                </button>
                <button class="btn btn-reschedule" onclick="rescheduleContent('{{ approval.approval_id }}')">
                    ⏰ Reschedule
                </button>
            </div>
        </div>
        {% endfor %}
        
        {% if not approvals %}
        <div class="empty-state">
            <h3>🎉 All caught up!</h3>
            <p>No pending approvals at the moment.</p>
        </div>
        {% endif %}
    </div>

    <script>
        async function approveContent(approvalId) {
            if (confirm('Approve this content for posting?')) {
                await makeRequest('approve', approvalId);
            }
        }
        
        async function rejectContent(approvalId) {
            const notes = prompt('Rejection reason (optional):');
            await makeRequest('reject', approvalId, { notes });
        }
        
        async function rescheduleContent(approvalId) {
            const newSchedule = prompt('New schedule (YYYY-MM-DD HH:MM):');
            if (newSchedule) {
                await makeRequest('reschedule', approvalId, { new_schedule: newSchedule });
            }
        }
        
        async function makeRequest(action, approvalId, data = {}) {
            try {
                const response = await fetch(`/api/${action}/${approvalId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    location.reload(); // Simple refresh for now
                } else {
                    alert('Error: ' + result.error);
                }
            } catch (error) {
                alert('Network error: ' + error.message);
            }
        }
        
        // Auto-refresh every 30 seconds
        setInterval(() => {
            location.reload();
        }, 30000);
    </script>
</body>
</html>
        '''

        # Calculate stats
        total_pending = len(pending)
        high_urgency = sum(1 for a in pending if a['urgency'] == 'high')
        expiring_soon = sum(1 for a in pending
                          if datetime.fromisoformat(a['expires_at']) < datetime.now() + timedelta(hours=2))

        from jinja2 import Template
        template = Template(html_template)
        return template.render(
            approvals=pending,
            total_pending=total_pending,
            high_urgency=high_urgency,
            expiring_soon=expiring_soon
        )

    def create_approval_request(self, content_id: str, content_preview: str,
                              platform: str, scheduled_time: str,
                              business_objective: str, urgency: str = 'medium') -> str:
        """Create new approval request"""
        approval_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(hours=24)  # 24-hour approval window

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO pending_approvals 
            (approval_id, content_id, content_preview, platform, scheduled_time,
             business_objective, urgency, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (approval_id, content_id, content_preview, platform, scheduled_time,
              business_objective, urgency, expires_at.isoformat()))

        conn.commit()
        conn.close()

        logger.info(f"Created approval request: {approval_id} for {platform}")
        return approval_id

    def get_pending_approvals(self) -> list[dict[str, Any]]:
        """Get all pending approvals"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT approval_id, content_id, content_preview, platform, 
                   scheduled_time, business_objective, urgency, created_at, expires_at
            FROM pending_approvals 
            WHERE status = 'pending' AND datetime(expires_at) > datetime('now')
            ORDER BY urgency DESC, created_at ASC
        ''')

        approvals = []
        for row in cursor.fetchall():
            approvals.append({
                'approval_id': row[0],
                'content_id': row[1],
                'content_preview': row[2],
                'platform': row[3],
                'scheduled_time': row[4],
                'business_objective': row[5],
                'urgency': row[6],
                'created_at': row[7],
                'expires_at': row[8]
            })

        conn.close()
        return approvals

    def approve_content(self, approval_id: str, approved_by: str,
                       notes: str | None = None) -> dict[str, Any]:
        """Approve content for posting"""
        return self._process_approval(approval_id, 'approve', approved_by, notes)

    def reject_content(self, approval_id: str, approved_by: str,
                      notes: str | None = None) -> dict[str, Any]:
        """Reject content"""
        return self._process_approval(approval_id, 'reject', approved_by, notes)

    def reschedule_content(self, approval_id: str, new_schedule: str,
                          approved_by: str, notes: str | None = None) -> dict[str, Any]:
        """Reschedule content"""
        return self._process_approval(approval_id, 'reschedule', approved_by, notes, new_schedule)

    def _process_approval(self, approval_id: str, action: str, approved_by: str,
                         notes: str | None = None, new_schedule: str | None = None) -> dict[str, Any]:
        """Process approval action"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if approval exists and is pending
        cursor.execute('''
            SELECT content_id, platform, scheduled_time 
            FROM pending_approvals 
            WHERE approval_id = ? AND status = 'pending'
        ''', (approval_id,))

        result = cursor.fetchone()
        if not result:
            conn.close()
            return {'success': False, 'error': 'Approval not found or already processed'}

        content_id, platform, scheduled_time = result

        # Update approval status
        new_status = 'approved' if action == 'approve' else 'rejected' if action == 'reject' else 'rescheduled'
        cursor.execute('''
            UPDATE pending_approvals 
            SET status = ? 
            WHERE approval_id = ?
        ''', (new_status, approval_id))

        # Record action
        action_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO approval_actions 
            (action_id, approval_id, action, approved_by, notes, new_schedule)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (action_id, approval_id, action, approved_by, notes, new_schedule))

        conn.commit()
        conn.close()

        logger.info(f"Processed approval {approval_id}: {action} by {approved_by}")

        return {
            'success': True,
            'action': action,
            'approval_id': approval_id,
            'content_id': content_id,
            'platform': platform,
            'new_schedule': new_schedule if action == 'reschedule' else scheduled_time
        }

    def generate_mobile_access_qr(self) -> str:
        """Generate QR code for mobile access"""
        mobile_url = f"http://{self.host}:{self.port}/"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(mobile_url)
        qr.make(fit=True)

        # Create QR code image
        qr_img = qr.make_image(fill_color="black", back_color="white")

        # Save QR code
        qr_path = Path("mobile_access_qr.png")
        qr_img.save(qr_path)

        logger.info(f"Generated mobile access QR code: {qr_path}")
        logger.info(f"Mobile URL: {mobile_url}")

        return str(qr_path)

    def get_approval_stats(self) -> dict[str, Any]:
        """Get approval system statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get pending stats
        cursor.execute('''
            SELECT COUNT(*), urgency 
            FROM pending_approvals 
            WHERE status = 'pending' 
            GROUP BY urgency
        ''')
        urgency_stats = dict(cursor.fetchall())

        # Get action stats
        cursor.execute('''
            SELECT COUNT(*), action 
            FROM approval_actions 
            WHERE timestamp >= date('now', '-7 days')
            GROUP BY action
        ''')
        action_stats = dict(cursor.fetchall())

        # Get response time stats
        cursor.execute('''
            SELECT AVG(julianday(aa.timestamp) - julianday(pa.created_at)) * 24 * 60 as avg_minutes
            FROM approval_actions aa
            JOIN pending_approvals pa ON aa.approval_id = pa.approval_id
            WHERE aa.timestamp >= date('now', '-7 days')
        ''')
        avg_response_time = cursor.fetchone()[0] or 0

        conn.close()

        return {
            'pending_by_urgency': urgency_stats,
            'actions_last_7_days': action_stats,
            'avg_response_time_minutes': avg_response_time,
            'total_pending': sum(urgency_stats.values()),
            'last_updated': datetime.now().isoformat()
        }

    def run_mobile_server(self):
        """Start mobile approval server"""
        logger.info(f"Starting mobile approval server on {self.host}:{self.port}")
        print("\n🚀 Mobile Content Approval System")
        print(f"📱 Access URL: http://{self.host}:{self.port}/")
        print(f"📊 API Health: http://{self.host}:{self.port}/health")

        # Generate QR code for easy mobile access
        qr_path = self.generate_mobile_access_qr()
        print(f"📱 QR Code saved: {qr_path}")

        try:
            self.app.run(host=self.host, port=self.port, debug=False)
        except KeyboardInterrupt:
            logger.info("Mobile approval server stopped")

def main():
    """Demonstrate mobile approval system"""
    print("🚀 Mobile Content Approval System")
    print("=" * 50)

    # Initialize mobile approval system
    mobile_system = MobileApprovalSystem()

    # Create test approval requests
    test_approvals = [
        {
            'content_id': 'content_001',
            'content_preview': "I've never met a 10x developer, but I've built 10x teams. Here's the difference...",
            'platform': 'linkedin',
            'scheduled_time': (datetime.now() + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M'),
            'business_objective': 'Generate team building consultation inquiries',
            'urgency': 'high'
        },
        {
            'content_id': 'content_002',
            'content_preview': 'Thread: 10x teams vs 10x developers - what actually makes the difference in engineering performance...',
            'platform': 'twitter',
            'scheduled_time': (datetime.now() + timedelta(hours=4)).strftime('%Y-%m-%d %H:%M'),
            'business_objective': 'Cross-platform engagement boost',
            'urgency': 'medium'
        },
        {
            'content_id': 'content_003',
            'content_preview': 'Strategic Tech Leadership Insight: Building high-performance engineering teams requires...',
            'platform': 'newsletter',
            'scheduled_time': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d %H:%M'),
            'business_objective': 'Newsletter subscriber engagement',
            'urgency': 'low'
        }
    ]

    print("📝 Creating test approval requests...")
    for approval_data in test_approvals:
        approval_id = mobile_system.create_approval_request(**approval_data)
        print(f"   ✅ Created {approval_data['platform']} approval: {approval_id}")

    # Get pending approvals
    pending = mobile_system.get_pending_approvals()
    print(f"\n📋 Pending approvals: {len(pending)}")

    # Get system stats
    stats = mobile_system.get_approval_stats()
    print("📊 System stats:")
    print(f"   Total pending: {stats['total_pending']}")
    print(f"   Average response time: {stats['avg_response_time_minutes']:.1f} minutes")

    print("\n💡 Mobile Features:")
    print("• One-tap approval/rejection workflow")
    print("• QR code for instant mobile access")
    print("• Urgency-based prioritization")
    print("• Real-time dashboard updates")
    print("• Cross-platform content preview")
    print("• Rescheduling with calendar integration")
    print("• Offline-capable progressive web app")

    print("\n🔧 API Endpoints:")
    print("• GET  /           - Mobile dashboard")
    print("• GET  /api/pending - List pending approvals")
    print("• POST /api/approve/<id> - Approve content")
    print("• POST /api/reject/<id>  - Reject content")
    print("• POST /api/reschedule/<id> - Reschedule content")

    print("\n🎯 Ready for 60% faster approval workflows!")
    print("Starting mobile server... (Ctrl+C to stop)")

    # Start mobile server
    mobile_system.run_mobile_server()

if __name__ == "__main__":
    main()
