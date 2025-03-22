class SchedulerError(Exception):
    """排程器基礎異常類"""
    pass

class TaskNotFoundError(SchedulerError):
    """任務不存在異常"""
    pass

class TaskExecutionError(SchedulerError):
    """任務執行異常"""
    pass

class TaskConfigurationError(SchedulerError):
    """任務配置異常"""
    pass

class ServiceStateError(SchedulerError):
    """服務狀態異常"""
    pass 