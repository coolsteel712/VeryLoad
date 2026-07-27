#include <iostream>
#include "file_compression.h"
#include "utils.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <ctype.h>


int main() {
    char formatInput[32];
    uint8_t format;

    // 获取格式参数
    printf("请输入颜色格式（默认133）: ");

    if (fgets(formatInput, sizeof(formatInput), stdin) == NULL) {
        // 输入错误，使用默认值
        format = 133;
    } else {
        // 移除换行符
        size_t len = strlen(formatInput);
        if (len > 0 && formatInput[len - 1] == '\n') {
            formatInput[len - 1] = '\0';
        }

        // 检查用户是否直接按回车（使用默认值）
        if (strlen(formatInput) == 0) {
            format = 133;
            printf("使用默认颜色格式: %d\n", format);
        } else {
            // 检查输入是否为纯数字
            if (!is_string_numeric(formatInput)) {
                printf("警告：输入不是有效的整数数字，使用默认值133\n");
                format = 133;
            } else {
                int tempFormat = atoi(formatInput);

                // 检查是否在uint8_t范围内（0-255）
                if (tempFormat < 0 || tempFormat > 255) {
                    printf("警告：数字超出范围（0-255），使用默认值133\n");
                    format = 133;
                } else {
                    format = (uint8_t) tempFormat;
                }
            }
        }
    }

    while (true) {
        char fileName[512];
        // 获取文件名（不能为空）
        fflush(stdout);
        while (1) {
            get_input_string("请输入图片路径: ", fileName, sizeof(fileName));
            if (strlen(fileName) == 0) {
                printf("错误：文件名不能为空！请重新输入。\n");
            } else {
                break;
            }
        }


        // 固定endName为".msg"
        const char *endName = "msg";



        // 调用外部函数
        uint32_t result = make_compression_file(fileName, endName, format);

        if (result == 0) {
            printf("传输使用: %s.msg\n", fileName);
            printf("固件使用: %s\\%s.bin\n", getParentDirectory(fileName), getFileNameWithoutExtension(fileName));
        }
        printf("\n*****%s*****\n\n", result == 0 ? "成功" : "失败");
    }

    return 0;
}
