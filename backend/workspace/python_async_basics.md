# Python Async Programming Basics

## Introduction

Python's `asyncio` module provides tools for writing concurrent code using async/await syntax. This guide covers the fundamental concepts of asynchronous programming in Python.

## What is Async Programming?

Asynchronous programming allows a program to handle multiple operations concurrently without using threads or processes. Instead of blocking while waiting for I/O operations to complete, async code can yield control back to the event loop, allowing other tasks to run.

### Key Benefits
- **Non-blocking I/O**: Operations don't block the entire program
- **Resource efficiency**: Uses less memory than threading
- **Simplified concurrency**: Easier to reason about than multi-threaded code
- **Scalability**: Can handle thousands of concurrent operations

## Core Concepts

### Coroutines
A coroutine is a function defined with `async def`. It can pause execution using `await` and resume later.

```python
async def fetch_data(url):
    # This is a coroutine
    data = await get_response(url)
    return data
```

### The Event Loop
The event loop is the heart of asyncio. It runs coroutines, handles callbacks, and manages I/O operations.

```python
import asyncio

async def main():
    print("Hello")
    await asyncio.sleep(1)
    print("World")

asyncio.run(main())
```

### Tasks
A Task is a wrapper around a coroutine that schedules its execution on the event loop.

```python
async def main():
    task = asyncio.create_task(fetch_data(url))
    result = await task
```

### Futures
A Future represents an eventual result of an asynchronous operation. Tasks are a subclass of Future.

## Common Patterns

### Running Multiple Coroutines Concurrently
Use `asyncio.gather()` to run multiple coroutines at the same time:

```python
async def main():
    results = await asyncio.gather(
        fetch_data(url1),
        fetch_data(url2),
        fetch_data(url3)
    )
```

### Waiting for the First Completion
Use `asyncio.wait()` or `asyncio.as_completed()`:

```python
async def main():
    done, pending = await asyncio.wait(
        [fetch_data(url1), fetch_data(url2)],
        return_when=asyncio.FIRST_COMPLETED
    )
```

### Timeouts
Use `asyncio.wait_for()` to set timeouts:

```python
try:
    result = await asyncio.wait_for(fetch_data(url), timeout=5.0)
except asyncio.TimeoutError:
    print("Request timed out")
```

## Best Practices

1. **Use `asyncio.run()`** for the main entry point (Python 3.7+)
2. **Avoid blocking operations** in async functions - use async libraries
3. **Don't mix async and sync code** without careful consideration
4. **Use context managers** for resource management
5. **Handle exceptions properly** in concurrent tasks
6. **Monitor task creation** to avoid creating too many tasks

## Common Pitfalls

- **Forgetting to await**: Not awaiting a coroutine means it won't execute
- **Blocking the event loop**: Using synchronous I/O blocks all tasks
- **Task cancellation**: Cancelled tasks can leave resources in inconsistent states
- **Exception handling**: Exceptions in tasks can be silently ignored if not handled

## Conclusion

Async programming in Python is powerful for I/O-bound operations. Understanding coroutines, the event loop, and common patterns will help you write efficient concurrent applications.
