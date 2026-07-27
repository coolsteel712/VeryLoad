/********************************************************************
* Name      :  fileCompression.h
* Describ   :  文件的压缩 mp3等
* Author    :  liux
* Date      :  2020/07/12
 * 备注     ：使用Cpp的文件
********************************************************************/

#ifndef __NAWUAMITUOFU_FILE_COMPRESSION_H__
#define __NAWUAMITUOFU_FILE_COMPRESSION_H__

#include "include_help.h"

#ifdef __cplusplus
extern "C" {
#endif

//制作照片
//fileName 文件名
//endName 保存文件名 后缀名
//format 格式
extern uint32_t make_compression_file(const char * fileName, const char*  endName, uint8_t format);

#ifdef __cplusplus
}
#endif


#endif //__NAWUAMITUOFU_FILE_COMPRESSION_H__
