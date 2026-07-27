

#include "file_compression.h"
#include "bitmap_tool.h"
#include "error.h"
#include "file_tool.h"
#include "fastlz_util.h"
#include "debug.h"
#include "utils.h"

uint32_t make_compression_file(const char *fileName, const char *endName, uint8_t format) {
    LOG_ERROR("make compression file file name = %s,endName = %s,format = %d", fileName, endName, format);
    uint32_t fileLength;

    uint8_t *picBuff = (uint8_t *) malloc(1024 * 1024);
    if (picBuff == NULL) {
        return ERROR_NULL;
    }
    fileLength = bitmap_tool_get_font_buff(fileName, picBuff, sizeof(1024 * 1024), format);
    if (fileLength == 0) {
        free(picBuff);
        return ERROR_INVALID_DATA;
    }


    char file_patht_temp[500];
    snprintf(file_patht_temp, sizeof(file_patht_temp), "%s/%s.bin", getParentDirectory(fileName),
             getFileNameWithoutExtension(fileName));

    fileTool::wirteBufftoFile(file_patht_temp, picBuff, fileLength);
    LOG_ERROR("file_patht_temp:%s  fileLength = %d ", file_patht_temp, fileLength);
    free(picBuff);

    //压缩
    FILE *in = fopen(file_patht_temp, "rb");
    if (in == NULL) {
        LOG_INFO("err:open file %s not find", fileName);
        return ERROR_NOT_FIND;
    }

    char file_path[500];
    snprintf(file_path, sizeof(file_path), "%s.%s", fileName, endName);

    FILE *out = fopen(file_path, "wb+");
    if (out == NULL) {
        LOG_INFO("err:create file %s fail", fileName);
        fclose(in);
        return ERROR_FORBIDDEN;
    }

    fastlz_util_compress_file(in, out, 1024);
    fclose(in);
    fclose(out);
    return SUCCESS;
}


