// Qi-specific C++17 referee, derived from AB-ARCH-003 minimal.cpp.
// Frozen experimental source remains unchanged; this is the maintained copy.
// The Python reference and frozen fixtures are the semantic authority.
#include <algorithm>
#include <array>
#include <cctype>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <string>
#include <type_traits>
#include <unordered_map>
#include <utility>
#include <vector>

namespace qi_native {
constexpr char START[] =
    "RNBAKABNR..........C.....C.P.P.P.P.P..................p.p.p.p.p.c.....c..........rnbakabnr";
using Board = std::array<char, 91>;
bool red(char p) { return p >= 'A' && p <= 'Z'; }
char kind(char p) { return static_cast<char>(std::toupper(static_cast<unsigned char>(p))); }
bool palace(int x, int y, bool side) {
    return x >= 3 && x <= 5 && (side ? y <= 2 && y >= 0 : y >= 7 && y <= 9);
}
bool reaches(const Board& b, int s, int t) {
    if (s == t || b[s] == '.' || (b[t] != '.' && red(b[s]) == red(b[t]))) return false;
    int x = s % 9, y = s / 9, tx = t % 9, ty = t / 9;
    int dx = tx - x, dy = ty - y, ax = std::abs(dx), ay = std::abs(dy);
    bool side = red(b[s]);
    char k = kind(b[s]);
    if (k == 'N') {
        if (!((ax == 1 && ay == 2) || (ax == 2 && ay == 1))) return false;
        return b[s + (ax == 2 ? dx / 2 : 9 * (dy / 2))] == '.';
    }
    if (k == 'B') return ax == 2 && ay == 2 && (side ? ty <= 4 : ty >= 5)
                         && b[s + dx / 2 + 9 * (dy / 2)] == '.';
    if (k == 'A') return ax == 1 && ay == 1 && palace(tx, ty, side);
    if (k == 'P') return (dx == 0 && dy == (side ? 1 : -1))
                       || ((side ? y >= 5 : y <= 4) && ax == 1 && dy == 0);
    if (k == 'K' && ax + ay == 1 && palace(tx, ty, side)) return true;
    if ((k != 'R' && k != 'C' && k != 'K') || (dx && dy)) return false;
    int step = dx ? (dx > 0 ? 1 : -1) : (dy > 0 ? 9 : -9), screens = 0;
    for (int i = s + step; i != t; i += step) screens += b[i] != '.';
    if (k == 'K') return dx == 0 && kind(b[t]) == 'K' && screens == 0;
    return screens == (k == 'C' && b[t] != '.' ? 1 : 0);
}
bool checked(const Board& b, bool side) {
    int king = -1;
    for (int i = 0; i < 90; ++i) if (b[i] == (side ? 'K' : 'k')) { king = i; break; }
    if (king < 0) return true;
    for (int s = 0; s < 90; ++s)
        if (b[s] != '.' && red(b[s]) != side && reaches(b, s, king)) return true;
    return false;
}
// Precompute geometry; dynamic blockers and king safety stay native.
struct Geometry {
    std::array<std::array<std::vector<int>, 90>, 128> targets;
    Geometry() {
        for (char p : std::string("RNBAKCP rnbakcp")) {
            if (p == ' ') continue;
            for (int s = 0; s < 90; ++s) {
                Board b; b.fill('.'); b[90] = 0; b[s] = p;
                for (int t = 0; t < 90; ++t)
                    if (reaches(b, s, t)) targets[static_cast<unsigned>(p)][s].push_back(t);
            }
        }
    }
};
const Geometry geometry;
std::vector<int> legal(Board& b, bool side) {
    std::vector<int> moves;
    moves.reserve(64);
    for (int s = 0; s < 90; ++s) {
        char p = b[s];
        if (p == '.' || red(p) != side) continue;
        for (int t : geometry.targets[static_cast<unsigned>(p)][s]) {
            char captured = b[t];
            if (kind(captured) == 'K' || !reaches(b, s, t)) continue;
            b[t] = p; b[s] = '.';
            bool safe = !checked(b, side);
            b[s] = p; b[t] = captured;
            if (safe) moves.push_back(s * 90 + t);
        }
    }
    return moves;
}
std::string move_text(int m) {
    int s = m / 90, t = m % 90;
    return {char('a' + s % 9), char('0' + s / 9), char('a' + t % 9), char('0' + t / 9)};
}
struct State {
    Board board{};
    bool side = true;
    int ply = 0;
    std::vector<int> history;
    std::unordered_map<std::string, int> repetitions;
    std::vector<int> cached;
    bool dirty = true;
    explicit State() { std::copy(START, START + 91, board.begin()); repetitions[key()] = 1; }
    static std::string key(const Board& position, bool red_to_move) {
        std::string value(position.data(), 91);
        value.back() = red_to_move ? 'r' : 'b';
        return value;
    }
    std::string key() const { return key(board, side); }
    const std::vector<int>& actions() {
        if (dirty) { cached = legal(board, side); dirty = false; }
        return cached;
    }
    int result() {
        if (actions().empty()) return checked(board, side) ? 1 : 2;
        if (repetitions.at(key()) >= 3) return 3;
        return ply >= 300 ? 4 : 0;
    }
    void advance(int m) {
        int s = m / 90, t = m % 90;
        Board next = board;
        next[t] = next[s]; next[s] = '.';
        auto next_key = key(next, !side);
        // Reserve geometrically, not once per move. Capacity changes are private;
        // a failed allocation must preserve the logical history and repetitions.
        if (history.size() == history.capacity())
            history.reserve(std::max(size_t{8}, history.size() * 2));
        // This is the last potentially throwing operation. try_emplace leaves the
        // map unchanged on allocation failure, including a failed rehash.
        auto entry = repetitions.try_emplace(std::move(next_key), 0).first;
        // No allocation below: int insertion fits reserved capacity, and board,
        // counters and flags are trivial values. Batch callers still stage copies.
        history.push_back(m);
        ++entry->second;
        board = next; side = !side; ++ply; dirty = true;
    }
    int validate(const std::string& move) {
        if (result()) return 1;
        if (move.size() != 4 || move[0] < 'a' || move[0] > 'i' || move[2] < 'a' || move[2] > 'i'
            || move[1] < '0' || move[1] > '9' || move[3] < '0' || move[3] > '9') return 2;
        int s = (move[1] - '0') * 9 + move[0] - 'a', t = (move[3] - '0') * 9 + move[2] - 'a';
        if (board[s] != '.' && red(board[s]) != side) return 3;
        int m = s * 90 + t;
        const auto& a = actions();
        if (!std::binary_search(a.begin(), a.end(), m)) return 4;
        return 0;
    }
};

int step(State& state, const std::string& move) {
    int error = state.validate(move);
    if (error) return error;
    int source = (move[1] - '0') * 9 + move[0] - 'a';
    int target = (move[3] - '0') * 9 + move[2] - 'a';
    state.advance(source * 90 + target);
    return 0;
}
} // namespace qi_native
