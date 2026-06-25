"""测试Celery异步任务 — 部署后在服务器上执行: docker exec rebar-app python3 test_celery.py"""
import time
from app.celery_app import celery

# 测试1: detailing占位类型
print("=== 测试1: detailing 占位类型 ===")
r1 = celery.send_task(
    'app.services.ledger_import.process_excel_import',
    args=[1, '/tmp/test.xlsx', 'detailing', 999, None]
)
print(f"Task ID: {r1.id}")
time.sleep(3)
result1 = celery.AsyncResult(r1.id)
print(f"Status: {result1.status}")
print(f"Result: {result1.result}")

# 测试2: 无效task_id查询
print("\n=== 测试2: 无效ID查询 ===")
fake = celery.AsyncResult('nonexistent-task-id')
print(f"Status: {fake.status}")
print("All tests done.")
