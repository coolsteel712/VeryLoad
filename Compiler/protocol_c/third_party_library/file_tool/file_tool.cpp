#include <fstream>
#include <string.h>
#include <unistd.h>
#include <dirent.h>
#include "file_tool.h"
#include "debug.h"

using namespace std;

void fileTool::getAllFiles(string pathString, vector<string> &files) {
    DIR *dir;
    struct dirent *ptr;
    //char base[1000];

    if ((dir = opendir(pathString.c_str())) == NULL) {
        return;
    }

    while ((ptr = readdir(dir)) != NULL) {
        if (strcmp(ptr->d_name, ".") == 0 || strcmp(ptr->d_name, "..") == 0)    ///current dir OR parrent dir
            continue;
        else if (ptr->d_type == DT_REG)    ///file
            files.push_back(ptr->d_name);
        else if (ptr->d_type == DT_LNK)    ///link file

            continue;
        else if (ptr->d_type == DT_DIR)    ///dir
        {
            //files.push_back(ptr->d_name);
        }
    }
    closedir(dir);

}

void fileTool::getAllFileAndDir(string pathString, vector<string> &files) {
    DIR *dir;
    struct dirent *ptr;
    //char base[1000];

    if ((dir = opendir(pathString.c_str())) == NULL) {
        return;
    }

    while ((ptr = readdir(dir)) != NULL) {
        if (strcmp(ptr->d_name, ".") == 0 || strcmp(ptr->d_name, "..") == 0)    ///current dir OR parrent dir
            continue;
        else if (ptr->d_type == DT_REG)    ///file
            files.push_back(ptr->d_name);
        else if (ptr->d_type == DT_LNK)    ///link file

            continue;
        else if (ptr->d_type == DT_DIR)    ///dir
        {
            files.push_back(ptr->d_name);
        }
    }
    closedir(dir);

}

void fileTool::wirteBufftoFile(std::string fileName, uint8_t *buff, uint32_t buff_size) {
    if (buff == NULL || buff_size == 0) {
        return;
    }
    fstream outFile;
    outFile.open(fileName, ios::out | ios::trunc | ios::binary);
    outFile.write((const char *) buff, buff_size);
    outFile.close();
}

bool fileTool::separateFileName(const char *pcFile, char *pcFileName, char *pcFileExtension) {
    char *pcTemp = NULL;
    char cFile[200] = {'\0'};

    if ((NULL != pcFile) &&
        (NULL != pcFileName) &&
        (NULL != pcFileExtension)) {
        strcpy(cFile, pcFile);
        //查找文件名与扩展名分隔符'.'
        pcTemp = strrchr(cFile, '.');
        if (NULL == pcTemp) {
            return false;
        }
        //获取扩展名
        strcpy(pcFileExtension, pcTemp + 1);
        //获取文件名
        memset(pcTemp, 0, strlen(pcTemp));
        strcpy(pcFileName, cFile);

        return true;
    }

    return false;
}
