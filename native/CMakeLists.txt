cmake_minimum_required(VERSION 3.20)
project(aprp_native LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(aprp_native SHARED src/aprp_native.cpp)
target_include_directories(aprp_native PUBLIC include)
target_compile_definitions(aprp_native PRIVATE APRP_NATIVE_EXPORTS UNICODE _UNICODE WIN32_LEAN_AND_MEAN NOMINMAX)
target_link_libraries(aprp_native PRIVATE psapi)

if(MSVC)
  target_compile_options(aprp_native PRIVATE /W4 /permissive-)
  # Static CRT: the DLL then has no VC++ redistributable dependency.
  set_property(TARGET aprp_native PROPERTY MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
endif()

# Put the DLL where the C# project picks it up.
set_target_properties(aprp_native PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY_RELEASE ${CMAKE_SOURCE_DIR}/bin
  RUNTIME_OUTPUT_DIRECTORY_DEBUG   ${CMAKE_SOURCE_DIR}/bin)
