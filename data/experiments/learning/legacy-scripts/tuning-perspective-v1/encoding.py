"""Prototype mover-relative observation/action mapping, not a production encoding."""
from hashlib import sha256
import torch
from qi.game import legal_moves
from qi.players.policy.encoding import PIECES, action_id

def key(game):
    board=game.board if game.turn=='red' else tuple(p.swapcase() for p in reversed(game.board))
    return sha256(('mover-relative-prototype-v1:'+''.join(board)).encode()).hexdigest()

def tensors(labels):
    x=torch.zeros((len(labels),1261),dtype=torch.float32)
    mask=torch.zeros((len(labels),8100),dtype=torch.bool)
    y=torch.empty(len(labels),dtype=torch.long)
    for i,label in enumerate(labels):
        game=label.analysis.snapshot.game(); black=game.turn=='black'
        board=game.board if not black else tuple(p.swapcase() for p in reversed(game.board))
        for square,piece in enumerate(board):
            if piece!='.': x[i,PIECES.index(piece)*90+square]=1.
        ids=[action_id(move) for move in legal_moves(game.board,game.turn)]
        mask[i,[8099-id if black else id for id in ids]]=True
        target=action_id(label.analysis.move); y[i]=8099-target if black else target
    return x,mask,y
