// Standalone checks of the maintained core, built with ASan and UBSan.
#include "src/qi_game_native/core.hpp"
#include <cstdio>
#include <new>
#include <random>
using namespace qi_native;

// Exercise the real standard-container allocations, without production failpoints.
// Static geometry initializes while injection is disabled.
long remaining_allocations = -1;
void* operator new(std::size_t size) {
    if (remaining_allocations == 0) throw std::bad_alloc();
    if (remaining_allocations > 0) --remaining_allocations;
    if (void* value = std::malloc(size ? size : 1)) return value;
    throw std::bad_alloc();
}
void* operator new[](std::size_t size) { return ::operator new(size); }
void operator delete(void* value) noexcept { std::free(value); }
void operator delete[](void* value) noexcept { std::free(value); }
void operator delete(void* value, std::size_t) noexcept { std::free(value); }
void operator delete[](void* value, std::size_t) noexcept { std::free(value); }
#define CHECK(value) do { if (!(value)) { \
    std::fprintf(stderr, "Check failed at line %d: %s\n", __LINE__, #value); std::abort(); \
} } while (false)

void same_game(const State& left, const State& right) {
    CHECK(left.board == right.board && left.side == right.side && left.ply == right.ply);
    CHECK(left.history == right.history && left.repetitions == right.repetitions);
}

void allocation_failures(const State& initial, const std::string& move) {
    State expected = initial;
    CHECK(step(expected, move) == 0);
    int failures = 0;
    for (int index = 0; index < 128; ++index) {
        State state = initial;
        bool failed = false;
        remaining_allocations = index;
        try { CHECK(step(state, move) == 0); }
        catch (const std::bad_alloc&) { failed = true; }
        remaining_allocations = -1;
        if (!failed) {
            same_game(state, expected);
            CHECK(failures > 0);
            std::printf("allocation failures checked: %d at ply %d\n", failures, initial.ply);
            return;
        }
        ++failures;
        same_game(state, initial);
        // Private capacity/cache changes are permitted. A retry must be identical.
        CHECK(step(state, move) == 0);
        same_game(state, expected);
        CHECK(state.result() == expected.result() && state.actions() == expected.actions());
    }
    CHECK(false);
}

int main() {
    State fresh;
    allocation_failures(fresh, "b2e2");
    State repeated;
    for (const auto& move : {"b0c2", "b9c7", "c2b0"}) CHECK(step(repeated, move) == 0);
    allocation_failures(repeated, "c7b9");
    State growing;
    std::mt19937 choices(29);
    for (int i = 0; i < 32; ++i) {
        CHECK(!growing.result());
        auto move = move_text(growing.actions()[choices() % growing.actions().size()]);
        CHECK(step(growing, move) == 0);
    }
    // Force the next insertion to exercise rehash and history growth failures.
    growing.history.shrink_to_fit();
    growing.repetitions.rehash(0);
    growing.repetitions.max_load_factor(
        static_cast<float>(growing.repetitions.size()) / growing.repetitions.bucket_count());
    allocation_failures(growing, move_text(growing.actions().front()));
    State state;
    for (const auto& [move, code] : std::vector<std::pair<std::string, int>>{
             {"bad", 2}, {"a9a8", 3}, {"a0a9", 4}, {std::string("a0a1\0", 5), 2}}) {
        CHECK(step(state, move) == code);
        CHECK(state.history.empty() && state.key() == std::string(START) + "r");
    }
    for (int i = 0; i < 2; ++i) {
        for (int move : {1 * 90 + 20, 82 * 90 + 65, 20 * 90 + 1, 65 * 90 + 82}) {
            CHECK(step(state, move_text(move)) == 0);
        }
    }
    CHECK(state.result() == 3 && state.validate("bad") == 1);
    // Frozen referee-v1 terminal diagrams: ordinary losses precede both draws.
    for (bool checkmate : {false, true}) {
        State terminal;
        terminal.board.fill('.'); terminal.board[90] = 0;
        terminal.board[4] = 'K'; terminal.board[49] = 'P';
        terminal.board[75] = 'R'; terminal.board[77] = 'R'; terminal.board[85] = 'k';
        if (checkmate) terminal.board[76] = 'R';
        terminal.side = false; terminal.ply = 300;
        terminal.repetitions.clear(); terminal.repetitions[terminal.key()] = 3;
        CHECK(terminal.result() == (checkmate ? 1 : 2));
    }
    std::mt19937 random(17);
    for (int i = 0; i < 128; ++i) {
        State game;
        while (!game.result()) {
            int move = game.actions()[random() % game.actions().size()];
            CHECK(step(game, move_text(move)) == 0);
            CHECK(game.ply <= 300);
        }
    }
}
