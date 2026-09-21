// AB-LEARN-008 diagnostic only. In-place stepping deliberately lacks the public
// allocation-failure atomicity guarantee and must never become a runtime path.
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include "core.hpp"

using Clock = std::chrono::steady_clock;
using qi_native::State;

int action(const std::string& m) {
    return ((m[1] - '0') * 9 + m[0] - 'a') * 90 + (m[3] - '0') * 9 + m[2] - 'a';
}

void mix(uint64_t& hash, const State& s, int result, bool checked) {
    for (int i = 0; i < 90; ++i) hash = (hash ^ static_cast<unsigned char>(s.board[i])) * 1099511628211ULL;
    hash = (hash ^ static_cast<unsigned>(result)) * 1099511628211ULL;
    hash = (hash ^ static_cast<unsigned>(s.ply)) * 1099511628211ULL;
    hash = (hash ^ static_cast<unsigned>(checked)) * 1099511628211ULL;
    for (int m : s.cached) hash = (hash ^ static_cast<unsigned>(m)) * 1099511628211ULL;
}

int main(int argc, char** argv) {
    if (argc != 4) return 2;
    std::ifstream input(argv[1]);
    if (!input) return 3;
    std::string mode(argv[2]), line;
    int repeats = std::stoi(argv[3]);
    if (repeats < 1 || (mode != "staged" && mode != "inplace" && mode != "profile")) return 4;
    std::vector<std::vector<std::string>> games;
    while (std::getline(input, line)) {
        std::istringstream words(line);
        std::vector<std::string> moves;
        std::string move;
        while (words >> move) moves.push_back(move);
        games.push_back(std::move(moves));
    }
    if (games.empty()) return 8;
    double validate = 0, copy = 0, advance = 0, commit = 0, observe = 0;
    size_t plies = 0;
    uint64_t hash = 1469598103934665603ULL;
    const auto start = Clock::now();
    for (int repeat = 0; repeat < repeats; ++repeat) for (const auto& moves : games) {
        State state;
        (void)state.result();
        for (const auto& move : moves) {
            if (mode == "profile") {
                auto t = Clock::now();
                if (state.validate(move)) return 5;
                auto next = Clock::now();
                validate += std::chrono::duration<double>(next - t).count(); t = next;
                State pending = state;
                next = Clock::now();
                copy += std::chrono::duration<double>(next - t).count(); t = next;
                pending.advance(action(move));
                next = Clock::now();
                advance += std::chrono::duration<double>(next - t).count(); t = next;
                state = std::move(pending);
                next = Clock::now();
                commit += std::chrono::duration<double>(next - t).count(); t = next;
                int result = state.result();
                bool checked = qi_native::checked(state.board, state.side);
                next = Clock::now();
                observe += std::chrono::duration<double>(next - t).count();
                mix(hash, state, result, checked);
            } else {
                if (mode == "staged") {
                    if (qi_native::step(state, move)) return 6;
                } else {
                    if (state.validate(move)) return 7;
                    state.advance(action(move));
                }
                int result = state.result();
                bool checked = qi_native::checked(state.board, state.side);
                mix(hash, state, result, checked);
            }
            ++plies;
        }
    }
    const double elapsed = std::chrono::duration<double>(Clock::now() - start).count();
    std::cout << std::setprecision(12)
              << "{\"mode\":\"" << mode << "\",\"repeats\":" << repeats
              << ",\"games\":" << games.size() << ",\"plies\":" << plies
              << ",\"state_digest\":\"" << std::hex << hash << std::dec
              << "\",\"seconds\":" << elapsed
              << ",\"validate_seconds\":" << validate << ",\"copy_seconds\":" << copy
              << ",\"advance_seconds\":" << advance << ",\"commit_seconds\":" << commit
              << ",\"observe_seconds\":" << observe << "}\n";
}
