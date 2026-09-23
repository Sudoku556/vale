find_package(PkgConfig REQUIRED)
pkg_check_modules(XCB REQUIRED xcb xcb-util xcb-keysyms xcb-icccm xcb-ewmh)
pkg_check_modules(CAIRO REQUIRED cairo cairo-xcb)

add_executable(vwin src/main.c)
target_link_libraries(vwin PRIVATE ${XCB_LIBRARIES} ${CAIRO_LIBRARIES} vale_shared)
target_include_directories(vwin PRIVATE ${XCB_INCLUDE_DIRS} ${CAIRO_INCLUDE_DIRS})
