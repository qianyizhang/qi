// Standalone checks of the maintained core, built with ASan and UBSan.
#include "src/qi_game_native/core.hpp"
#include <cassert>
#include <random>
using namespace qi_native;

int main() {
    State state;
    for (const auto& [move, code] : std::vector<std::pair<std::string, int>>{
             {"bad", 2}, {"a9a8", 3}, {"a0a9", 4}, {std::string("a0a1\0", 5), 2}}) {
        assert(step(state, move) == code);
        assert(state.history.empty() && state.key() == std::string(START) + "r");
    }
    for (int i = 0; i < 2; ++i) {
        for (int move : {1 * 90 + 20, 82 * 90 + 65, 20 * 90 + 1, 65 * 90 + 82}) {
            assert(step(state, move_text(move)) == 0);
        }
    }
    assert(state.result() == 3 && state.validate("bad") == 1);
    // Frozen referee-v1 terminal diagrams: ordinary losses precede both draws.
    for (bool checkmate : {false, true}) {
        State terminal;
        terminal.board.fill('.'); terminal.board[90] = 0;
        terminal.board[4] = 'K'; terminal.board[49] = 'P';
        terminal.board[75] = 'R'; terminal.board[77] = 'R'; terminal.board[85] = 'k';
        if (checkmate) terminal.board[76] = 'R';
        terminal.side = false; terminal.ply = 300;
        terminal.repetitions.clear(); terminal.repetitions[terminal.key()] = 3;
        assert(terminal.result() == (checkmate ? 1 : 2));
    }
    std::mt19937 random(17);
    for (int i = 0; i < 128; ++i) {
        State game;
        while (!game.result()) {
            int move = game.actions()[random() % game.actions().size()];
            assert(step(game, move_text(move)) == 0);
            assert(game.ply <= 300);
        }
    }
}
