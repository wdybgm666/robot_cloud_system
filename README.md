# 机器人云控系统 - Web端地图显示与导航

本项目是一个基于Web的机器人云控制系统，可以实现对机器人的远程监控与操作。本文档将详细介绍如何运行项目以查看地图数据和使用导航功能，以及地图数据的来源和传输过程。

## 项目概述

robot_cloud_system 是一个基于Web的机器人云控制系统，旨在实现对机器人的远程监控与操作。系统采用Flask作为Web框架，使用Flask-SocketIO实现前后端实时通信，并集成ROS 2机器人操作系统进行机器人控制与数据交互。

## 系统要求

- Python 3.x
- ROS 2 (可选，用于真实机器人数据)
- Flask
- Flask-SocketIO
- 其他Python依赖包

## 安装和运行

### 1. 安装依赖

```bash
pip install flask flask-socketio numpy
```

### 2. 运行主应用

```bash
python app.py
```

默认情况下，系统将在 `http://localhost:5000` 启动Web服务。

### 3. 查看地图数据

有两种方式可以查看地图数据：

#### 方式一：使用测试数据（推荐）

运行测试地图发布器来生成模拟地图数据：

```bash
python test_map_publisher.py
```

然后在浏览器中访问 `http://localhost:5000`，切换到"地图与导航"标签页即可看到地图。

#### 方式二：使用真实ROS数据

如果您有运行中的ROS 2系统并发布了地图数据到`/map`话题，系统将自动显示这些数据。

### 4. 使用导航功能

导航功能支持两种模式：

#### 模式一：使用测试导航服务器

运行测试导航服务器来模拟机器人导航：

```bash
python test_navigation_server.py
```

#### 模式二：使用真实ROS导航栈

如果您有运行中的ROS 2导航系统，系统将自动与之交互。

在浏览器中访问 `http://localhost:5000`，切换到"地图与导航"标签页，输入目标点坐标并点击"设置目标点"按钮即可开始导航。

## 地图数据流程说明

地图数据从产生到在Web端显示的完整流程如下：

### 1. 数据来源

地图数据有两种来源：
- **测试数据**：由 `test_map_publisher.py` 脚本生成的模拟地图数据
- **真实数据**：来自ROS 2系统中SLAM节点发布的地图数据

### 2. 数据格式

地图数据使用ROS的 `nav_msgs/OccupancyGrid` 消息格式：

```
Header header           # 消息头
MapMetaData info        # 地图元数据
  time map_load_time    # 地图加载时间
  float32 resolution    # 地图分辨率 (米/格)
  uint32 width          # 地图宽度 (格数)
  uint32 height         # 地图高度 (格数)
  geometry_msgs/Pose origin  # 地图原点位置
int8[] data             # 网格占用数据
```

数据值含义：
- `100`: 占用 (障碍物区域)
- `0`: 空闲 (可通行区域)
- `-1`: 未知区域

### 3. 数据传输过程

```
地图数据源 → ROS 2节点 → WebSocket服务器 → Web浏览器
    ↓           ↓             ↓              ↓
测试脚本/SLAM   app.py    Flask-SocketIO   前端JavaScript
```

详细步骤：
1. 地图数据源（测试脚本或SLAM节点）发布 `OccupancyGrid` 消息到 `/map` 话题
2. 在 `app.py` 中的 `WebNode` 类订阅 `/map` 话题
3. `map_callback` 函数接收并处理地图数据，简化数据结构
4. 通过 `Flask-SocketIO` 的 `socketio.emit('map_update', slim_map)` 方法将数据发送到前端
5. 前端JavaScript接收数据并使用Canvas渲染地图

### 4. 前端渲染

前端使用HTML5 Canvas技术渲染地图：

1. 创建图像数据并根据占用值设置对应颜色：
   - 黑色 (0,0,0) 表示障碍物
   - 白色 (255,255,255) 表示自由空间
   - 灰色 (128,128,128) 表示未知区域

2. 使用Canvas的 `putImageData` 方法将图像数据绘制到临时Canvas

3. 将临时Canvas的内容缩放并绘制到主Canvas上进行显示

## 导航功能说明

### 1. 导航架构

导航功能基于ROS 2的Navigation Stack实现，使用`NavigateToPose` Action接口进行通信。

### 2. 导航数据流

```
Web界面 → WebSocket服务器 → ROS 2 Action客户端 → 导航服务器
   ↓             ↓                ↓                  ↓
用户输入      app.py        NavigateToPose      nav2/测试服务器
```

详细步骤：
1. 用户在Web界面输入目标点坐标并点击"设置目标点"
2. 前端JavaScript通过WebSocket将目标点发送到后端
3. 后端`app.py`中的`WebNode`类接收目标点并创建`NavigateToPose` Action请求
4. Action客户端将请求发送到导航服务器（真实nav2或测试服务器）
5. 导航服务器执行路径规划并避开障碍物，定期发送反馈
6. 后端接收反馈并通过WebSocket发送给前端
7. 前端实时显示机器人位置更新

### 3. 路径规划

测试导航服务器实现了基于A*算法的路径规划，能够：
- 订阅并使用实际地图数据
- 识别障碍物并避开它们
- 计算从当前位置到目标位置的最优路径
- 模拟机器人沿着路径移动

## 项目结构

```
robot_cloud_system/
├── app.py                 # 主应用文件
├── test_map_publisher.py   # 测试地图发布器
├── test_navigation_server.py # 测试导航服务器
├── templates/
│   └── index.html         # 主页面模板
├── static/
│   └── js/
│       ├── map_navigation.js      # 主界面地图导航系统
│       └── map_navigation_test.js # 旧版地图导航系统
├── map_debug.html         # 地图调试页面
├── NAVIGATION_DEVELOPMENT_LOG.md # 导航功能开发日志
└── README.md              # 本说明文件
```

## 调试工具

项目包含几个调试页面帮助诊断问题：

- `http://localhost:5000/map_debug` - 地图渲染调试页面
- `http://localhost:5000/test_websocket` - WebSocket连接测试页面

## 常见问题

### 1. 看不到地图显示

- 确保 `test_map_publisher.py` 正在运行（用于测试）或ROS系统正在发布地图数据
- 检查浏览器控制台是否有JavaScript错误
- 确认WebSocket连接是否正常

### 2. 地图显示不正确

- 检查Canvas尺寸设置是否正确
- 确认地图数据格式是否符合预期
- 查看浏览器开发者工具中的网络面板，确认数据是否正确传输

### 3. 导航功能无法工作

- 确保 `test_navigation_server.py` 正在运行（用于测试）或ROS导航系统正在运行
- 检查浏览器控制台是否有JavaScript错误
- 确认WebSocket连接是否正常
- 查看后端日志确认导航目标是否正确接收

## 扩展开发

如需扩展地图功能，可参考以下文件：
- `app.py` - 后端数据处理和WebSocket通信
- `static/js/map_navigation.js` - 前端地图渲染和交互
- `test_map_publisher.py` - 地图数据生成示例
- `test_navigation_server.py` - 导航功能实现示例

如需扩展导航功能，可参考以下文件：
- `app.py` - 后端导航Action客户端实现
- `test_navigation_server.py` - 导航服务器实现和路径规划算法
- `static/js/map_navigation.js` - 前端导航交互实现

## 许可证

请参阅项目中的 LICENSE 文件了解更多信息。