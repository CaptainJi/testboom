import httpx
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health_check():
    """测试健康检查接口"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["status"] == "ok"

def test_generate_cases():
    """测试生成用例接口"""
    response = client.post(
        "/api/v1/cases/generate",
        json={
            "doc_path": "test.docx",
            "module_name": "登录模块"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert len(data["data"]) > 0
    assert data["data"][0]["module"] == "登录模块"

def test_get_case():
    """测试获取用例详情接口"""
    response = client.get("/api/v1/cases/CASE001")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["case_id"] == "CASE001"

def test_list_cases():
    """测试获取用例列表接口"""
    # 测试无参数查询
    response = client.get("/api/v1/cases")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert len(data["data"]) > 0

    # 测试带参数查询
    response = client.get("/api/v1/cases?module=登录模块&level=P0")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert len(data["data"]) > 0
    assert data["data"][0]["module"] == "登录模块"
    assert data["data"][0]["level"] == "P0" 