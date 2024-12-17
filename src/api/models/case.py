class TestCase(Base):
    """测试用例模型"""
    
    __tablename__ = "testcase"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project = Column(String(100), nullable=False, comment="项目名称")
    module = Column(String(100), nullable=False, comment="模块名称")
    name = Column(String(200), nullable=False, comment="用例名称")
    level = Column(String(10), nullable=False, comment="用例等级")
    precondition = Column(String(500), nullable=True, comment="前置条件")
    steps = Column(JSON, nullable=False, comment="测试步骤")
    expected = Column(JSON, nullable=False, comment="预期结果")
    actual = Column(String(500), nullable=True, comment="实际结果")
    status = Column(String(20), nullable=True, comment="测试状态")
    remark = Column(String(500), nullable=True, comment="备注")
    task_id = Column(String(36), nullable=True, comment="任务ID")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间") 