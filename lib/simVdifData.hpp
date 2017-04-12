#ifndef SIM_VDIF_DATA_H
#define SIM_VDIF_DATA_H

#include "buffers.h"
#include "KotekanProcess.hpp"
#include "vdif_functions.h"

class simVdifData : public KotekanProcess {
public:
    simVdifData(Config &config,
                 struct Buffer &buf);
    ~simVdifData();
    void apply_config(uint64_t fpga_seq) override;
    void main_thread();
private:
    struct Buffer &buf;
    double time_available;
    double start_time, stop_time;

};

#endif