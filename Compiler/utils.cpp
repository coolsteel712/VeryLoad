//
// Created by Davy on 2025/12/4.
//

#include "utils.h"

#include <stdio.h>
#include <string.h>

#ifdef _WIN32
#include <windows.h>
#include <direct.h>
#define MKDIR(dir) _mkdir(dir)
#else

#include <sys/stat.h>
#include <sys/types.h>
#include <errno.h>

#define MKDIR(dir) mkdir(dir, 0755)
#endif

// 函数：检查字符串是否为纯数字
int is_string_numeric(const char *str) {
    if (str == NULL || *str == '\0') {
        return 0;
    }

    for (int i = 0; str[i] != '\0'; i++) {
        if (!isdigit((unsigned char) str[i])) {
            return 0;
        }
    }
    return 1;
}


// 函数：获取用户输入的字符串（移除末尾换行符）
void get_input_string(const char *prompt, char *buffer, int buffer_size) {
    printf("%s", prompt);
    fflush(stdout);

    if (fgets(buffer, buffer_size, stdin) == NULL) {
        buffer[0] = '\0';
        return;
    }

    // 移除换行符
    size_t len = strlen(buffer);
    if (len > 0 && buffer[len - 1] == '\n') {
        buffer[len - 1] = '\0';
    }
}

// 获取父目录路径
char *getParentDirectory(const char *filePath) {
    if (filePath == NULL) return NULL;

    // 找到最后一个路径分隔符
    const char *lastSlash = strrchr(filePath, '/');
    const char *lastBackslash = strrchr(filePath, '\\');
    const char *lastSeparator;

    if (lastSlash == NULL && lastBackslash == NULL) {
        // 没有父目录
        char *currentDir = static_cast<char *>(malloc(2));
        if (currentDir) {
            currentDir[0] = '.';
            currentDir[1] = '\0';
        }
        return currentDir;
    }

    // 取更靠后的分隔符
    if (lastSlash == NULL) {
        lastSeparator = lastBackslash;
    } else if (lastBackslash == NULL) {
        lastSeparator = lastSlash;
    } else {
        lastSeparator = (lastSlash > lastBackslash) ? lastSlash : lastBackslash;
    }

    // 计算父目录长度
    size_t parentLen = lastSeparator - filePath;
    if (parentLen == 0) {
        parentLen = 1;  // 根目录的情况
    }

    // 分配内存并复制
    char *parentDir = (char *) malloc(parentLen + 1);
    if (parentDir == NULL) return NULL;

    strncpy(parentDir, filePath, parentLen);
    parentDir[parentLen] = '\0';

    return parentDir;
}

// 获取文件名（带扩展名）
char *getFileName(const char *filePath) {
    if (filePath == NULL) return NULL;

    const char *p = filePath + strlen(filePath) - 1;
    const char *start = filePath;

    // 反向查找路径分隔符
    while (p >= filePath) {
        if (*p == '/' || *p == '\\') {
            start = p + 1;
            break;
        }
        p--;
    }

    return strdup(start);  // strdup会分配内存
}

// 获取文件名（不带扩展名）
char *getFileNameWithoutExtension(const char *filePath) {
    if (filePath == NULL) return NULL;

    // 先获取完整文件名
    char *fullName = getFileName(filePath);
    if (fullName == NULL) return NULL;

    // 查找最后一个点号
    char *lastDot = strrchr(fullName, '.');
    if (lastDot != NULL && lastDot != fullName) {  // 避免处理以点开头的文件
        *lastDot = '\0';  // 截断字符串，去掉扩展名
    }
    // 注意：这里修改了fullName，但不需要重新分配内存

    return fullName;  // 返回已经修改的fullName
}


// 跨平台目录创建函数
int create_directory_recursive(const char *path) {
    char temp_path[1024];
    char *p = NULL;
    size_t len;

    // 复制路径
    snprintf(temp_path, sizeof(temp_path), "%s", path);
    len = strlen(temp_path);

    // 移除末尾的斜杠（如果有）
    if (temp_path[len - 1] == '/' || temp_path[len - 1] == '\\') {
        temp_path[len - 1] = '\0';
    }

    // 逐级创建目录
    for (p = temp_path + 1; *p; p++) {
        if (*p == '/' || *p == '\\') {
            *p = '\0';  // 临时截断路径

            // 尝试创建目录
            if (MKDIR(temp_path) != 0) {
#ifdef _WIN32
                if (GetLastError() != ERROR_ALREADY_EXISTS) {
#else
                if (errno != EEXIST) {
#endif
                    return -1;  // 创建失败
                }
            }

            *p = '/';  // 恢复路径（统一使用正斜杠）
        }
    }

    // 创建最终目录
    if (MKDIR(temp_path) != 0) {
#ifdef _WIN32
        if (GetLastError() != ERROR_ALREADY_EXISTS) {
#else
        if (errno != EEXIST) {
#endif
            return -1;
        }
    }

    return 0;
}

// 检查目录是否存在
int directory_exists(const char *path) {
#ifdef _WIN32
    DWORD dwAttrib = GetFileAttributes(path);
    return (dwAttrib != INVALID_FILE_ATTRIBUTES &&
            (dwAttrib & FILE_ATTRIBUTE_DIRECTORY));
#else
    struct stat st;
    return (stat(path, &st) == 0 && S_ISDIR(st.st_mode));
#endif
}

// 主函数：检查并创建目录
int ensure_directory_exists(const char *path) {
    if (directory_exists(path)) {
        printf("目录已存在: %s\n", path);
        return 0;
    }

    printf("正在创建目录: %s\n", path);
    if (create_directory_recursive(path) == 0) {
        printf("目录创建成功\n");
        return 1;
    } else {
        printf("目录创建失败\n");
        return -1;
    }
}