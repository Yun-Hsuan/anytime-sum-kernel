# Development Logs

## Database Models and Initialization

### Article Models Implementation (2024-03-xx)

1. Created two main article models:
   - `RawArticle`: For storing original article data
   - `ProcessedArticle`: For storing cleaned and structured article data

2. Key features of the models:
   ```python
   class RawArticle(SQLModel, table=True):
       id: UUID
       source: ArticleSource
       news_id: str
       raw_data: Dict  # Using JSON type for flexible data storage
       status: ArticleStatus
       # Timestamps
       created_at: datetime
       updated_at: datetime

   class ProcessedArticle(SQLModel, table=True):
       id: UUID
       raw_article_id: UUID  # Foreign key to RawArticle
       # Basic Information
       title: str
       content: str
       summary: Optional[str]
       # Metadata
       source: ArticleSource
       category_id: int
       category_name: str
       # Tags and Classifications
       stocks: List[str]  # Using JSON type for array storage
       tags: List[str]    # Using JSON type for array storage
       # Timestamps
       created_at: datetime
       updated_at: datetime
   ```

3. Database Handling Improvements:
   - Implemented automatic table creation during application startup
   - Added proper JSON type support for array and dictionary fields
   - Configured foreign key relationships between models

### RawArticle Model Field Implementation (2024-03-09)

1. 逐步添加 RawArticle 模型字段：
   - 首先簡化模型，只保留 `news_id` 和 `source` 字段進行測試
   - 通過逐步添加字段的方式，確保每個字段都能正確工作
   - 按照以下順序成功添加字段：
     ```python
     class RawArticle(SQLModel, table=True):
         # 系統字段
         id: UUID = Field(default_factory=uuid4, primary_key=True)
         source: ArticleSource = Field(index=True)
         status: ArticleStatus = Field(default=ArticleStatus.PENDING)
         created_at: datetime = Field(default_factory=datetime.utcnow)
         updated_at: datetime = Field(default_factory=datetime.utcnow)
         
         # 文章基本信息
         news_id: str = Field(index=True)
         title: str = Field(index=True)
         copyright: str
         creator: str
         
         # 分類信息
         category_id: int = Field(index=True)
         category_name: str = Field(index=True)
         
         # 時間信息
         pub_date: int
         
         # 內容
         news_content: str
         
         # 標籤
         stock: List[str] = Field(default=[], sa_type=JSON)
         tags: List[str] = Field(default=[], sa_type=JSON)
     ```

2. 實現細節：
   - 為每個字段設置了合適的默認值：
     - 字符串類型使用空字符串 `""`
     - 數字類型使用 `0`
     - 列表類型使用空列表 `[]`
   - 在 `base.py` 和 `cnyes.py` 中保持一致的實現
   - 添加了適當的錯誤處理和日誌記錄

3. 代碼改進：
   ```python
   async def save_raw_article(self, article_data: Dict) -> RawArticle:
       """
       Save raw article data to database with all fields
       """
       article = RawArticle(
           news_id=news_id,
           source=self.source,
           title=article_data.get("title", ""),
           copyright=article_data.get("copyright", ""),
           creator=article_data.get("creator", ""),
           category_id=article_data.get("categoryId", 0),
           category_name=article_data.get("categoryName", ""),
           pub_date=article_data.get("pubDate", 0),
           news_content=article_data.get("newsContent", ""),
           stock=article_data.get("stock", []),
           tags=article_data.get("tags", [])
       )
   ```

4. 技術要點：
   - 使用 `get()` 方法安全地獲取字段值，避免 KeyError
   - 為每個字段提供合適的默認值，確保數據完整性
   - 在保存前進行適當的類型轉換
   - 完善的錯誤處理和日誌記錄

5. 測試和驗證：
   - 使用 API 端點進行測試：
     ```bash
     export LOG_LEVEL=DEBUG
     curl -X POST "http://localhost:8000/api/scraper/cnyes/headline"
     ```
   - 逐步解決了各種字段相關的錯誤
   - 確保所有字段都能正確保存到數據庫

### Database Initialization Setup (2024-03-xx)

1. Enhanced `session.py` with proper async database handling:
   ```python
   # Create async engine with environment-aware logging
   engine = create_async_engine(
       str(settings.SQLALCHEMY_DATABASE_URI),
       echo=settings.ENVIRONMENT == "local" and settings.DEBUG_SQL,
   )

   # Async session factory
   async_session = async_sessionmaker(
       engine,
       expire_on_commit=False,
   )
   ```

2. Implemented safe table initialization:
   - Tables are created only if they don't exist
   - Added logging for better visibility
   - Proper cleanup on application shutdown

3. FastAPI Integration:
   ```python
   @app.on_event("startup")
   async def startup_event():
       """Initialize database when application starts"""
       await init_db()

   @app.on_event("shutdown")
   async def shutdown_event():
       """Clean up resources when application shuts down"""
       await close_db()
   ```

### SQL Debug Logging Implementation (2024-03-xx)

1. Added configurable SQL query logging:
   - Introduced `DEBUG_SQL` setting in `config.py`:
     ```python
     class Settings(BaseSettings):
         # Debug settings
         DEBUG_SQL: bool = False  # Default to False, can be overridden in .env file
     ```

2. Enhanced database engine configuration:
   - SQL query logging only enabled when both conditions are met:
     1. Environment is "local"
     2. DEBUG_SQL is set to true
   ```python
   engine = create_async_engine(
       str(settings.SQLALCHEMY_DATABASE_URI),
       echo=settings.ENVIRONMENT == "local" and settings.DEBUG_SQL,
   )
   ```

3. Environment Configuration:
   - Added to local environment file (`env-config/local/.env`):
     ```env
     # Debug settings
     DEBUG_SQL=true  # Set to true to see SQL queries in logs, false to disable
     ```
   - Can be easily toggled for debugging purposes
   - Automatically disabled in non-local environments

### Technical Notes

1. **JSON Field Usage**:
   - Used SQLAlchemy's JSON type for flexible data storage
   - Handles both arrays (`stocks`, `tags`) and objects (`raw_data`, `processed_data`)
   - Maintains Python type hints while ensuring database compatibility

2. **Database Safety**:
   - `create_all()` is safe and won't overwrite existing tables
   - For schema updates, Alembic migrations should be used
   - Proper connection cleanup implemented

3. **Future Considerations**:
   - Consider implementing Alembic for database migrations
   - Monitor JSON field performance with large datasets
   - Plan for index optimization based on query patterns

### Environment Setup

1. Required Environment Variables:
   ```env
   POSTGRES_SERVER=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=app
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=changethis
   DEBUG_SQL=true  # Optional, for development debugging
   ```

2. Database URL Format:
   ```python
   SQLALCHEMY_DATABASE_URI=postgresql+psycopg://user:password@server:port/dbname
   ``` 