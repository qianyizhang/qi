// Python owns handles. C++ owns game state. No raw pointers cross this boundary.
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <memory>
#include <stdexcept>
#include <unordered_set>
#include "core.hpp"

namespace py = pybind11;
using qi_native::State;

namespace {
int action(const std::string& move) {
    int source = (move[1] - '0') * 9 + move[0] - 'a';
    int target = (move[3] - '0') * 9 + move[2] - 'a';
    return source * 90 + target;
}

std::pair<int, int> step_many(const std::vector<std::shared_ptr<State>>& states,
                             const std::vector<std::string>& moves) {
    if (states.size() != moves.size() || states.empty() || states.size() > 128)
        throw std::invalid_argument("Batch needs 1..128 states and exactly one action per state.");
    std::unordered_set<State*> seen;
    std::vector<State> pending;
    pending.reserve(states.size());
    for (size_t i = 0; i < states.size(); ++i) {
        if (!states[i] || !seen.insert(states[i].get()).second)
            throw std::invalid_argument("Batch states must be distinct live handles.");
        // Stage all changes. Any rule or allocation error leaves every game intact.
        pending.push_back(*states[i]);
        int error = pending.back().validate(moves[i]);
        if (error) return {static_cast<int>(i), error};
        pending.back().advance(action(moves[i]));
    }
    static_assert(std::is_nothrow_move_assignable_v<State>);
    for (size_t i = 0; i < states.size(); ++i) *states[i] = std::move(pending[i]);
    return {-1, 0};
}
}

PYBIND11_MODULE(_native, module) {
    module.doc() = "Qi C++17 persistent game execution";
    module.attr("compiler") = __VERSION__;
    py::class_<State, std::shared_ptr<State>>(module, "State")
        .def(py::init([](const std::vector<std::string>& moves) {
            if (moves.size() > 300) throw std::invalid_argument("History exceeds 300 plies.");
            auto state = std::make_shared<State>();
            for (const auto& move : moves) {
                int error = state->validate(move);
                if (error) throw std::invalid_argument("Invalid history: rule error " + std::to_string(error));
                state->advance(action(move));
            }
            return state;
        }))
        .def("inspect", [](State& state) {
            int result = state.result();
            std::vector<std::string> moves, history;
            if (!result) for (int move : state.actions()) moves.push_back(qi_native::move_text(move));
            for (int move : state.history) history.push_back(qi_native::move_text(move));
            return py::make_tuple(std::string(state.board.data(), 90), state.side, result,
                                  qi_native::checked(state.board, state.side), moves, history);
        });
    // Keep the GIL: exclusive game ownership is the initial concurrency policy.
    module.def("step_many", &step_many);
}
