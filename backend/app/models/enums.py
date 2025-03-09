from enum import Enum

class CnyesSource(str, Enum):
    """鉅亨網新聞來源"""
    TW_Stock_Summary = "TW_Stock_Summary"           # 台股
    US_Stock_Summary = "US_Stock_Summary"           # 美股
    Hot_News_Summary = "Hot_News_Summary"           # 頭條 