// Standalone memory/UB check of the exact minimal core, outside Python.
#include "minimal.cpp"
#include <cassert>
int main() {
    assert(nb_perft(3) == 79666);
    void* s = nb_new();
    std::string initial = nb_board(s);
    assert(nb_apply(s, "bad") == 2);
    assert(nb_apply(s, "a9a8") == 3);
    assert(nb_apply(s, "a0a9") == 4);
    assert(initial == nb_board(s));
    for (int i = 0; i < 2; ++i) {
        for (const char* move : {"b0c2", "b9c7", "c2b0", "c7b9"}) assert(nb_apply(s, move) == 0);
    }
    assert(nb_result(s) == 3);
    assert(nb_apply(s, "bad") == 1);
    nb_free(s);
    uint32_t seeds[128];
    for (uint32_t i = 0; i < 128; ++i) seeds[i] = i + 1;
    char* rows = nb_rollouts(seeds, 128, 300);
    assert(rows != nullptr && rows[0] == '[');
    nb_release(rows);
    assert(nb_rollouts(seeds, 129, 300) == nullptr);
    assert(nb_rollouts(seeds, 1, 301) == nullptr);
    seeds[0] = 0;
    assert(nb_rollouts(seeds, 1, 1) == nullptr);
}
