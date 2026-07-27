cmake_minimum_required(VERSION 3.18)
project(IDOCompress)

set(CMAKE_CXX_STANDARD 17)
include_directories(
        protocol_c/logger
        protocol_c/help
        protocol_c/third_party_library/bitmap
        protocol_c/third_party_library/compression/fastlz
        protocol_c/third_party_library/compression/lz4
        protocol_c/third_party_library/png2bmp
        protocol_c/third_party_library/png2bmp/libpng
        protocol_c/third_party_library/pngQuant
        protocol_c/third_party_library/file_tool
        protocol_c/third_party_library/jsonCpp
        protocol_c/third_party_library/jsonCpp/json
        protocol_c/dial
        protocol_c/dial/make_file
        protocol_c/func_table
        ./
)


aux_source_directory(protocol_c/third_party_library/jsonCpp JSON_TOOLS_SRC)
aux_source_directory(protocol_c/third_party_library/jsonCpp/json JSON_SRC)

# dial
aux_source_directory(protocol_c/dial DIAL_TOOL_SRC)
aux_source_directory(protocol_c/dial/make_file DIAL_SRC)

add_executable(
        IDOCompress
        main_dial.cpp
        file_compression.cpp
        protocol_c/logger/debug.cpp
        protocol_c/third_party_library/bitmap/bitmap.c
        protocol_c/third_party_library/bitmap/bitmap_tool.c
        protocol_c/third_party_library/compression/fastlz/fastlz.c
        protocol_c/third_party_library/compression/fastlz/fastlz_util.c
        protocol_c/third_party_library/compression/lz4/lz4.c
        protocol_c/third_party_library/pngQuant/blur.c
        protocol_c/third_party_library/pngQuant/example.c
        protocol_c/third_party_library/pngQuant/kmeans.c
        protocol_c/third_party_library/pngQuant/libimagequant.c
        protocol_c/third_party_library/pngQuant/lodepng.c
        protocol_c/third_party_library/pngQuant/mediancut.c
        protocol_c/third_party_library/pngQuant/mempool.c
        protocol_c/third_party_library/pngQuant/nearest.c
        protocol_c/third_party_library/pngQuant/pam.c
        protocol_c/third_party_library/file_tool/file_tool.cpp
        protocol_c/func_table/protocol_func_table.c
        utils.cpp
        ${JSON_TOOLS_SRC}
        ${JSON_SRC}
        ${DIAL_TOOL_SRC}
        ${DIAL_SRC}
        app.rc
)