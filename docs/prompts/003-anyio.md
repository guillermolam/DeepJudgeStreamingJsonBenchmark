Based on src/serializers/solid implementations refactor the ones in src/serializers/anyio
following these premises:

1. All these parsers must pass all tests in tests/test_parsers.py
2. That means init, get and consume have to maintain the same api contract
3. Refactor in smaller classes and/or methods to keep the cognitive complexity under 14
4. Use SOLID Principles, clean code and Reactive Programming principles.
5. Use any additional library to make it work or improve performance and non-functional aspects, such as:
    trio, trio-parallel, asyncio, tractor, multithreading, triotp, time,  etc.
6. get might for simplicity be considered a blocking call
7. Use async / non-blockigh on any given subtask/method call, constructor and make sure all implementations can recover from blocking calls or back-pressure issues
8. Maximize Concurrency as much as possible to try to reach one process per async thread if 
9. 
10. Task is considered done when all tests in tests/test_parsers.py pass and tests/test_reactive_parsers.py (Optional if
    you created it) pass