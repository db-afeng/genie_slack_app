from functools import wraps
import asyncio

def poll(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result_waiter = func(*args, **kwargs)
        
        poll_count = 0
        wait_duration = 5

        while not result_waiter.done():             
            await asyncio.sleep(wait_duration)
            poll_count += 1
        
        return result_waiter.result()