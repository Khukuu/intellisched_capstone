# intellisched\_capstone

Automatic Scheduling LPU\_B

How to start

1. Open terminal
2. Activate virtual environment ".venv\\Scripts\\activate"
3. Run the app "uvicorn app:app --reload"





Dependencies

1. fastAPI
2. uvicorn
3. psycopg2-binary
4. sqlalchemy
5. ortools
6. python-multipart





Database setup

1. Install PostgreSQL
2. Run createDB\_script.sql (mysql -u root -p < intellisched.sql)





**python -c "import jwt; print('JWT library:', jwt.\_\_file\_\_); print('Version:', getattr(jwt, '\_\_version\_\_', 'Unknown'))"**


Issues:
File "C:\Python313\Lib\asyncio\runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "C:\Python313\Lib\asyncio\base_events.py", line 719, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
asyncio.exceptions.CancelledError

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\Python313\Lib\asyncio\runners.py", line 195, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "C:\Python313\Lib\asyncio\runners.py", line 123, in run
    raise KeyboardInterrupt()
KeyboardInterrupt

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\Users\chlar\documents\repositories\test\intellisched_capstone\algorithm\.venv\Lib\site-packages\starlette\routing.py", line 701, in lifespan
    await receive()
  File "C:\Users\chlar\documents\repositories\test\intellisched_capstone\algorithm\.venv\Lib\site-packages\uvicorn\lifespan\on.py", line 137, in receive
    return await self.receive_queue.get()
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Python313\Lib\asyncio\queues.py", line 186, in get
    await getter
asyncio.exceptions.CancelledError
ERROR WHEN STOPPING THE LOCAL SERVER