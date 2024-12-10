#!/bin/bash

# 测试健康检查接口
echo "Testing health check endpoint..."
curl -X GET http://localhost:8000/health

echo -e "\n\nTesting case generation endpoint..."
curl -X POST http://localhost:8000/api/v1/cases/generate \
  -H "Content-Type: application/json" \
  -d '{"doc_path": "test.docx", "module_name": "登录模块"}'

echo -e "\n\nTesting get case endpoint..."
curl -X GET http://localhost:8000/api/v1/cases/CASE001

echo -e "\n\nTesting list cases endpoint..."
curl -X GET "http://localhost:8000/api/v1/cases?module=登录模块&level=P0"

echo -e "\n\nDone!" 