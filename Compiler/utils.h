//
// Created by Davy on 2025/12/4.
//

#ifndef MSG_TOOLS_UTILS_H
#define MSG_TOOLS_UTILS_H

#include <iostream>
#include "file_compression.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <ctype.h>

// 获取父目录路径
extern char *getParentDirectory(const char *filePath);

// 获取文件名（带扩展名）
extern char *getFileName(const char *filePath);

// 获取文件名（不带扩展名）
extern char *getFileNameWithoutExtension(const char *filePath);

// 函数：检查字符串是否为纯数字
extern int is_string_numeric(const char *str);

// 函数：获取用户输入的字符串（移除末尾换行符）
void get_input_string(const char *prompt, char *buffer, int buffer_size);
int ensure_directory_exists(const char *path);
#endif //MSG_TOOLS_UTILS_H
