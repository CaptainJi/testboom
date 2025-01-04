import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.api.services.case import CaseService
from src.db.models import TestCase, File
import json
from typing import List

@pytest_asyncio.fixture
async def db_session():
    """创建测试数据库会话"""
    from src.db.session import get_db
    async for session in get_db():
        # 清理数据库
        await session.execute(text("DELETE FROM testcase"))
        await session.execute(text("DELETE FROM file"))
        await session.commit()
        
        yield session
        await session.rollback()

@pytest_asyncio.fixture
async def test_file(db_session: AsyncSession) -> File:
    """创建测试文件记录"""
    file = File(
        name="test.jpg",
        type="image",
        path="test/path",
        status="success"
    )
    db_session.add(file)
    await db_session.commit()
    await db_session.refresh(file)
    return file

@pytest_asyncio.fixture
async def test_cases(db_session: AsyncSession, test_file: File) -> List[TestCase]:
    """创建测试用例记录"""
    cases = []
    for i in range(3):
        case = TestCase(
            project="test_project",
            module="test_module",
            name=f"test_case_{i}",
            level="P1",
            status="ready",
            content=json.dumps({
                "name": f"test_case_{i}",
                "steps": ["step1", "step2"],
                "expected": "expected result"
            }),
            file_id=test_file.id
        )
        db_session.add(case)
        cases.append(case)
    await db_session.commit()
    for case in cases:
        await db_session.refresh(case)
    return cases

@pytest.mark.asyncio
async def test_get_case_by_id(db_session: AsyncSession, test_cases: List[TestCase]):
    """测试通过ID获取用例"""
    # 获取第一个测试用例
    test_case = test_cases[0]
    
    # 获取用例
    case = await CaseService.get_case_by_id(test_case.id, db_session)
    
    # 验证结果
    assert case is not None
    assert case.id == test_case.id
    assert case.project == "test_project"
    assert case.module == "test_module"
    assert case.name == "test_case_0"
    assert case.level == "P1"
    assert case.status == "ready"
    
    # 验证内容
    content = json.loads(case.content)
    assert content["name"] == "test_case_0"
    assert "steps" in content
    assert "expected" in content

@pytest.mark.asyncio
async def test_list_cases(db_session: AsyncSession, test_cases: List[TestCase]):
    """测试获取用例列表"""
    # 获取所有用例
    cases = await CaseService.list_cases(
        db_session,
        project="test_project",
        module="test_module"
    )
    
    # 验证结果
    assert len(cases) == len(test_cases)
    for case in cases:
        assert case.project == "test_project"
        assert case.module == "test_module"
        assert case.level == "P1"
        assert case.status == "ready"

@pytest.mark.asyncio
async def test_delete_case(db_session: AsyncSession, test_cases: List[TestCase]):
    """测试删除用例"""
    # 获取第一个测试用例
    test_case = test_cases[0]
    
    # 删除用例
    success = await CaseService.delete_case(test_case.id, db_session)
    
    # 验证结果
    assert success is True
    
    # 验证用例已被删除
    deleted_case = await CaseService.get_case_by_id(test_case.id, db_session)
    assert deleted_case is None

@pytest.mark.asyncio
async def test_batch_delete_cases(db_session: AsyncSession, test_cases: List[TestCase]):
    """测试批量删除用例"""
    # 获取所有测试用例ID
    case_ids = [case.id for case in test_cases]
    
    # 批量删除用例
    results = await CaseService.batch_delete_cases(case_ids, db_session)
    
    # 验证结果
    assert len(results) == 3
    for case_id in case_ids:
        assert results[case_id] is True
        # 验证用例已被删除
        deleted_case = await CaseService.get_case_by_id(case_id, db_session)
        assert deleted_case is None

@pytest.mark.asyncio
async def test_update_case(db_session: AsyncSession, test_cases: List[TestCase]):
    """测试更新用例信息"""
    # 获取第一个测试用例
    test_case = test_cases[0]
    
    # 更新用例信息
    updated_case = await CaseService.update_case(
        case_id=test_case.id,
        project="updated_project",
        module="updated_module",
        name="updated_case",
        level="P0",
        status="completed",
        content={"name": "updated_case", "steps": ["new_step"]},
        remark="测试更新",
        db=db_session
    )
    
    # 验证结果
    assert updated_case is not None
    assert updated_case.project == "updated_project"
    assert updated_case.module == "updated_module"
    assert updated_case.name == "updated_case"
    assert updated_case.level == "P0"
    assert updated_case.status == "completed"
    
    # 验证内容
    content = json.loads(updated_case.content)
    assert content["name"] == "updated_case"
    assert content["steps"] == ["new_step"]
    
    # 验证修改历史
    assert len(updated_case.history) == 6  # project, module, name, level, status, content
    
    # 验证每个字段的修改记录
    history_fields = [h.field for h in updated_case.history]
    assert "project" in history_fields
    assert "module" in history_fields
    assert "name" in history_fields
    assert "level" in history_fields
    assert "status" in history_fields
    assert "content" in history_fields
    
    # 验证修改说明
    for history in updated_case.history:
        assert history.remark == "测试更新"
        
@pytest.mark.asyncio
async def test_update_case_no_changes(db_session: AsyncSession, test_cases: List[TestCase]):
    """测试更新用例信息但没有实际变化"""
    # 获取第一个测试用例
    test_case = test_cases[0]
    
    # 使用相同的值更新用例
    updated_case = await CaseService.update_case(
        case_id=test_case.id,
        project=test_case.project,
        module=test_case.module,
        name=test_case.name,
        level=test_case.level,
        status=test_case.status,
        content=json.loads(test_case.content),
        remark="无变化更新",
        db=db_session
    )
    
    # 验证结果
    assert updated_case is not None
    assert len(updated_case.history) == 0  # 没有修改历史记录
    
@pytest.mark.asyncio
async def test_update_case_partial(db_session: AsyncSession, test_cases: List[TestCase]):
    """测试部分更新用例信息"""
    # 获取第一个测试用例
    test_case = test_cases[0]
    
    # 只更新部分字段
    updated_case = await CaseService.update_case(
        case_id=test_case.id,
        name="new_name",
        level="P1",
        remark="部分更新",
        db=db_session
    )
    
    # 验证结果
    assert updated_case is not None
    assert updated_case.name == "new_name"
    assert updated_case.level == "P1"
    assert updated_case.project == test_case.project  # 未修改的字段保持不变
    assert updated_case.module == test_case.module    # 未修改的字段保持不变
    
    # 验证修改历史
    assert len(updated_case.history) == 2  # 只有name和level的修改记录
    history_fields = [h.field for h in updated_case.history]
    assert "name" in history_fields
    assert "level" in history_fields
    
@pytest.mark.asyncio
async def test_update_case_invalid_id(db_session: AsyncSession):
    """测试更新不存在的用例"""
    with pytest.raises(ValueError) as exc_info:
        await CaseService.update_case(
            case_id="invalid_id",
            name="new_name",
            db=db_session
        )
    assert str(exc_info.value) == "用例不存在"

@pytest.mark.asyncio
async def test_generate_cases_from_file(db_session: AsyncSession, test_file: File):
    """测试从文件生成用例"""
    # 生成用例
    task_id = await CaseService.generate_cases_from_file(
        file_id=test_file.id,
        project_name="test_project",
        module_name="test_module",
        db=db_session
    )
    
    # 验证结果
    assert task_id is not None
    
    # 注意:这里不验证实际的用例生成过程,因为它是异步的
    # 实际应用中应该等待任务完成并验证生成的用例