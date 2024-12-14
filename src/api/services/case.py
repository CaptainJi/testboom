import json
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models import TestCase, File
from src.api.services.file import FileService
from src.ai_core.chat_manager import ChatManager
from src.api.services.task import TaskManager
from src.db.session import AsyncSessionLocal
from loguru import logger
import zipfile
import os
import glob
import asyncio

class CaseService:
    """用例服务"""
    
    def __init__(self):
        """初始化用例服务"""
        self.chat_manager = ChatManager()
    
    @classmethod
    async def generate_cases_from_file(
        cls,
        file_id: str,
        project_name: str,
        module_name: Optional[str],
        db: AsyncSession
    ) -> str:
        """从文件生成测试用例
        
        Args:
            file_id: 文件ID
            project_name: 项目名称
            module_name: 模块名称
            db: 数据库会话
            
        Returns:
            str: 任务ID
        """
        # 获取文件信息
        file = await FileService.get_file_by_id(file_id, db)
        if not file:
            raise ValueError("文件不存在")
            
        # 更新文件状态为处理中
        await FileService.update_file_status(file, "processing", db=db)
        
        # 创建任务
        task_id = TaskManager.create_task("generate_cases")
        
        try:
            # 启动后台任务
            asyncio.create_task(
                TaskManager.run_background_task(
                    task_id,
                    cls._generate_cases,
                    file,
                    project_name,
                    module_name,
                    db
                )
            )
            
            return task_id
            
        except Exception as e:
            # 更新文件状态为失败
            await FileService.update_file_status(
                file,
                "failed",
                error=str(e),
                db=db
            )
            raise
            
    @classmethod
    async def _generate_cases(
        cls,
        file: File,
        project_name: str,
        module_name: Optional[str],
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """生成测试用例的具体实现"""
        # 创建新的数据库会话
        async with AsyncSessionLocal() as session:
            try:
                # 在新会话中获取文件对象
                result = await session.execute(
                    select(File).where(File.id == file.id)
                )
                file = result.scalar_one()
                
                # 根据文件类型处理
                if file.type == "zip":
                    cases = await cls._process_zip_file(file, project_name, module_name)
                else:
                    cases = await cls._process_image_file(file, project_name, module_name)
                    
                # 保存用例到数据库
                case_infos = []
                for case in cases:
                    case.file_id = file.id
                    session.add(case)
                    case_infos.append({
                        'id': str(case.id),
                        'project': project_name,
                        'module': case.module,
                        'name': case.name,
                        'level': case.level,
                        'status': case.status,
                        'content': json.loads(case.content)
                    })
                
                # 更新文件状态为完成
                await FileService.update_file_status(file, "completed", db=session)
                await session.commit()
                
                return case_infos
                
            except Exception as e:
                # 更新文件状态为失败
                await FileService.update_file_status(
                    file,
                    "failed",
                    error=str(e),
                    db=session
                )
                await session.rollback()
                raise
    
    @classmethod
    async def _process_zip_file(
        cls,
        file: File,
        project_name: str,
        module_name: Optional[str]
    ) -> List[TestCase]:
        """处理ZIP文件"""
        cases = []
        extract_path = os.path.join(os.path.dirname(file.path), "temp")
        
        try:
            # 解压文件
            with zipfile.ZipFile(file.path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
                
            # 获取所有图片文件
            image_files = []
            for ext in ['*.png', '*.jpg', '*.jpeg']:
                image_files.extend(
                    glob.glob(os.path.join(extract_path, '**', ext), recursive=True)
                )
                
            if not image_files:
                raise ValueError("ZIP文件中未找到图片")
                
            # 创建ChatManager实例
            chat_manager = ChatManager()
            
            # 分析需求并生成用例
            summary = chat_manager.analyze_requirement(
                content=f"模块名称: {module_name}" if module_name else "",
                image_paths=image_files
            )
            
            if not summary:
                raise ValueError("需求分析失败")
                
            # 生成测试用例
            testcases = chat_manager.generate_testcases(
                summary=summary,
                details={
                    "images": [
                        {
                            "content": summary,
                            "features": {}
                        }
                    ]
                }
            )
            
            if not testcases:
                raise ValueError("用例生成失败")
            
            # 转换为TestCase对象
            for case_data in testcases:
                case = TestCase(
                    project=project_name,
                    module=module_name or case_data.get('module', '默认模块'),
                    name=case_data.get('name', '未命名用例'),
                    level=case_data.get('level', 'P2'),
                    status='ready',
                    content=json.dumps(case_data)
                )
                cases.append(case)
                
        finally:
            # 清理临时文件
            if os.path.exists(extract_path):
                import shutil
                shutil.rmtree(extract_path)
                
        return cases
    
    @classmethod
    async def _process_image_file(
        cls,
        file: File,
        project_name: str,
        module_name: Optional[str]
    ) -> List[TestCase]:
        """处理图片文件"""
        # 创建ChatManager实例
        chat_manager = ChatManager()
        
        # 分析需求并生成用例
        summary = chat_manager.analyze_requirement(
            content=f"模块名称: {module_name}" if module_name else "",
            image_paths=[file.path]
        )
        
        if not summary:
            raise ValueError("需求分析失败")
            
        # 生成测试用例
        testcases = chat_manager.generate_testcases(
            summary=summary,
            details={
                "images": [
                    {
                        "content": summary,
                        "features": {}
                    }
                ]
            }
        )
        
        if not testcases:
            raise ValueError("用例生成失败")
        
        # 转换为TestCase对象
        cases = []
        for case_data in testcases:
            case = TestCase(
                project=project_name,
                module=module_name or case_data.get('module', '默认模块'),
                name=case_data.get('name', '未命名用例'),
                level=case_data.get('level', 'P2'),
                status='ready',
                content=json.dumps(case_data)
            )
            cases.append(case)
            
        return cases
    
    @classmethod
    async def get_case_by_id(
        cls,
        case_id: str,
        db: AsyncSession
    ) -> Optional[TestCase]:
        """根据ID获取用例
        
        Args:
            case_id: 用例ID
            db: 数据库会话
            
        Returns:
            Optional[TestCase]: 用例对象，如果不存在则返回None
        """
        try:
            # 查询用例
            result = await db.execute(
                select(TestCase).where(TestCase.id == case_id)
            )
            case = result.scalar_one_or_none()
            
            if case:
                logger.debug(f"获取到用例: {case.id}")
            else:
                logger.warning(f"未找到用例: {case_id}")
                
            return case
            
        except Exception as e:
            logger.error(f"获取用例失败: {str(e)}")
            raise
    
    @classmethod
    async def list_cases(
        cls,
        db: AsyncSession,
        project: Optional[str] = None,
        module: Optional[str] = None,
        level: Optional[str] = None
    ) -> List[TestCase]:
        """获取用例列表
        
        Args:
            db: 数据库会话
            project: 项目名称
            module: 模块名称
            level: 用例等级
            
        Returns:
            List[TestCase]: 用例列表
        """
        try:
            # 构建基础查询
            query = select(TestCase)
            
            # 添加查询条件
            conditions = []
            
            if project:
                # 记录查询条件
                logger.info(f"查询项目: {project}")
                # 使用 project 字段查询
                conditions.append(TestCase.project == project)
                
            if module:
                logger.info(f"查询模块: {module}")
                conditions.append(TestCase.module == module)
                
            if level:
                logger.info(f"查询等级: {level}")
                conditions.append(TestCase.level == level)
                
            # 组合所有条件
            if conditions:
                query = query.where(*conditions)
                
            # 执行查询
            result = await db.execute(query)
            cases = result.scalars().all()
            
            # 记录查询结果
            logger.info(f"查询到 {len(cases)} 条用例")
            for case in cases:
                logger.debug(f"用例内容: {case.content}")
                
            return cases
            
        except Exception as e:
            logger.error(f"查询用例失败: {str(e)}")
            return []
    