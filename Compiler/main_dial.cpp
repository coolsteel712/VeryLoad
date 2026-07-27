//
// Created by Davy on 2026/1/8.
//

#include "main_dial.h"
#include "make_file.h"
#include "utils.h"
#include "file_tool.h"
#include "debug.h"
#include "fastlz_util.h"
#include <regex>  //正则表达式
#include <stdlib.h>
#include <stdio.h>
#include <sys/stat.h>
#include <errno.h>

int main() {
    debug_log_init(true, false, "");
    char formatInput[32];
    // 获取格式参数，从设备获取，参考协议文档 15.7  获取屏幕信息协议返回的format、block_size
    uint8_t format;
    uint16_t block_size = 4096;
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
    std::string suffix = ".iwf";
    std::string sep = "/";
    std::string outDir = "a.output";
    while (true) {
        char dirPath[512];

        // 获取文件名（不能为空）
        fflush(stdout);
        while (1) {
            get_input_string("请将表盘包所在文件夹拖进来（不要放其他文件、文件夹）: ", dirPath, sizeof(dirPath));
            if (strlen(dirPath) == 0) {
                printf("错误：文件名不能为空！请重新输入。\n");
            } else {
                break;
            }
        }
        std::vector<std::string> fileList;
        fileTool::getAllFileAndDir(dirPath, fileList);
        if (fileList.empty()) {
            printf("无效目录");
            continue;
        }
        std::regex ZipFileSuffix("(.*)(.bmp|BMP|png|PNG|DS_Store|iwf|zip|output)"); //PNG和BMP后缀过滤

        std::string outputDir = dirPath + sep + outDir;

        ensure_directory_exists(outputDir.c_str());

        for (int i = 0; i < fileList.size(); i++) {
            std::string fileName = fileList.at(i);
            if (std::regex_match(fileName, ZipFileSuffix)) {
                continue;
            }

            std::string filePath = dirPath + sep + fileName + sep;
            std::string outputFile = outputDir + sep + fileName + suffix;
            printf("%s\n", fileName.c_str());
            int result = mkWatchDialFile(filePath.c_str(), outputFile.c_str(), 133);

            printf("\n*****%s*****\n\n", result > 0 ? "成功" : "失败");

            //compress to lz for transfer
            FILE *in = fopen(outputFile.c_str(), "rb");
            if (in == NULL) {
                LOG_INFO("err:open file %s not find", outputFile.c_str());
                return -1;
            }

            char file_path[500];
            snprintf(file_path, sizeof(file_path), "%s.%s", outputFile.c_str(), ".lz");

            FILE *out = fopen(file_path, "wb+");
            if (out == NULL) {
                LOG_INFO("err:create file %s fail", file_path);
                fclose(in);
                return -1;
            }

            fastlz_util_compress_file(in, out, block_size);
            fclose(in);
            fclose(out);
        }
    }

}

/**
 * @brief 制作(IWF)文件, 根据表盘包获取到IWF文件且返回生成的iwf文件大小
 * @param file_path 素材路径
 * @param save_file_name 文件名
 * @param format 取模图片的格式
 * @return int {1失败,IWF文件大小 成功}
*/
int mkWatchDialFile(const char *file_path, const char *save_file_name, int format) {
    return make_iwf_file(file_path, save_file_name, format);
}