from flask import Blueprint, request, jsonify
import sqlite3
from datetime import datetime
from task_state_machine import task_state_machine

# 创建蓝图
tasks_bp = Blueprint('tasks', __name__)


@tasks_bp.route('/tasks/execute_all', methods=['POST'])
def execute_all_tasks():
    try:
        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute("""
            SELECT id FROM tasks 
            WHERE status = 'pending'
            ORDER BY CASE priority 
                WHEN 'high' THEN 3 
                WHEN 'medium' THEN 2 
                WHEN 'low' THEN 1 
                ELSE 0 END DESC, created_at ASC
        """)
        pending_ids = [row[0] for row in c.fetchall()]
        executed = 0
        for task_id in pending_ids:
            is_valid, err = task_state_machine.validate_transition(task_id, 'in_progress', conn)
            if not is_valid:
                continue
            c.execute('UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?',
                      ('in_progress', now, task_id))
            c.execute('''INSERT INTO task_status_history (task_id, status, timestamp, message)
                         VALUES (?, ?, ?, ?)''',
                      (task_id, 'in_progress', now, '批量执行：开始任务'))
            c.execute('UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?',
                      ('completed', now, task_id))
            c.execute('''INSERT INTO task_status_history (task_id, status, timestamp, message)
                         VALUES (?, ?, ?, ?)''',
                      (task_id, 'completed', now, '批量执行：任务完成'))
            executed += 1
        conn.commit()
        conn.close()
        return jsonify({'executed': executed})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/tasks', methods=['GET'])
def get_tasks():
    """获取任务列表"""
    try:
        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()
        
        # 获取查询参数
        status_filter = request.args.get('status')
        priority_filter = request.args.get('priority')
        type_filter = request.args.get('type')
        
        # 构建查询条件
        query = 'SELECT * FROM tasks'
        conditions = []
        params = []
        
        if status_filter:
            conditions.append('status = ?')
            params.append(status_filter)
        
        if priority_filter:
            conditions.append('priority = ?')
            params.append(priority_filter)
        
        if type_filter:
            conditions.append('type = ?')
            params.append(type_filter)
        
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
        
        query += ' ORDER BY created_at DESC'
        
        c.execute(query, params)
        tasks = c.fetchall()
        
        # 转换为字典列表
        task_list = []
        for task in tasks:
            task_list.append({
                'id': task[0],
                'name': task[1],
                'type': task[2],
                'priority': task[3],
                'status': task[4],
                'parameters': task[5],
                'created_at': task[6],
                'updated_at': task[7]
            })
        
        conn.close()
        
        return jsonify(task_list)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/tasks', methods=['POST'])
def create_task():
    """创建新任务"""
    try:
        data = request.json
        
        # 验证必需字段
        required_fields = ['name', 'type', 'priority']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'缺少必需字段: {field}'}), 400
        
        # 获取当前时间
        now = datetime.now().isoformat()
        
        # 插入数据库
        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()
        
        c.execute('''INSERT INTO tasks 
                     (name, type, priority, status, parameters, created_at, updated_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (data['name'], data['type'], data['priority'], 'pending',
                   data.get('parameters', ''), now, now))
        
        task_id = c.lastrowid
        
        # 记录状态历史
        c.execute('''INSERT INTO task_status_history 
                     (task_id, status, timestamp, message)
                     VALUES (?, ?, ?, ?)''',
                  (task_id, 'pending', now, '任务创建'))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'id': task_id,
            'message': '任务创建成功'
        }), 201
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """获取特定任务详情"""
    try:
        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()
        
        c.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
        task = c.fetchone()
        
        if task is None:
            conn.close()
            return jsonify({'error': '任务不存在'}), 404
        
        # 转换为字典
        task_dict = {
            'id': task[0],
            'name': task[1],
            'type': task[2],
            'priority': task[3],
            'status': task[4],
            'parameters': task[5],
            'created_at': task[6],
            'updated_at': task[7]
        }
        
        conn.close()
        
        return jsonify(task_dict)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """更新任务信息"""
    try:
        data = request.json
        
        # 检查任务是否存在
        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()
        
        c.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
        task = c.fetchone()
        
        if task is None:
            conn.close()
            return jsonify({'error': '任务不存在'}), 404
        
        # 构建更新语句
        updates = []
        params = []
        
        if 'name' in data:
            updates.append('name = ?')
            params.append(data['name'])
        
        if 'type' in data:
            updates.append('type = ?')
            params.append(data['type'])
        
        if 'priority' in data:
            updates.append('priority = ?')
            params.append(data['priority'])
        
        if 'parameters' in data:
            updates.append('parameters = ?')
            params.append(data['parameters'])
        
        # 更新时间
        updates.append('updated_at = ?')
        params.append(datetime.now().isoformat())
        
        if updates:
            params.append(task_id)
            query = 'UPDATE tasks SET ' + ', '.join(updates) + ' WHERE id = ?'
            c.execute(query, params)
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': '任务更新成功'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除任务"""
    try:
        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()
        
        # 检查任务是否存在
        c.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
        task = c.fetchone()
        
        if task is None:
            conn.close()
            return jsonify({'error': '任务不存在'}), 404
        
        # 删除相关的状态历史
        c.execute('DELETE FROM task_status_history WHERE task_id = ?', (task_id,))
        
        # 删除任务
        c.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': '任务删除成功'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/tasks/<int:task_id>/status', methods=['PUT'])
def update_task_status(task_id):
    """更新任务状态"""
    try:
        data = request.json
        
        if 'status' not in data:
            return jsonify({'error': '缺少status字段'}), 400
        
        new_status = data['status']
        message = data.get('message', '')
        
        # 验证状态转换
        conn = sqlite3.connect('tasks.db')
        # 获取当前状态用于额外验证
        c = conn.cursor()
        c.execute('SELECT status FROM tasks WHERE id = ?', (task_id,))
        row = c.fetchone()
        current_status = row[0] if row else None

        # 验证状态转换（特别处理 in_progress -> completed）
        if new_status == 'completed' and current_status != 'in_progress':
            conn.close()
            return jsonify({'error': '只有进行中的任务可以标记为完成'}), 400

        is_valid, error_msg = task_state_machine.validate_transition(task_id, new_status, conn)
        
        if not is_valid:
            conn.close()
            return jsonify({'error': error_msg}), 400
        
        # 获取当前时间
        now = datetime.now().isoformat()
        
        # 更新任务状态
        c = conn.cursor()
        c.execute('UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?',
                  (new_status, now, task_id))
        
        # 记录状态历史
        c.execute('''INSERT INTO task_status_history 
                     (task_id, status, timestamp, message)
                     VALUES (?, ?, ?, ?)''',
                  (task_id, new_status, now, message))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': '任务状态更新成功'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/tasks/<int:task_id>/history', methods=['GET'])
def get_task_history(task_id):
    """获取任务状态历史"""
    try:
        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()
        
        # 检查任务是否存在
        c.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
        task = c.fetchone()
        
        if task is None:
            conn.close()
            return jsonify({'error': '任务不存在'}), 404
        
        # 获取状态历史
        c.execute('SELECT * FROM task_status_history WHERE task_id = ? ORDER BY timestamp DESC',
                  (task_id,))
        history_records = c.fetchall()
        
        # 转换为字典列表
        history_list = []
        for record in history_records:
            history_list.append({
                'id': record[0],
                'task_id': record[1],
                'status': record[2],
                'timestamp': record[3],
                'message': record[4]
            })
        
        conn.close()
        
        return jsonify(history_list)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
