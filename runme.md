# SDBR 编译、测试与启动指令

本文档记录本项目在 Windows / PowerShell 下的常用检查、测试和启动命令。

## 1. 进入项目目录

```powershell
cd D:\Documents\SDBR
```

## 2. 安装依赖

建议使用 Python 3.11 或更高版本。

```powershell
python -m pip install -U pip
python -m pip install -e ".[api]"
python -m pip install pytest ortools
```

说明：

- `.[api]` 安装 FastAPI、Uvicorn、HTTPX 等 API 运行依赖。
- `ortools` 是当前第一版唯一启用的排程求解器 CP-SAT。
- Gurobi 已暂停新任务执行，不作为启动必需依赖。
- Simio 本机 Headless 验证是可选增强能力；普通启动和全量测试不依赖 Simio 许可。

## 3. 编译 / 语法检查

```powershell
python -m compileall -q sdbr
```

如果修改了前端脚本，可额外检查 JavaScript 语法。若系统没有全局 `node`，请使用 Codex 工作区自带 Node 路径。

```powershell
node --check sdbr\web\planner-workbench.js
```

或：

```powershell
& "C:\Users\wyfch\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" --check sdbr\web\planner-workbench.js
```

## 4. 运行测试

全量测试：

```powershell
pytest -q --basetemp .tmp\pytest-full -p no:cacheprovider
```

常用定向测试：

```powershell
pytest tests\test_api.py -q
pytest tests\test_scheduling_solver.py -q
pytest tests\test_dispatch_priority.py tests\test_integration_contracts.py -q
pytest tests\test_simio_model_template.py tests\test_simio_validation.py -q
```

## 5. 启动测试系统服务

测试系统默认端口是 `8765`，默认数据库路径是：

```text
data\test\workbench-state.db
```

前台启动：

```powershell
$env:SDBR_ENVIRONMENT = "test"
python -m uvicorn sdbr.api:app --host 127.0.0.1 --port 8765
```

访问地址：

```text
http://127.0.0.1:8765/planner/workbench
```

健康检查：

```powershell
Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8765/planner/workbench/state-store/health
```

## 6. 后台启动测试系统服务

```powershell
$processIds = (Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue).OwningProcess | Sort-Object -Unique
foreach ($processId in $processIds) { Stop-Process -Id $processId -Force }

Start-Process -WindowStyle Hidden `
  -FilePath python `
  -ArgumentList @("-m", "uvicorn", "sdbr.api:app", "--host", "127.0.0.1", "--port", "8765") `
  -WorkingDirectory "D:\Documents\SDBR" `
  -RedirectStandardOutput "D:\Documents\SDBR\uvicorn.out.log" `
  -RedirectStandardError "D:\Documents\SDBR\uvicorn.err.log"

Start-Sleep -Seconds 2
(Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8765/planner/workbench -TimeoutSec 5).StatusCode
```

停止测试系统服务：

```powershell
$processIds = (Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue).OwningProcess | Sort-Object -Unique
foreach ($processId in $processIds) { Stop-Process -Id $processId -Force }
```

## 7. 启动生产系统服务

生产系统默认端口是 `8766`，默认数据库路径是：

```text
data\production\workbench-state.db
```

```powershell
$env:SDBR_ENVIRONMENT = "production"
python -m uvicorn sdbr.api:app --host 127.0.0.1 --port 8766
```

访问地址：

```text
http://127.0.0.1:8766/planner/workbench
```

## 8. 指定数据库路径

如需使用独立数据库文件：

```powershell
$env:SDBR_ENVIRONMENT = "test"
$env:SDBR_WORKBENCH_DB_PATH = "D:\Documents\SDBR\data\test\workbench-state.db"
python -m uvicorn sdbr.api:app --host 127.0.0.1 --port 8765
```

## 9. Planning Run Worker

服务启动后，可另开一个 PowerShell 窗口启动 Worker。Worker 会领取已入队的 Planning Run，并调用 API 执行排程。

```powershell
sdbr-planning-worker --base-url http://127.0.0.1:8765 --worker-id worker-1
```

如果命令行脚本没有进入 PATH，可用模块方式：

```powershell
python -m sdbr.planning_worker --base-url http://127.0.0.1:8765 --worker-id worker-1
```

## 10. 测试数据

重置或生成测试数据：

```powershell
sdbr-reset-test-data
```

如果脚本没有进入 PATH：

```powershell
python -m sdbr.test_data
```

## 11. Simio 可选验证

普通 API 启动、排程和测试不要求 Simio。

如果要运行本机 Simio Headless 验证，需要本机安装 Simio，并先确保许可服务可用：

```powershell
Start-Process -WindowStyle Hidden -FilePath "D:\Program Files\Simio LLC\RLM\rlm.exe"
```

Simio 官方 PDF 参考资料是本地资料，已被 `.gitignore` 忽略，不应提交到 GitHub。若需要查阅，请放在本机 `model\` 目录下。

## 12. Git 注意事项

提交前查看状态：

```powershell
git status --short
```

`nofinish\` 是临时目录，不需要跟踪或提交。

