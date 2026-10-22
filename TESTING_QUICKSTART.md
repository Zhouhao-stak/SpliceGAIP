# 测试快速指南 ⚡

## 一键运行测试

```bash
# 安装依赖（首次使用）
pip install -r requirements-dev.txt

# 运行全部测试（单元 + API 集成）
pytest tests/unit tests/integration -v

# 查看覆盖率报告
pytest --cov=splicegaip --cov-report=html
start htmlcov\index.html  # Windows
```

## 常用命令速查

| 任务 | 命令 |
|------|------|
| 运行单个测试文件 | `pytest tests/unit/test_schema.py` |
| 运行特定测试函数 | `pytest tests/unit/test_schema.py::TestStandardEvent::test_create_minimal_event` |
| 快速模式（无覆盖率） | `pytest --no-cov` |
| 详细输出 | `pytest -v` |
| 只看失败的测试 | `pytest --lf` |
| 生成 XML 报告 | `pytest --cov-report=xml` |

## 当前状态

✅ **83 个测试全部通过**（65 个单元测试 + 18 个 API 集成测试）  
📊 **当前整体覆盖率**: 27%  
🎯 **当前 CI 门槛**: 20%，后续随新增测试逐步提高

详细说明请参阅 [TESTING.md](TESTING.md)
