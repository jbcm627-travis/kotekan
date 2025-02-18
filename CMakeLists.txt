# Set the version of CMake required for *all* CMake files in the project. 3.8.2 to match C++17.
cmake_minimum_required(VERSION 3.8.2)
project(
    KOTEKAN
    DESCRIPTION "A high performance radio data processing pipeline"
    LANGUAGES C CXX)
set(CMAKE_MODULE_PATH ${KOTEKAN_SOURCE_DIR}/cmake)

# Require at least c++17 support from the compiler
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
# this makes sure we use -std=c++17, not -std=gnu++17
set(CMAKE_CXX_EXTENSIONS OFF)

# set C standard to gnu99
set(CMAKE_C_STANDARD 99)

# This quiets a noisy cmake warning on newer versions, triggered by some of our CMake/FindXYZ.cmake
# scripts.
if(NOT ${CMAKE_VERSION} VERSION_LESS "3.12.0")
    cmake_policy(SET CMP0075 NEW)
endif()

# Fix a problem with homebrew linking on MacOS >= 10.14 See
# https://stackoverflow.com/questions/54068035
if(APPLE)
    link_directories(/usr/local/lib)
endif()

# optional modules for GPUs and the like
option(USE_AIRSPY "Build Airspy Producer" OFF)
option(USE_FFTW "Build with FFTW F-engine" OFF)
option(USE_LAPACK "Build with LAPACK Linear Algebra (OpenBLAS)" OFF)
option(USE_HSA "Build HSA GPU Framework" OFF)
option(USE_CLOC "Use the CL offline compiler" OFF)
option(USE_OPENCL "Build OpenCL GPU Framework" OFF)
option(USE_CUDA "Build CUDA GPU Framework" OFF)
option(USE_HIP "Build HIP GPU Framework" OFF)
option(USE_OLD_DPDK "Enable old versions of DPDK (<19.11)" OFF)
option(USE_HDF5 "Build HDF5 output stages" OFF)
option(USE_OMP "Enable OpenMP" OFF)
option(USE_OLD_ROCM "Build for ROCm versions 2.3 or older" OFF)
option(NO_MEMLOCK "Do not lock buffer memory (useful when running in Docker)" OFF)
option(SUPERDEBUG "Enable extra debugging with no optimisation" OFF)
option(SANITIZE "Enable clang sanitizers for testing" OFF)
option(COMPILE_DOCS "Use Sphinx to compile documentation" OFF)
option(WITH_TESTS "Compile testing library and boost C++ unit tests" OFF)
option(IWYU "Enable include-what-you-use and print suggestions to stderr" OFF)
option(CCACHE "Use ccache to speed up the build" OFF)
option(WERROR "Warnings are errors" OFF)

if(${CCACHE})
    find_program(CCACHE_PROGRAM ccache)
    if(CCACHE_PROGRAM)
        message("Using ccache from " ${CCACHE_PROGRAM})
        set(CMAKE_CXX_COMPILER_LAUNCHER "${CCACHE_PROGRAM}")
    else()
        message("Unable to find ccache")
    endif()
endif()

# Compiler warnings
if(${WERROR})
    message("Treating all warnings as errors")
    add_compile_options(-Werror)
endif()
# lots of warnings and all warnings as errors
add_compile_options(-Wall -Wextra)
add_compile_options($<$<COMPILE_LANGUAGE:CXX>:-Wzero-as-null-pointer-constant>)
# Warning about missing override is called differently in clang and gcc
include(CheckCXXCompilerFlag)
check_cxx_compiler_flag(-Winconsistent-missing-override HAVE_INCONSISTANT_MISSING_OVERRIDE)
if(HAVE_INCONSISTANT_MISSING_OVERRIDE AND NOT ${IWYU})
    add_compile_options($<$<COMPILE_LANGUAGE:CXX>:-Winconsistent-missing-override>)
endif()
check_cxx_compiler_flag(-Wsuggest-override HAVE_SUGGEST_OVERRIDE)
if(HAVE_SUGGEST_OVERRIDE AND NOT ${IWYU})
    add_compile_options($<$<COMPILE_LANGUAGE:CXX>:-Wsuggest-override>)
endif()

# optimization
set(CMAKE_C_FLAGS_DEBUG "${CMAKE_C_FLAGS_DEBUG} ${CMAKE_C_FLAGS} -ggdb -O2")
set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} ${CMAKE_CXX_FLAGS} -ggdb -O2")

# Improve debugging by turning off all optimisations.
if(${SUPERDEBUG})
    message("Superdebugging enabled!!")
    set(CMAKE_C_FLAGS_DEBUG "${CMAKE_C_FLAGS_DEBUG} -O0 -fno-omit-frame-pointer")
    set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} -O0 -fno-omit-frame-pointer")
endif()

# Turn on sanitizers for finding memory issues.
if(${SANITIZE})
    message("Sanitization enabled!!")
    set(CMAKE_C_FLAGS_DEBUG "${CMAKE_C_FLAGS_DEBUG} -O0 -fno-omit-frame-pointer")
    set(CMAKE_C_FLAGS_DEBUG "${CMAKE_C_FLAGS_DEBUG} -fno-optimize-sibling-calls -fsanitize=address")
    set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} -O0 -fno-omit-frame-pointer")
    set(CMAKE_CXX_FLAGS_DEBUG
        "${CMAKE_CXX_FLAGS_DEBUG} -fno-optimize-sibling-calls -fsanitize=address")
endif()

if(${USE_HSA})
    find_package(HSA REQUIRED)
    set(USE_HSA ${HSA_FOUND})
    find_library(hsa-runtime64 /opt/rocm/hsa/lib/)
    if(${USE_OLD_ROCM})
        add_definitions(-DUSE_OLD_ROCM)
    endif()
endif()

if(${USE_OPENCL})
    set(ENV{AMDAPPSDKROOT} /opt/rocm/opencl)
    find_package(OPENCL REQUIRED)
    set(USE_OPENCL ${OPENCL_FOUND})
endif()

if(${USE_HIP})
    find_package(HIP)
    set(USE_HIP ${HIP_FOUND})
endif()

if(${USE_CUDA})
    set(CUDA_TOOLKIT_ROOT_DIR /usr/local/cuda)
    set(CMAKE_CUDA_COMPILER /usr/local/cuda/bin/nvcc)
    find_package(CUDA REQUIRED)
    set(USE_CUDA ${CUDA_FOUND})
    enable_language(CUDA)
endif()

if(${USE_AIRSPY})
    find_package(LIBAIRSPY)
    set(USE_AIRSPY ${LIBAIRSPY_FOUND})
endif()

if(${USE_FFTW})
    find_package(FFTW)
    set(USE_FFTW ${FFTW_FOUND})
    add_definitions(-DWITH_FFTW)
endif()

if(NOT DEFINED ARCH)
    set(ARCH "native")
endif()

include(CheckIncludeFileCXX)
if(${USE_LAPACK})

    set(BLA_VENDOR OpenBLAS)
    find_package(BLAS REQUIRED)
    find_path(
        BLAS_INCLUDE_DIRS cblas.h
        PATHS /usr/include /usr/local/include
        PATH_SUFFIXES openblas)
    message("Using BLAS ${BLAS_LIBRARIES}")
    message("Using BLAS includes ${BLAS_INCLUDE_DIRS}")
    find_package(LAPACK REQUIRED)
    message("Using LAPACK ${LAPACK_LIBRARIES}")
    find_package(LAPACKE REQUIRED)
    message("Using LAPACKE ${LAPACKE_LIBRARIES}")

    # Check Blaze is installed
    if(DEFINED BLAZE_PATH)
        if(NOT EXISTS ${BLAZE_PATH}/blaze/Blaze.h)
            message(FATAL_ERROR "Could not find Blaze headers")
        endif()
    endif()
    add_definitions(-DBLAZE_BLAS_MODE=1)
    add_definitions(-DBLAZE_BLAS_IS_PARALLEL=1)
endif()

if(${CMAKE_SYSTEM_NAME} MATCHES "Darwin")
    # enable all MacOS specific code
    add_definitions(-DMAC_OSX)
endif()

# Create custom build type for testing: no debug info, but asserts
string(REGEX REPLACE "( -DNDEBUG$|-DNDEBUG )" "" CMAKE_CXX_FLAGS_TEST "${CMAKE_CXX_FLAGS_RELEASE}")
string(REGEX REPLACE "( -DNDEBUG$|-DNDEBUG )" "" CMAKE_C_FLAGS_TEST "${CMAKE_C_FLAGS_RELEASE}")

# Set a default build type if none was specified
set(DEFAULT_BUILD_TYPE "Debug")
# Set the possible values of build type for cmake-gui
set_property(CACHE CMAKE_BUILD_TYPE PROPERTY STRINGS "Debug" "Release" "Test")
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    message(STATUS "Setting build type to '${DEFAULT_BUILD_TYPE}' as none was specified.")
    set(CMAKE_BUILD_TYPE "${DEFAULT_BUILD_TYPE}")
endif()

# Enable debug logging for Debug and Test builds
if(CMAKE_BUILD_TYPE MATCHES Debug OR CMAKE_BUILD_TYPE MATCHES Test)
    add_definitions(-DDEBUGGING)
    message("DEBUG logging enabled")
    message("Asserts enabled")
endif()

# include-what-you-use: this has to be set before any targets are added
if(IWYU)
    find_program(IWYU_PATH NAMES include-what-you-use iwyu)
    if(NOT IWYU_PATH)
        message(FATAL_ERROR "Could not find the program include-what-you-use")
    endif()
    if(NOT IWYU_MAPPING_FILE)
        set(IWYU_MAPPING_FILE "${KOTEKAN_SOURCE_DIR}/iwyu.kotekan.imp")
    endif()
    message("IWYU enabled: Using iwyu from ${IWYU_PATH} and mapping file ${IWYU_MAPPING_FILE}")
    execute_process(
        COMMAND ${IWYU_PATH} "--version"
        OUTPUT_VARIABLE IWYU_VERSION
        OUTPUT_STRIP_TRAILING_WHITESPACE)
    message("IWYU version: ${IWYU_VERSION}")
    set(IWYU_PATH_AND_OPTIONS
        ${IWYU_PATH}
        -Xiwyu
        --max_line_length=100
        -Xiwyu
        --mapping_file=${IWYU_MAPPING_FILE}
        -Xiwyu
        --no_fwd_decls)
    set(CMAKE_CXX_INCLUDE_WHAT_YOU_USE ${IWYU_PATH_AND_OPTIONS})
    set(CMAKE_C_INCLUDE_WHAT_YOU_USE ${IWYU_PATH_AND_OPTIONS})
endif()

set(GPU_MODULES "")
if(${USE_HIP})
    add_definitions(-DWITH_HIP)
    set(GPU_MODULES ${GPU_MODULES} "HIP ")
endif()
if(${USE_HSA})
    add_definitions(-DWITH_HSA)
    set(GPU_MODULES ${GPU_MODULES} "HSA ")
endif()
if(${USE_OPENCL})
    set(GPU_MODULES ${GPU_MODULES} "OpenCL ")
endif()
if(${USE_CUDA})
    add_definitions(-DWITH_CUDA)
    set(GPU_MODULES ${GPU_MODULES} "CUDA ")
endif()
message("GPU Modules Included: " ${GPU_MODULES})

set(INPUT_MODULES "")
if(${USE_AIRSPY})
    add_definitions(-DWITH_AIRSPY)
    set(INPUT_MODULES ${INPUT_MODULES} "AIRSPY ")
endif()
message("Input Modules Included: " ${INPUT_MODULES})

if(${USE_HDF5})
    # only clone highfive if HIGHFIVE_PATH is not specified nor cached
    if(NOT DEFINED HIGHFIVE_PATH)
        message("HIGHFIVE_PATH not specified: Cloning HighFive repository")
        include(ExternalProject)
        find_package(Git REQUIRED)
        ExternalProject_Add(
            highfive
            PREFIX ${CMAKE_BINARY_DIR}/ext
            GIT_REPOSITORY https://github.com/jrs65/HighFive.git
            GIT_TAG extensible-datasets
            TIMEOUT 10
            UPDATE_COMMAND ${GIT_EXECUTABLE} pull
            CONFIGURE_COMMAND ""
            BUILD_COMMAND ""
            INSTALL_COMMAND ""
            LOG_DOWNLOAD ON)
        ExternalProject_Get_Property(highfive source_dir)
        set(HIGHFIVE_PATH ${source_dir})
    else()
        # just to satisfy dependencies (dependencies on highfive are needed to make sure it is
        # cloned before attempting to build kotekan)
        add_custom_target(highfive COMMENT "Highfive path supplied manually.")
    endif()
    message("HDF5 enabled; using HighFive from: " ${HIGHFIVE_PATH})
    find_package(HDF5 REQUIRED)
    add_definitions(-DWITH_HDF5)
endif()

find_package(Threads REQUIRED)

add_compile_options(-D_GNU_SOURCE -march=${ARCH} -mtune=${ARCH} -I/opt/rocm/include)

# OpenMP flag
if(${USE_OMP})
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fopenmp")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fopenmp")
endif()

set(CMAKE_INSTALL_PREFIX "/")

if(${CMAKE_SYSTEM_NAME} MATCHES "Darwin")
    # On MacOS turn off ASLR for better debugging/profiling
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -lm -Wl,-no_pie")
else()
    set(CMAKE_EXE_LINKER_FLAGS
        "${CMAKE_EXE_LINKER_FLAGS} -static-libgcc -static-libstdc++ -L/opt/rocm/lib -lm")
endif()

# Disable complex math NaN/INFO range checking for performance
check_cxx_compiler_flag(-fcx-limited-range HAVE_CX_LIMITED_RANGE)
if(HAVE_CX_LIMITED_RANGE AND NOT ${IWYU})
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fcx-limited-range")
endif()

include(CheckCCompilerFlag)
check_c_compiler_flag(-fcx-limited-range HAVE_C_LIMITED_RANGE)
if(HAVE_C_LIMITED_RANGE AND NOT ${IWYU})
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fcx-limited-range")
endif()

if(${USE_OPENCL})
    install(DIRECTORY lib/opencl/kernels DESTINATION /var/lib/kotekan/opencl)
endif()
set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -lm")

if(${COMPILE_DOCS})
    add_subdirectory(docs EXCLUDE_FROM_ALL)
endif()

# Prevent memory locking and setting any memory policies. This is useful when running in restricted
# environments, e.g. Docker containers.  Note this can also be done with the configuration file for
# systems which do support memory locking, but where some memory shouldn't be memory locked.
if(${NO_MEMLOCK})
    message("Do not lock buffer memory.")
    add_definitions(-DWITH_NO_MEMLOCK)
endif()

add_subdirectory(lib)
add_subdirectory(kotekan)
add_subdirectory(scripts)
add_subdirectory(external)
add_subdirectory(config)

# Testing with boost
if(${WITH_TESTS})
    set(_BOOST_TESTS_DIR
        tests/boost/
        CACHE INTERNAL "Path to boost test sources")
    message("BOOST_TESTS enabled: building tests in " ${_BOOST_TESTS_DIR})
    add_subdirectory(${_BOOST_TESTS_DIR})
else()
    message("BOOST_TESTS disabled")
endif()

# Enforce code formatting rules with clang-format.
find_program(
    CLANG_FORMAT_PATH
    NAMES "clang-format-8" "clang-format"
    DOC "Path to clang-format executable")
if(NOT CLANG_FORMAT_PATH)
    message(STATUS "clang-format not found.")
else()
    message(STATUS "clang-format found: ${CLANG_FORMAT_PATH}")
    set(DO_CLANG_FORMAT "${CLANG_FORMAT_PATH}" "-i -style=file")
endif()

# Remove files containing substring from a list of file names.
function(exclude_files_containing var exclude_string)
    set(listVar "")
    foreach(file ${ARGN})
        string(FIND ${file} ${exclude_string} EXCLUDE_STRING_FOUND)
        if(${EXCLUDE_STRING_FOUND} EQUAL -1)
            list(APPEND listVar ${file})
        endif()
    endforeach()
    set(${var}
        "${listVar}"
        PARENT_SCOPE)
endfunction()

if(CLANG_FORMAT_PATH)
    # Find all .c(pp) and .h(pp) files.
    file(GLOB_RECURSE KOTEKAN_ALL_CPP_FILES *.cpp)
    file(GLOB_RECURSE KOTEKAN_ALL_HPP_FILES *.hpp)
    file(GLOB_RECURSE KOTEKAN_ALL_C_FILES *.c)
    file(GLOB_RECURSE KOTEKAN_ALL_H_FILES *.h)

    list(APPEND FILES_TO_FORMAT ${KOTEKAN_ALL_CPP_FILES})
    list(APPEND FILES_TO_FORMAT ${KOTEKAN_ALL_HPP_FILES})
    list(APPEND FILES_TO_FORMAT ${KOTEKAN_ALL_C_FILES})
    list(APPEND FILES_TO_FORMAT ${KOTEKAN_ALL_H_FILES})

    # Exclude all code we don't want auto-formatted (external libs).
    set(EXCLUDE_DIR "external")
    exclude_files_containing(FILES_TO_FORMAT ${EXCLUDE_DIR} ${FILES_TO_FORMAT})
    set(EXCLUDE_DIR "build")
    exclude_files_containing(FILES_TO_FORMAT ${EXCLUDE_DIR} ${FILES_TO_FORMAT})

    # Use .clang-format file to auto format.
    add_custom_target(
        clang-format
        COMMAND ${CLANG_FORMAT_PATH} -style=file -i ${FILES_TO_FORMAT}
        COMMENT "Running clang-format")
endif()
