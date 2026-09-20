// Qi-specific experimental C++17 referee. No application, search or model code.
// The Python reference and frozen fixtures are the semantic authority.
#include <algorithm>
#include <array>
#include <cctype>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <string>
#include <unordered_map>
#include <vector>

namespace {
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
    std::string key() const { return std::string(board.data(), 90) + (side ? 'r' : 'b'); }
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
        board[t] = board[s]; board[s] = '.';
        side = !side; ++ply; history.push_back(m); ++repetitions[key()]; dirty = true;
    }
    int apply(const char* move) {
        if (result()) return 1;
        if (std::strlen(move) != 4 || move[0] < 'a' || move[0] > 'i' || move[2] < 'a' || move[2] > 'i'
            || move[1] < '0' || move[1] > '9' || move[3] < '0' || move[3] > '9') return 2;
        int s = (move[1] - '0') * 9 + move[0] - 'a', t = (move[3] - '0') * 9 + move[2] - 'a';
        if (board[s] != '.' && red(board[s]) != side) return 3;
        int m = s * 90 + t;
        const auto& a = actions();
        if (!std::binary_search(a.begin(), a.end(), m)) return 4;
        advance(m); return 0;
    }
};
uint32_t next_rng(uint32_t& x) { x ^= x << 13; x ^= x >> 17; x ^= x << 5; return x; }
std::string record(State& s) {
    std::string out = "{\"board\":\"" + std::string(s.board.data()) + "\",\"turn\":\""
        + (s.side ? "red" : "black") + "\",\"moves\":[";
    for (size_t i = 0; i < s.history.size(); ++i) {
        if (i) out += ',';
        out += '"' + move_text(s.history[i]) + '"';
    }
    return out + "],\"result\":" + std::to_string(s.result()) + "}";
}
uint64_t perft(Board& b, bool side, int depth) {
    if (!depth) return 1;
    auto moves = legal(b, side);
    uint64_t count = 0;
    for (int m : moves) {
        int s = m / 90, t = m % 90;
        char p = b[s], captured = b[t]; b[t] = p; b[s] = '.';
        count += perft(b, !side, depth - 1);
        b[s] = p; b[t] = captured;
    }
    return count;
}
} // namespace

// Study-private C ABI. Handles are exclusively owned by their Python wrapper;
// no Python callback enters the native trajectory loop.
extern "C" {
void* nb_new() { return new State(); }
void nb_free(void* p) { delete static_cast<State*>(p); }
const char* nb_board(void* p) { return static_cast<State*>(p)->board.data(); }
int nb_turn(void* p) { return static_cast<State*>(p)->side; }
int nb_result(void* p) { return static_cast<State*>(p)->result(); }
int nb_check(void* p) { auto& s = *static_cast<State*>(p); return checked(s.board, s.side); }
int nb_apply(void* p, const char* move) { return static_cast<State*>(p)->apply(move); }
int nb_legal(void* p, int* output, int capacity) {
    auto& s = *static_cast<State*>(p);
    if (s.result()) return 0;
    const auto& a = s.actions();
    if (capacity < static_cast<int>(a.size())) return -1;
    std::copy(a.begin(), a.end(), output);
    return static_cast<int>(a.size());
}
int nb_diagram(void* p, const char* board, int red_turn, int ply, int repetitions) {
    if (std::strlen(board) != 90 || ply < 0 || repetitions < 1) return 1;
    for (int i = 0; i < 90; ++i) if (!std::strchr(".RNBAKCP rnbakcp", board[i]) || board[i] == ' ') return 1;
    auto& s = *static_cast<State*>(p);
    std::copy(board, board + 90, s.board.begin()); s.board[90] = 0;
    s.side = red_turn != 0; s.ply = ply; s.history.clear(); s.repetitions.clear();
    s.repetitions[s.key()] = repetitions; s.dirty = true; return 0;
}
uint64_t nb_perft(int depth) {
    if (depth < 0 || depth > 4) return 0;
    State s; return perft(s.board, s.side, depth);
}
char* nb_rollouts(const uint32_t* seeds, int count, int max_plies) {
    if (count < 1 || count > 128 || max_plies < 0 || max_plies > 300) return nullptr;
    std::vector<State> games(count);
    std::vector<uint32_t> rng(seeds, seeds + count);
    for (uint32_t seed : rng) if (!seed) return nullptr;
    for (int ply = 0; ply < max_plies; ++ply) {
        bool active = false;
        for (int i = 0; i < count; ++i) {
            auto& s = games[i];
            if (s.result()) continue;
            active = true;
            const auto& a = s.actions();
            int move = a[next_rng(rng[i]) % a.size()];
            s.advance(move);
        }
        if (!active) break;
    }
    std::string out = "[";
    for (int i = 0; i < count; ++i) { if (i) out += ','; out += record(games[i]); }
    out += ']';
    auto* result = static_cast<char*>(std::malloc(out.size() + 1));
    if (result) std::memcpy(result, out.c_str(), out.size() + 1);
    return result;
}
void nb_release(void* p) { std::free(p); }
}
