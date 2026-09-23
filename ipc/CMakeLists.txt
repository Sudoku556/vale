add_executable(vale-ipc-test test_client.c)
target_link_libraries(vale-ipc-test PRIVATE vale_shared)
