cmake_minimum_required(VERSION 3.16)
project(vale_de C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_subdirectory(shared)
add_subdirectory(wm)
add_subdirectory(ipc)
