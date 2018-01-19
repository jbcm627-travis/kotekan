

// Split frequencies into upper and lower halves
class freqSplit : public KotekanProcess {

public:
    freqSplit(Config &config,
              const string& unique_name,
              bufferContainer &buffer_container);

    // This might be something standard for all KotekanProcesses
    // Doesn't seem to be implemented
    void apply_config(uint64_t fpga_seq);

    void main_thread(); // This is where the main functionality lives

private:

    // Parameters saved from the config files
    size_t num_elements, num_eigenvectors, block_size;

    // I may have to modify this one depending on what buffers I use in my process
    // Vector of the buffers we are using and their current frame ids.
    std::vector<std::pair<Buffer*, unsigned int>> output_buffers;
    Buffer * output_buffer; // Pointer to a Buffer object

    // TODO: I don't hink I need this. Should try to comment out
    // The mapping from buffer element order to output file element ordering
//    std::vector<uint32_t> input_remap;

};
