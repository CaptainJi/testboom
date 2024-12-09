import pytest
import os
from pathlib import Path
from src.ai_core.chat_manager import ChatManager
from src.logger.logger import logger

def test_chat_manager():
    """测试基本对话功能"""
    manager = ChatManager()
    
    # 测试单轮对话
    question = "解释一下什么是自动化测试?"
    logger.info(f"\n提问: {question}")
    
    reply = manager.chat(question)
    assert reply is not None
    logger.info(f"\n回复: {reply}")
    assert len(manager.history) == 2  # user消息和assistant回复

def test_chat_manager_with_image():
    """测试图片理解功能"""
    manager = ChatManager()
    
    # 准备图片路径
    image_path = "tests/test_data/需求背景.png"
    assert Path(image_path).exists(), f"图片文件不存在: {image_path}"
    
    # 测试图片理解
    question = "这个项目的技术架构是怎样的?请根据图片内容详细说明。"
    logger.info(f"\n提问: {question}")
    logger.info(f"图片路径: {image_path}")
    
    reply = manager.chat_with_images(question, [image_path])
    assert reply is not None
    logger.info(f"\n回复: {reply}")
    assert len(manager.history) == 2  # user消息和assistant回复

def test_requirement_analysis():
    """测试需求分析功能"""
    manager = ChatManager()
    
    # 准备测试数据
    requirement_text = """
    图书馆管理系统需求：
    1. 空间管理
       - 统计使用情况
       - 开放时间通知
       - 客流统计
    2. 人员管理
       - 信息录入
       - 考勤管理
       - 权限设置
    3. 设备管理
       - 设备监控
       - 使用统计
    """
    
    # 测试文本需求分析
    logger.info("\n测试文本需求分析:")
    result = manager.analyze_requirement(requirement_text)
    assert result is not None
    logger.info(f"\n分析结果:\n{result}")
    
    # 测试带图片的需求分析
    image_path = "tests/test_data/需求背景.png"
    assert Path(image_path).exists()
    
    logger.info("\n测试带图片的需求分析:")
    result = manager.analyze_requirement(requirement_text, [image_path])
    assert result is not None
    logger.info(f"\n分析结果:\n{result}")

def test_testcase_generation():
    """测试用例生成功能"""
    manager = ChatManager()
    
    # 准备需求分析结果
    analysis_result = """
    功能点列表：
    1. 空间管理
       - 统计使用情况
       - 开放时间通知
       - 客流统计
    
    业务流程：
    1. 空间使用统计
       - 收集使用数据
       - 生成统计报表
       - 展示统计结果
    
    数据流向：
    1. 客流数据 -> 统计模块 -> 报表展示
    2. 使用记录 -> 统计分析 -> 使用报告
    
    接口定义：
    1. 数据采集接口
    2. 统计分析接口
    3. 报表生成接口
    """
    
    logger.info("\n测试用例生成:")
    result = manager.generate_testcases(analysis_result)
    assert result is not None
    logger.info(f"\n生成的测试用例:\n{result}")

def test_testcase_analysis():
    """测试用例分析功能"""
    manager = ChatManager()
    
    # 准备测试用例
    testcases = """
    |用例ID|所属模块|用例名称|用例等级|前置条件|测试步骤|预期结果|实际结果|测试状态|备注|
    |TC001|空间管理|统计使用情况|P0|系统正常运行|1.进入统计页面<br>2.选择时间范围<br>3.点击统计按钮|1.页面正常显示<br>2.时间范围可选择<br>3.显示统计结果|待执行|未执行||
    |TC002|空间管理|开放时间通知|P1|系统正常运行|1.进入通知管理<br>2.设置开放时间<br>3.发送通知|1.页面正常显示<br>2.时间可设置<br>3.通知发送成功|待执行|未执行||
    """
    
    logger.info("\n测试用例分析:")
    result = manager.analyze_testcases(testcases)
    assert result is not None
    logger.info(f"\n分析结果:\n{result}")