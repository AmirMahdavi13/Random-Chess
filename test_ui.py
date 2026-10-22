# -*- coding: utf-8 -*-
"""Render UI screens headlessly and save screenshots for visual inspection."""

import os
import sys

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui import App, BOARD_X, BOARD_Y, SQ
from engine import Board, WHITE, BLACK

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shots')
os.makedirs(OUT, exist_ok=True)


def shot_settings():
    app = App(headless=True)
    app.draw()
    app.screenshot(os.path.join(OUT, 'settings.png'))
    print('saved settings.png')


def shot_game_classic():
    app = App(headless=True)
    app.cfg.update({'mode': 'classic', 'opponent': 'ai', 'difficulty': 'hard',
                    'side': 'white', 'minutes': 10})
    app.start_game()
    # pretend two moves were played + a selection with legal dots
    app.moves_count = 2
    app.last_move = (52, 36)  # e2-e4
    app.board.make((52, 36, None, 1))
    app.board.make((12, 28, None, 1))  # e7-e5
    app.moves_count = 2
    app.last_move = (12, 28)
    # select the knight g1 -> shows legal dots
    app.selected = 62
    app.legal_cache = [m for m in app.board.legal_moves() if m[0] == 62]
    app.draw()
    app.screenshot(os.path.join(OUT, 'game_classic.png'))
    print('saved game_classic.png  (selected knight, legal dots, last move tint)')


def shot_game_random():
    app = App(headless=True)
    app.cfg.update({'mode': 'random', 'opponent': '2p', 'minutes': 15})
    app.start_game()
    app.draw()
    app.screenshot(os.path.join(OUT, 'game_random.png'))
    print('saved game_random.png  (badges on pieces + pattern table)')


def shot_promo_and_over():
    app = App(headless=True)
    app.cfg.update({'mode': 'classic', 'opponent': 'ai', 'minutes': 10})
    app.start_game()
    app.board = Board.from_fen('8/P6k/8/8/8/8/8/K6R w - - 0 1')
    app.selected = 48  # pawn a7
    app.legal_cache = [m for m in app.board.legal_moves() if m[0] == 48]
    app.promo = (48, 0)
    app.draw()
    app.screenshot(os.path.join(OUT, 'promo.png'))
    print('saved promo.png')

    app2 = App(headless=True)
    app2.cfg.update({'mode': 'classic', 'opponent': '2p', 'minutes': 10})
    app2.start_game()
    app2.over = ('mate', WHITE)
    app2.draw()
    app2.screenshot(os.path.join(OUT, 'gameover.png'))
    print('saved gameover.png')


def shot_flipped():
    app = App(headless=True)
    app.cfg.update({'mode': 'random', 'opponent': 'ai', 'difficulty': 'medium',
                    'side': 'black', 'minutes': 15})
    app.start_game()
    app.draw()  # board flipped, black at bottom (AI already "thinking" not triggered: update not called)
    app.screenshot(os.path.join(OUT, 'flipped.png'))
    print('saved flipped.png')


def shot_stalemate_and_hint():
    app = App(headless=True)
    app.cfg.update({'mode': 'classic', 'opponent': '2p', 'minutes': None})
    app.start_game()
    app.over = ('stalemate', None)
    app.draw()
    app.screenshot(os.path.join(OUT, 'stalemate.png'))
    print('saved stalemate.png')

    app2 = App(headless=True)
    app2.cfg['mode'] = 'random'
    app2.state = 'settings'
    app2.draw()
    app2.screenshot(os.path.join(OUT, 'settings.png'))
    print('re-saved settings.png (wrapped hint)')


def test_animation():
    from engine import NORMAL
    app = App(headless=True)
    app.cfg.update({'mode': 'classic', 'opponent': 'ai', 'difficulty': 'easy',
                    'side': 'white', 'minutes': None})
    app.start_game()
    app.update(16)  # not human's turn handling — white is human, AI waits
    # human plays e2-e4 via play_move -> animation must engage
    m = (52, 36, None, NORMAL)
    app.play_move(m)
    assert app.anim is not None and app.anim[0][1] == 52 and app.anim[0][2] == 36
    assert app.board.squares[36] is not None  # position already updated
    # mid-animation frame: e4 must be empty (piece is sliding), e2 empty too
    app.draw()
    app.screenshot(os.path.join(OUT, 'anim_mid.png'))
    ticks = 0
    while app.anim is not None and ticks < 20000:
        app.update(16)
        pygame.time.wait(2)  # anim uses real time; let 220ms actually pass
        ticks += 1
    assert app.anim is None, 'animation did not finish'
    print(f'ok    move animation cleared after {ticks} ticks (~{ticks * 2}ms)')

    # full game with animations still works end to end
    import random as _rnd
    app2 = App(headless=True)
    app2.cfg.update({'mode': 'random', 'opponent': 'ai', 'difficulty': 'easy',
                     'side': 'white', 'minutes': None})
    app2.start_game()
    app2.ANIM_MS = 0  # headless fast-forward (real game runs at 60 fps)
    for _ in range(30000):
        if app2.over:
            break
        app2.update(16)
        if app2.over or app2.anim is not None or app2.thinking or app2.promo is not None:
            continue
        if app2.board.turn in app2.human_colors:
            moves = app2.board.legal_moves()
            if not moves:
                break
            mv = _rnd.choice(moves)
            app2.play_move((mv[0], mv[1], mv[2], NORMAL) if mv[2] else mv)
    print('ok    random mixed loop with animation finished, over =', app2.over,
          'moves =', app2.moves_count)
    app2.draw()
    app2.screenshot(os.path.join(OUT, 'loop_end.png'))


def test_undo():
    from engine import NORMAL
    app = App(headless=True)
    app.ANIM_MS = 0
    app.cfg.update({'mode': 'classic', 'opponent': 'ai', 'difficulty': 'easy',
                    'side': 'white', 'minutes': None})
    app.start_game()
    # human e2-e4, then let the AI answer
    app.play_move((52, 36, None, NORMAL))
    app.update(16)  # clears human-move anim, AI answers within the same tick
    assert app.moves_count == 2, 'AI did not answer'
    app.update(16)  # clear the AI-move animation before undoing
    snap_after_2 = [p and (p[0], p[1], p[2]) for p in app.board.squares]
    snap_after_2_turn = app.board.turn
    # undo takes back both half-moves -> start position, white to move
    app.undo_moves()
    assert app.moves_count == 0 and app.board.turn == 0
    assert app.board.squares[52] is not None and app.board.squares[36] is None
    assert app.board.squares[60][1] == 'K' and app.board.squares[4][1] == 'K'
    # undo with empty history shows the flash message, no crash
    app.undo_moves()
    assert app.flash is not None
    # two-player mode: undo takes back exactly one half-move
    app2 = App(headless=True)
    app2.ANIM_MS = 0
    app2.cfg.update({'mode': 'classic', 'opponent': '2p', 'minutes': None})
    app2.start_game()
    app2.play_move((52, 36, None, NORMAL))
    app2.update(16)  # clear move animation
    app2.undo_moves()
    assert app2.moves_count == 0 and app2.board.turn == 0
    assert app2.board.squares[52] is not None
    # undo after game over revives the game
    app3 = App(headless=True)
    app3.ANIM_MS = 0
    app3.cfg.update({'mode': 'classic', 'opponent': 'ai', 'difficulty': 'easy',
                     'side': 'white', 'minutes': None})
    app3.start_game()
    app3.play_move((52, 36, None, NORMAL))
    app3.update(16)  # AI answers, anim cleared in the same tick
    app3.update(16)  # clear AI-move animation
    app3.over = ('mate', 1)  # simulate an end state
    app3.undo_moves()
    assert app3.over is None and app3.board.turn == 0
    print('ok    undo: AI pair, two-player single, empty-history flash, after game over')


if __name__ == '__main__':
    shot_settings()
    shot_game_classic()
    shot_game_random()
    shot_promo_and_over()
    shot_flipped()
    shot_stalemate_and_hint()
    test_animation()
    test_undo()
    pygame.quit()
    print('done')
