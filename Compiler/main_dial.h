//
// Created by Davy on 2026/1/8.
//

#ifndef MSG_TOOLS_MAIN_DIAL_H
#define MSG_TOOLS_MAIN_DIAL_H

/**
 * @brief 制作(IWF)文件, 根据表盘包获取到IWF文件且返回生成的iwf文件大小
 * @param file_path 素材路径
 * @param save_file_name 文件名
 * @param format 取模图片的格式
 * @return int {1失败,IWF文件大小 成功}
*/
extern int mkWatchDialFile(const char *file_path, const char *save_file_name, int format);

#endif //MSG_TOOLS_MAIN_DIAL_H
