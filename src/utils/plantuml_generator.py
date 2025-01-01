from typing import List, Dict, Any, Optional
from src.logger.logger import logger

class PlantUMLGenerator:
    """PlantUML 图表生成器"""
    
    def generate_mindmap(self, testcases: List[Dict[str, Any]]) -> str:
        """生成思维导图格式的PlantUML代码
        
        Args:
            testcases: 测试用例列表
            
        Returns:
            str: PlantUML代码
        """
        try:
            plantuml_code = ["@startmindmap", "* 测试用例集"]
            
            # 按模块分组
            modules = {}
            for case in testcases:
                module = case.get("module", "未分类")
                if module not in modules:
                    modules[module] = []
                modules[module].append(case)
            
            # 生成思维导图结构
            for module, cases in modules.items():
                plantuml_code.append(f"** {module}")
                for case in cases:
                    # 用例名称和ID
                    plantuml_code.append(f"*** {case['name']} ({case['id']})")
                    # 用例等级
                    plantuml_code.append(f"**** 等级: {case['level']}")
                    # 前置条件
                    if case.get('precondition'):
                        plantuml_code.append(f"**** 前置条件: {case['precondition']}")
                    # 测试步骤
                    plantuml_code.append("**** 测试步骤:")
                    for i, step in enumerate(case['steps'], 1):
                        plantuml_code.append(f"***** {i}. {step}")
                    # 预期结果
                    plantuml_code.append("**** 预期结果:")
                    for i, expected in enumerate(case['expected'], 1):
                        plantuml_code.append(f"***** {i}. {expected}")
            
            plantuml_code.append("@endmindmap")
            return "\n".join(plantuml_code)
            
        except Exception as e:
            logger.error(f"生成思维导图失败: {str(e)}")
            return ""

    def generate_sequence(self, testcase: Dict[str, Any]) -> str:
        """生成时序图格式的PlantUML代码
        
        Args:
            testcase: 单个测试用例
            
        Returns:
            str: PlantUML代码
        """
        try:
            plantuml_code = [
                "@startuml",
                f"title {testcase['name']} ({testcase['id']})",
                "skinparam sequenceMessageAlign center",
                "skinparam responseMessageBelowArrow true",
                "",
                "actor User",
                "participant System"
            ]
            
            # 添加前置条件
            if testcase.get('precondition'):
                plantuml_code.extend([
                    "note over User, System",
                    f"前置条件: {testcase['precondition']}",
                    "end note",
                    ""
                ])
            
            # 添加测试步骤和预期结果
            for i, (step, expected) in enumerate(zip(testcase['steps'], testcase['expected']), 1):
                plantuml_code.extend([
                    f"User -> System: {i}. {step}",
                    f"System --> User: {expected}",
                    ""
                ])
            
            plantuml_code.append("@enduml")
            return "\n".join(plantuml_code)
            
        except Exception as e:
            logger.error(f"生成时序图失败: {str(e)}")
            return "" 