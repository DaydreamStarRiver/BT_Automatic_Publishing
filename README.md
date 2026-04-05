# 🎬 BT 自动发布系统 (BT Auto Publishing System)

> **v2.1** | 7×24 小时无人值守的 BT 资源自动发布系统

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## ✨ 核心功能

- 🔍 **自动监控** - 实时扫描指定文件夹中的新视频文件
- 📦 **自动生成** - Torrent 种子文件（支持 40+ Tracker）
- 🚀 **自动发布** - 到主流 BT 站点（通过 [OKP](https://github.com/AmusementClub/OKP) 工具）
- 🔄 **智能重试** - 发布失败时自动重试（最多 3 次，指数退避）
- 💾 **断点恢复** - 程序重启后自动继续未完成任务
- 🌐 **Web 管理面板** - 浏览器管理任务 / 查看日志 / 手动操作
- 🔌 **REST API** - 完整的 HTTP 接口，支持远程控制

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Windows / Linux / macOS
- （可选）OKP 工具用于 BT 发布

### 安装与运行

```bash
# 克隆项目
git clone <your-repo-url>
cd BT_Automatic_Publishing_copy

# 安装依赖
pip install -r requirements.txt

# 启动系统
python main.py
```

启动成功后，打开浏览器访问：

```
http://localhost:8080
```

### 测试使用

将视频文件放入 `data/watch/` 目录，系统会自动：

1. 检测到新视频文件
2. 提取视频信息并生成 Torrent
3. 调用 OKP 发布到 BT 站点
4. 在 Web 面板显示任务状态和实时日志

---

## ⚙️ 配置说明

编辑 `config.yaml` 即可配置系统参数：

```yaml
# 监控目录
watch_dir: ./data/watch

# OKP 发布配置
okp_auto_confirm: true          # true=全自动 false=手动确认
okp_preview_only: false         # true=仅预览不发布

# Web 面板配置（可选）
web_enabled: true
web_port: 8080
```

完整配置项请查看 [部署说明文档](docs/deployment.md)

---

## 📁 项目结构

```
BT_Automatic_Publishing/
├── main.py                 # 主程序入口
├── config.yaml             # 配置文件
├── requirements.txt        # 依赖列表
│
├── src/
│   ├── web/                # Web 面板 + REST API
│   │   ├── api.py          # FastAPI 后端
│   │   └── panel.html      # 前端面板
│   └── core/
│       ├── task_model.py       # 任务数据模型
│       ├── task_worker.py      # 执行引擎
│       ├── task_queue.py       # 任务队列
│       ├── watcher.py          # 文件监控
│       ├── torrent_builder.py  # Torrent 生成
│       └── executor_okp.py     # OKP 调用器
│
└── data/
    ├── watch/              # 监控目录
    ├── torrents/           # Torrent 输出目录
    └── tasks.json          # 任务持久化数据库
```

---

## 📚 文档导航

| 文档 | 说明 |
|------|------|
| [🏗️ 系统架构](docs/architecture.md) | 架构图、组件职责、设计模式 |
| [🔄 任务流程](docs/workflow.md) | 处理流程、状态机、重试机制 |
| [🔌 API 接口](docs/api.md) | REST API 说明、请求示例 |
| [🚀 部署说明](docs/deployment.md) | 安装配置、环境搭建、常见问题 |
| [💻 开发指南](docs/development.md) | 开发规范、模块详解、扩展开发 |

---

## 🎯 适用场景

- 动画/视频资源批量发布
- PT 站点自动化维护
- 长期运行的发布任务队列
- 7×24 小时无人值守发布

---

## 🛠️ 技术栈

| 技术 | 用途 |
|------|------|
| Python 3.10+ | 核心语言 |
| FastAPI + Uvicorn | Web 后端 |
| Watchdog | 文件系统监控 |
| PyMediaInfo | 视频信息提取 |
| torf | Torrent 文件生成 |
| OKP | BT 站点发布 |

---

## 📈 版本历史

### v2.1 - Web 面板版 ⭐ 当前版本

- ✅ Web 管理界面（FastAPI + 单文件前端）
- ✅ REST API（任务 CRUD、SSE 日志流）
- ✅ 实时日志推送
- ✅ 手动触发 / 重试 / 删除任务

### v2.0 - 队列架构版

- ✅ 任务队列系统（Queue + Worker 异步架构）
- ✅ 状态机驱动（7 种显式状态转换）
- ✅ 自动重试机制（指数退避策略）
- ✅ JSON 持久化（断点恢复）

### v1.x - MVP 版本

- ✅ Watchdog 文件夹监控
- ✅ 视频信息提取（PyMediaInfo）
- ✅ Torrent 生成（torf 库）
- ✅ OKP 一键发布集成

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

详细开发规范请查看 [开发指南](docs/development.md)

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- [OKP](https://github.com/AmusementClub/OKP) - BT 站点发布工具
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Web 框架
- 所有贡献者和使用者

---

**最后更新：** 2026-04-05  
**当前版本：** v2.1.0  
**作者：** BT Auto Publishing Team
