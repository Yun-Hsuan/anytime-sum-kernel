import asyncio
from app.pipeline.orchestration.executor import PipelineExecutor
from app.pipeline.processors.tasks import (
    FetchArticlesTask,
    ProcessArticlesTask,
    GenerateSummariesTask
)

async def run_pipeline_example():
    # Create executor
    executor = PipelineExecutor()
    
    # Set context
    context = {
        "source_type": "tw",  # 改為 "tw"，而不是 "tw_stock"
        "source": "TW_Stock_Summary",  # Source ID defined in source_registry.py 
        "limit": 150
    }
    
    # Configure task pipeline
    executor.set_context(context)
    executor.add_task(FetchArticlesTask())
    executor.add_task(ProcessArticlesTask())
    executor.add_task(GenerateSummariesTask())
    
    try:
        # Execute pipeline
        result = await executor.execute()
        print("Pipeline executed successfully:", result)
        print("\nDetailed results:")
        for key, value in result.items():
            print(f"{key}: {value}")
            
    except ValueError as e:
        print(f"Validation error: {str(e)}")
    except Exception as e:
        print(f"Pipeline execution failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(run_pipeline_example())