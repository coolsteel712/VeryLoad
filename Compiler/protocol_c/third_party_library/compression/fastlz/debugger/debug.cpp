//
// Created by Administrator on 2018/3/15.
//

#include "debug.h"
#include <stdarg.h>
#include <time.h>
#include <stdio.h>
#include <string.h>
#include <dirent.h>
#include <sys/types.h>
#include <sys/time.h>


static bool m_is_write_file = false;
static bool m_is_print_consloe = true;
static bool m_debug_log_init = false;

int cur_debug_level = DEBUG_LEVEL_WARN; //0:debug 1:debug 2:release , 默认level=1
static int log_save_day = 2;//日志保存天数 默认两天

//打印
void printf_log_consloe(char *log) {
    printf("%s\n", log);
}

void debug_log_get_time(struct tm *get_time) {
    time_t now_time;
    time(&now_time);
    struct tm *now = localtime(&now_time);

    memcpy(get_time, now, sizeof(struct tm));
    get_time->tm_year += 1900;
    get_time->tm_mon += 1;
}

static long debug_log_get_mil(void) {
    struct timeval val = {0};
    gettimeofday(&val, NULL);
    return (val.tv_usec / 1000);
}

static char log_buff[4096];

void debug_log(DEBUG_LEVEL level, const char *tag, const char *func_name, int line, const char *fmt, ...) {
    bool write_close = false;
    if (m_debug_log_init == false) {
        return;
    }

    //如果输出的等级小于日志等级, 则不输出 2023-3-20
    if (cur_debug_level > level) {
        write_close = true;
    }

    struct tm now_time;
    debug_log_get_time(&now_time);

//    static char log_buff[1024];
    memset(log_buff, 0, sizeof(log_buff));
    //处理tag
    if (tag != NULL) {
        const char *get_last_p;
        get_last_p = strrchr(tag, '/');
        if (get_last_p != NULL) {
            get_last_p += 1;
        }
        snprintf(log_buff, sizeof(log_buff), "[%02d-%02d %d:%02d:%02d.%03ld] [%s] [%s] [line %d] ", now_time.tm_mon,
                 now_time.tm_mday, now_time.tm_hour, now_time.tm_min, now_time.tm_sec, debug_log_get_mil(), get_last_p,
                 func_name, line);
    } else {
        snprintf(log_buff, sizeof(log_buff), "[%02d-%02d %d:%02d:%02d.%03ld] [%s] [line %d]", now_time.tm_mon,
                 now_time.tm_mday, now_time.tm_hour, now_time.tm_min, now_time.tm_sec, debug_log_get_mil(), func_name,
                 line);
    }


    va_list arg;
    va_start(arg, fmt);

    vsnprintf(log_buff + strlen(log_buff), sizeof(log_buff) - 1 - strlen(log_buff), fmt, arg);

    if (m_is_print_consloe == true) {
        printf_log_consloe(log_buff);
    }

    if (m_is_write_file == true && !write_close) {
    }

    va_end(arg);
}


void debug_log_get_old_one_day_time(struct tm *get_time) {
    time_t now_time;
    time(&now_time);
    now_time -= 24 * 60 * 60;
    struct tm *now = localtime(&now_time);

    memcpy(get_time, now, sizeof(struct tm));
    get_time->tm_year += 1900;
    get_time->tm_mon += 1;
}

static bool get_file_time_2_delete(time_t start_time, char *name) {
    char date[20] = {0};
    int year, month, day = 0;
    if (name == NULL) {
        return true;
    }
    char *suffix = strrchr(name, '.');
    if (!suffix) {
        return true;
    }

    memcpy(date, name, strlen(name) - strlen(suffix));
    DEBUG_INFO("file date:%s", date);

    int result = sscanf(date, "%d-%d-%d", &year, &month, &day);
    if (result < 3) {
        return true;
    }


    struct tm timetmp = {0};
    debug_log_get_time(&timetmp);
    time_t end_time = mktime(&timetmp);

    timetmp.tm_year = year;
    timetmp.tm_mon = month;
    timetmp.tm_mday = day;
    timetmp.tm_hour = 0;
    timetmp.tm_min = 0;
    timetmp.tm_sec = 0;
    time_t cur_time = mktime(&timetmp);
//    LOG_ERROR("start time:%d,end time:%d,cur time:%d",start_time,end_time,cur_time);

    if (cur_time >= start_time && cur_time <= end_time) {
        return true;
    }

    return false;
}

static void clear_old_log(char *filepath, int save_day) {
    struct tm ntime;
    char ntime_str[20] = {0};
    char etime_str[20] = {0};
    char pathname[strlen(filepath) + 20];

    debug_log_get_time(&ntime);
    ntime.tm_hour = 0;
    ntime.tm_min = 0;
    ntime.tm_sec = 0;

    time_t today_time = mktime(&ntime);
    time_t save_end_time = today_time - ((save_day - 1) * 24 * 60 * 60);

    struct tm *etime = localtime(&save_end_time);

    snprintf(ntime_str, sizeof(ntime_str), "%d-%02d-%02d", ntime.tm_year, ntime.tm_mon, ntime.tm_mday);
    snprintf(etime_str, sizeof(etime_str), "%d-%02d-%02d", etime->tm_year, etime->tm_mon, etime->tm_mday);

//    LOG_ERROR("ntime_str:%s timestamp:%d,etime_str:%s timestamp:%d",ntime_str,today_time,etime_str,save_end_time);

    DIR *dir = opendir(filepath);//打开目录文件
    if (dir == NULL) {
        LOG_INFO("err:opendir error");
        return;
    }
    struct dirent *entry;
    while ((entry = readdir(dir)) != 0) {
        if ((strncmp(entry->d_name, ".", 1) == 0) || (strncmp(entry->d_name, "..", 2) == 0) ||
            get_file_time_2_delete(save_end_time, entry->d_name)) {
            DEBUG_INFO("save %s", entry->d_name);
        } else {
            memset(pathname, 0, sizeof(pathname));
            snprintf(pathname, sizeof(pathname), "%s%s", filepath, entry->d_name);
            int ret = remove(pathname);
            if (ret != 0) {
                LOG_INFO("删除%s失败", entry->d_name);
                return;
            } else
                LOG_INFO("删除%s成功", entry->d_name);
        }
    }

    return;
}

void debug_log_init(bool is_print_console, bool is_write_file, const char *file_path) {
    struct tm now_time;
//    struct tm old_time;
    debug_log_get_time(&now_time);
    char buff[100] = {0};

    snprintf(buff, sizeof(buff), "%d-%02d-%02d", now_time.tm_year, now_time.tm_mon, now_time.tm_mday);

    //初始化，失败就不保存
    int ret = 0;
    if (is_write_file == true) {
    }
    if (ret == 0)//false 初始化失败，那么就停止保存打印
    {
        m_is_write_file = false;
        m_is_print_consloe = is_print_console;
    } else {
        m_is_write_file = is_write_file;
        m_is_print_consloe = is_print_console;
    }


    char version_release_string[10] = {0};


    m_debug_log_init = true;

    //2023-3-10 只保存两天的log
    char path[500] = {0};
    memcpy(path, file_path, strlen(file_path));
    clear_old_log(path, log_save_day);
}

void set_log_save_day(int save_day) {
    log_save_day = save_day < 2 ? 2 : save_day;
}
