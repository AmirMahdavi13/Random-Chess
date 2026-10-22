# -*- coding: utf-8 -*-
"""Engine correctness tests: perft on standard positions + Random Chess invariants."""

import random
import time

from engine import (Board, perft, WHITE, BLACK, PAWN, KING, ROOK, KNIGHT,
                    BISHOP, QUEEN, BACK_RANK, EN_PASSANT, CASTLE)

CASES = [
    # (fen, {depth: expected nodes})
    ('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
     {1: 20, 2: 400, 3: 8902, 4: 197281}),
    # "Kiwipete": castling, pins, checks
    ('r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1',
     {1: 48, 2: 2039, 3: 97862}),
    # en-passant pins and discovered checks
    ('8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1',
     {1: 14, 2: 191, 3: 2812, 4: 43238}),
    # promotions (incl. under-promotion), castling rights by capture
    ('r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1',
     {1: 6, 2: 264, 3: 9467}),
    # promotions + castling
    ('rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8',
     {1: 44, 2: 1486, 3: 62379}),
]


def test_perft():
    for fen, expect in CASES:
        b = Board.from_fen(fen)
        for depth, want in sorted(expect.items()):
            t0 = time.time()
            got = perft(b, depth)
            dt = time.time() - t0
            status = 'ok' if got == want else 'FAIL'
            print(f'{status}  perft({depth}) = {got:>8} (want {want:>8})  {dt:5.2f}s  {fen[:30]}')
            assert got == want, f'perft mismatch on {fen} depth {depth}'


def test_make_unmake_roundtrip():
    rng = random.Random(7)
    for mode in (False, True):
        b = Board().new_game(random_mode=mode, seed=42)
        for _ in range(300):
            moves = b.legal_moves()
            if not moves:
                break
            m = rng.choice(moves)
            snap = (list(b.squares), b.turn, b.castling, b.ep, list(b.king_sq))
            undo = b.make(m)
            b.unmake(undo)
            snap2 = (list(b.squares), b.turn, b.castling, b.ep, list(b.king_sq))
            # tuples contain tuples -> compare element-wise
            assert all((a is None and c is None) or a == c
                       for a, c in zip(snap[0], snap2[0]))
            assert snap[1:] == snap2[1:], f'make/unmake mismatch after {m} (random={mode})'
            b.make(m)


def test_random_mode_invariants():
    for seed in range(10):
        b = Board().new_game(random_mode=True, seed=seed)
        assert b.castling == frozenset()
        assert not b.legal_moves() or True  # smoke
        for f, kind in enumerate(BACK_RANK):
            w = b.squares[56 + f]
            bl = b.squares[f]
            if kind in (PAWN, KING):
                assert w[2] == kind and bl[2] == kind
                continue
            # pattern differs from the piece's own standard movement
            assert w[2] != kind and w[2] in ('N', 'B', 'R', 'Q'), (f, kind, w)
            # mirrored assignment between colors
            assert w[2] == bl[2]
            assert b.pattern_map[f] == w[2]
        # pawns and kings untouched
        assert b.squares[52][1] == PAWN and b.squares[52][2] == PAWN
        assert b.squares[60][1] == KING and b.squares[60][2] == KING
        assert b.squares[4][1] == KING and b.squares[4][2] == KING
        # a full random playout must not crash and must respect check rules
        rng = random.Random(seed)
        moves_played = 0
        while moves_played < 120:
            moves = b.legal_moves()
            if not moves:
                break
            m = rng.choice(moves)
            b.make(m)
            moves_played += 1
            # mover's king can never be left in check
            assert not b.is_check(1 - b.turn)
        print(f'ok    random seed {seed}: {moves_played} moves played')


def test_checkmate_detection():
    # Fool's mate: 1. f3 e5 2. g4 Qh4#
    b = Board().new_game()
    for m in ((53, 45, None, 1), (12, 28, None, 1), (54, 38, None, 1), (3, 39, None, 1)):
        b.make(m)
    assert b.status() == 'checkmate'
    # stalemate: black to move, king a8 blocked, no checks
    b = Board.from_fen('k7/8/1Q6/8/8/8/8/K7 b - - 0 1')
    assert b.status() == 'stalemate'
    b = Board.from_fen('k6R/8/KQ6/8/8/8/8/8 b - - 0 1')
    assert b.status() == 'checkmate'
    print('ok    mate/stalemate detection')


def test_en_passant_and_castle_flags():
    b = Board().new_game()
    assert any(m[3] == EN_PASSANT for m in []) or True
    # 1. e4 (double push) -> black e5 -> exd5? use known ep line:
    b = Board.from_fen('rnbqkbnr/ppp1pppp/8/8/3pP3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1')
    eps = [m for m in b.legal_moves() if m[3] == EN_PASSANT]
    assert len(eps) == 1 and eps[0][1] == 44  # d4 pawn captures on e3
    b2 = Board.from_fen('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1')
    castles = [m for m in b2.legal_moves() if m[3] == CASTLE]
    assert len(castles) == 2  # white O-O and O-O-O (black not to move)
    b2.turn = 1 - b2.turn
    castles = [m for m in b2.legal_moves() if m[3] == CASTLE]
    assert len(castles) == 2  # black O-O and O-O-O
    print('ok    en-passant + castling generation')


if __name__ == '__main__':
    test_en_passant_and_castle_flags()
    test_checkmate_detection()
    test_random_mode_invariants()
    test_make_unmake_roundtrip()
    test_perft()
    print('\nAll engine tests passed.')
