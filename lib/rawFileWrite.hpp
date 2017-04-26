#ifndef RAW_FILE_WRITE_H
#define RAW_FILE_WRITE_H

#include "buffers.h"
#include "KotekanProcess.hpp"
#include <string>

class rawFileWrite : public KotekanProcess {
public:
    rawFileWrite(Config &config,
                const string& unique_name,
                 struct Buffer &buf,
                 const std::string &base_dir,
                 const std::string &file_name,
                 const std::string &file_ext);
    virtual ~rawFileWrite();
    void apply_config(uint64_t fpga_seq) override;
    void main_thread();
private:
    struct Buffer &buf;
    std::string base_dir;
    std::string file_name;
    std::string file_ext;
};

#endif
