# -*- coding: utf-8 -*-
"""Sanity tests for the bot: finds mates, returns legal moves, reasonable speed."""

import time

from engine import Board, QUEEN, WHITE, BLACK
from ai import AI


def sq(name):
    return (8 - int(name[1])) * 8 + 'abcdefgh'.index(name[0])


def test_finds_mate_in_one():
    # 1...Qh4# style: back-rank mate available with Ra8
    b = Board.from_fen('6k1/5ppp/8/8/8/8/5PPP/R6K w - - 0 1')
    for level in ('medium', 'hard'):
        m = AI(b).choose_move(level)
        assert m is not None and m[1] == sq('a8'), (level, m)
        print(f'ok    {level} finds back-rank mate in 1 (Ra8)')


def test_easy_returns_legal():
    b = Board().new_game()
    legal = set(b.legal_moves())
    for _ in range(10):
        m = AI(b).choose_move('easy')
        assert m in legal
    print('ok    easy returns legal moves')


def test_random_mode_ai():
    for seed in range(3):
        b = Board().new_game(random_mode=True, seed=seed)
        legal = set(b.legal_moves())
        for level in ('easy', 'medium', 'hard'):
            m = AI(b).choose_move(level)
            assert m in legal, (seed, level)
        # play a few full moves both sides
        for _ in range(6):
            if not b.legal_moves():
                break
            b.make(AI(b).choose_move('medium'))
    print('ok    random-mode AI search works')


def test_speed():
    b = Board().new_game()
    for level in ('medium', 'hard'):
        t0 = time.time()
        AI(b).choose_move(level)
        print(f'ok    {level} first move in {time.time() - t0:.2f}s')
    # a middlegame-ish position with more branching
    b = Board.from_fen('r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 0 1')
    t0 = time.time()
    AI(b).choose_move('hard')
    print(f'ok    hard middlegame move in {time.time() - t0:.2f}s')


def test_promotes_to_queen():
    b = Board.from_fen('8/P6k/8/8/8/8/8/K7 w - - 0 1')
    m = AI(b).choose_move('hard')
    assert m[2] == QUEEN, m
    print('ok    promotes to queen when winning')


if __name__ == '__main__':
    test_finds_mate_in_one()
    test_easy_returns_legal()
    test_promotes_to_queen()
    test_random_mode_ai()
    test_speed()
    print('\nAll AI tests passed.')
