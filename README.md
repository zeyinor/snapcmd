# SnapCmd v1.0.0

把每天重复敲的长命令，压缩成 3 个字母。

## 使用

双击 `dist\SnapCmd.exe` 即可，无需安装 Python。

首次启动会在 `%APPDATA%\SnapCmd\commands.json` 写入内置示例（docker / kubectl / git / python 共 10 条）。

## 功能

- **3 字母别名**：每条命令一个短别名（`dcd` / `kpg` / `glo` ...）
- **即输即搜**：顶部搜索框按别名 / 描述 / 标签模糊过滤
- **交互式参数填充**：命令模板里写 `{{参数名}}` 或 `{{参数名:默认值}}`，选命令后自动出现输入框
- **一键复制**：Enter 或「复制到剪贴板」按钮
- **一键执行**：Ctrl+Enter 在新 cmd 窗口跑
- **增删改**：GUI 内直接编辑，或点「打开配置文件」手改 JSON

## 参数语法示例

模板：

```
docker compose -f docker-compose.dev.yml up -d --build {{service}}
kubectl get pods -n {{namespace:production}} -o wide
```

选中命令后，右侧会出现 `service`、`namespace` 输入框，填完即实时拼出最终命令。

## 快捷键

| 按键 | 作用 |
|---|---|
| 输入即搜 | 顶部搜索框自动过滤 |
| Enter | 复制最终命令到剪贴板 |
| Ctrl+Enter | 在新终端执行 |
| Ctrl+N | 新增命令 |
| F5 | 刷新列表 |
| Esc | 清空搜索 |
| 双击列表项 | 直接复制 |

## 重新打包

修改 `snapcmd.py` 后双击 `build.bat`，产物在 `dist\SnapCmd.exe`。
