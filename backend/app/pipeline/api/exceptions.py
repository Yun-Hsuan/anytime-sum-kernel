class PipelineAPIError(Exception):
    """基礎 Pipeline API 異常"""
    pass

class RequestTimeoutError(PipelineAPIError):
    """請求超時異常"""
    pass

class APIConnectionError(PipelineAPIError):
    """API 連接異常"""
    pass

class APIResponseError(PipelineAPIError):
    """API 響應異常"""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"API 錯誤 {status_code}: {message}") 