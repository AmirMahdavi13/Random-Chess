# -*- coding: utf-8 -*-
"""
Graphical chess interface (pygame) with Persian UI:
  - classic chess or "Random Chess" (random movement patterns per game)
  - vs computer (easy/medium/hard) or two players on one screen
  - 10/15 minute clocks or unlimited
"""

import os
import random
import sys
import time

import pygame

from engine import (Board, WHITE, BLACK, other, FILES, NORMAL, EN_PASSANT,
                    CASTLE, PAWN, KING, QUEEN, ROOK, BISHOP, KNIGHT,
                    BACK_RANK)
from ai import AI

# ----------------------------------------------------------- Persian text

try:
    import arabic_reshaper
    from bidi.algorithm import get_display

    _reshaper = arabic_reshaper.ArabicReshaper()

    def fa(text):
        """Shape Persian text for correct pygame rendering (RTL + joined)."""
        if not text or text.isascii():
            return text
        return get_display(_reshaper.reshape(text))
except ImportError:  # pragma: no cover - fallback if libs are missing
    def fa(text):
        return text

FA_DIGITS = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')


def fa_num(text):
    return text.translate(FA_DIGITS)


STR = {
    'title': ('شطرنج', 'Chess'),
    'mode': ('حالت بازی', 'Game mode'),
    'classic': ('شطرنج کلاسیک', 'Classic Chess'),
    'random': ('Random Chess', 'Random Chess'),
    'opponent': ('حریف', 'Opponent'),
    'computer': ('بازی با کامپیوتر', 'vs Computer'),
    'twoplayer': ('بازی دو نفره', 'Two players'),
    'difficulty': ('سطح دشواری', 'Difficulty'),
    'easy': ('آسان', 'Easy'),
    'medium': ('متوسط', 'Medium'),
    'hard': ('سخت', 'Hard'),
    'side': ('رنگ شما', 'Your color'),
    'white': ('سفید', 'White'),
    'black': ('سیاه', 'Black'),
    'time': ('زمان هر بازیکن', 'Time per player'),
    'min10': ('۱۰ دقیقه', '10 min'),
    'min15': ('۱۵ دقیقه', '15 min'),
    'notime': ('بدون محدودیت', 'Unlimited'),
    'start': ('شروع بازی', 'Start game'),
    'exit': ('خروج', 'Exit'),
    'randomhint': ('در حالت Random Chess، در هر بازیِ جدید مهره‌های غیر از پیاده و شاه '
                   'الگوی حرکت تصادفی می‌گیرند (مثلاً اسب مثل رخ حرکت کند).',
                   'In Random Chess every new game shuffles the movement patterns.'),
    'turn': ('نوبت', 'Turn'),
    'check': ('کیش!', 'Check!'),
    'thinking': ('در حال فکر…', 'Thinking…'),
    'resign': ('تسلیم', 'Resign'),
    'undo': ('برگشت حرکت', 'Undo move'),
    'nothing': ('حرکتی برای برگشت نیست', 'Nothing to undo'),
    'rematch': ('بازی جدید', 'New game'),
    'menu': ('منوی اصلی', 'Main menu'),
    'promotitle': ('ارتقای پیاده — یک مهره را انتخاب کن', 'Promote pawn — choose a piece'),
    'pawnsnormal': ('پیاده‌ها و شاه: حرکت عادی', 'Pawns & king: normal'),
    'like': ('مثل', 'like'),
    'patterns': ('الگوی حرکت مهره‌ها در این بازی', 'Movement patterns this game'),
    'mate': ('کیش و مات!', 'Checkmate!'),
    'stalemate': ('پات! بازی مساوی شد', 'Stalemate — draw'),
    'material': ('مساوی — مهره کافی برای مات نیست', 'Draw — insufficient material'),
    'timeout': ('وقت تمام شد', 'Time out'),
    'resigned': ('تسلیم شد', 'resigned'),
    'wins': ('برنده شد', 'won'),
    'computername': ('کامپیوتر', 'Computer'),
    'you': ('شما', 'You'),
    'player': ('بازیکن', 'Player'),
}

FA_OK = fa('سلام') != 'سلام' or True  # shaping applied when libs present


def T(key):
    return STR[key][0]


# ----------------------------------------------------------------- layout

WIN_W, WIN_H = 1000, 700
SQ = 79
BOARD_X, BOARD_Y = 30, 26
BOARD_PX = SQ * 8
SIDE_X = BOARD_X + BOARD_PX + 22          # 684
SIDE_W = WIN_W - SIDE_X - 16              # 300

BG = (36, 32, 28)
PANEL = (56, 50, 44)
PANEL_HI = (74, 66, 57)
ACCENT = (106, 153, 78)
ACCENT_DARK = (78, 118, 56)
GOLD = (198, 164, 92)
TEXT = (238, 232, 222)
DIM = (168, 158, 146)
LIGHT_SQ = (238, 216, 180)
DARK_SQ = (175, 131, 94)
SEL_TINT = (247, 223, 111, 110)
LAST_TINT = (250, 220, 120, 80)
CHECK_TINT = (226, 74, 60, 130)
DOT_COLOR = (25, 22, 18, 115)

GLYPH = {PAWN: '♟', KNIGHT: '♞', BISHOP: '♝', ROOK: '♜', QUEEN: '♛', KING: '♚'}
PIECE_FILL = {WHITE: (250, 250, 244), BLACK: (38, 34, 30)}
PIECE_OUTLINE = {WHITE: (56, 46, 36), BLACK: (208, 198, 178)}

FA_FONT_NAMES = 'tahoma,segoeui,arial'
GLYPH_FONT_NAMES = 'segoeuisymbol,dejavusans,tahoma'


class Button:
    __slots__ = ('rect', 'kind', 'value')

    def __init__(self, rect, kind, value=None):
        self.rect = rect
        self.kind = kind
        self.value = value


class App:
    def __init__(self, headless=False):
        if headless:
            os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
            os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
        pygame.init()
        pygame.display.set_caption('شطرنج — Chess & Random Chess')
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        self._set_icon()
        self.clock = pygame.time.Clock()
        self.fonts = {
            'title': self._font(FA_FONT_NAMES, 44, bold=True),
            'label': self._font(FA_FONT_NAMES, 20, bold=True),
            'pill': self._font(FA_FONT_NAMES, 19),
            'big': self._font(FA_FONT_NAMES, 24, bold=True),
            'text': self._font(FA_FONT_NAMES, 18),
            'small': self._font(FA_FONT_NAMES, 15),
            'clock': self._font(FA_FONT_NAMES, 30, bold=True),
            'glyph': self._font(GLYPH_FONT_NAMES, int(SQ * 0.86)),
            'glyph_mid': self._font(GLYPH_FONT_NAMES, 30),
            'glyph_small': self._font(GLYPH_FONT_NAMES, 19),
            'coord': self._font(FA_FONT_NAMES, 14),
        }
        self._piece_cache = {}
        self._glyph_cache = {}
        self.buttons = []
        # settings
        self.cfg = {'mode': 'classic', 'opponent': 'ai', 'difficulty': 'medium',
                    'side': 'white', 'minutes': 10}
        self.state = 'settings'
        self._init_game_state()

    # ------------------------------------------------------------ helpers

    @staticmethod
    def _font(names, size, bold=False):
        return pygame.font.SysFont(names, size, bold=bold)

    def _set_icon(self):
        surf = pygame.Surface((32, 32))
        surf.fill(DARK_SQ)
        pygame.draw.rect(surf, LIGHT_SQ, (0, 0, 16, 16))
        pygame.draw.rect(surf, LIGHT_SQ, (16, 16, 16, 16))
        try:
            f = pygame.font.SysFont(GLYPH_FONT_NAMES, 26)
            surf.blit(f.render('♞', True, (20, 18, 16)), (4, 2))
        except Exception:
            pass
        pygame.display.set_icon(surf)

    def text(self, key, size='text', color=TEXT):
        return self.fonts[size].render(fa(T(key)), True, color)

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.on_click(event.pos)
            self.update(dt)
            self.draw()
            pygame.display.flip()
        pygame.quit()

    # --------------------------------------------------------- game setup

    def _init_game_state(self):
        self.board = None
        self.human_colors = ()
        self.ai_color = None
        self.clocks = {}
        self.selected = None
        self.legal_cache = []
        self.last_move = None
        self.moves_count = 0
        self.over = None          # (key, winner_color_or_None, extra)
        self.promo = None         # (frm, to) while promotion dialog is open
        self.thinking = False
        self.view_flip = False
        self.anim = None          # [(piece, frm, to)] while sliding
        self.anim_start = 0
        self.history = []         # [(engine undo record, previous last_move)]
        self.flash = None         # (text, until_ticks) for transient messages

    ANIM_MS = 220

    def start_game(self):
        self._init_game_state()
        self.board = Board().new_game(random_mode=(self.cfg['mode'] == 'random'))
        minutes = self.cfg['minutes']
        ms = minutes * 60_000 if minutes else None
        self.clocks = {WHITE: ms, BLACK: ms}
        if self.cfg['opponent'] == 'ai':
            human = WHITE if self.cfg['side'] == 'white' else BLACK
            self.human_colors = (human,)
            self.ai_color = other(human)
        else:
            self.human_colors = (WHITE, BLACK)
            self.ai_color = None
        self.view_flip = (self.ai_color == WHITE)
        self.state = 'game'

    def player_name(self, color):
        if self.cfg['opponent'] == 'ai':
            if color == self.ai_color:
                return fa(f"{T('computername')} ({T(self.cfg['difficulty'])})")
            return fa(T('you'))
        return fa(f"{T('player')} — {T('white') if color == WHITE else T('black')}")

    # ------------------------------------------------------------ updates

    def update(self, dt):
        if self.state != 'game' or self.board is None:
            return
        if self.anim is not None:
            if pygame.time.get_ticks() - self.anim_start < self.ANIM_MS:
                return  # still sliding
            self.anim = None  # finished: fall through and continue the turn
        if self.over or self.promo is not None:
            return
        minutes = self.cfg['minutes']
        if minutes and self.moves_count >= 1:
            self.clocks[self.board.turn] -= dt
            if self.clocks[self.board.turn] <= 0:
                self.clocks[self.board.turn] = 0
                loser = self.board.turn
                self.over = ('timeout', other(loser))
                return
        if (self.ai_color is not None and self.board.turn == self.ai_color
                and not self.thinking):
            self._ai_move()

    def _ai_move(self):
        self.thinking = True
        self.draw()                       # show the "thinking" state
        pygame.display.flip()
        pygame.event.pump()
        t0 = time.time()
        move = AI(self.board).choose_move(self.cfg['difficulty'])
        if self.cfg['minutes'] and self.moves_count >= 1:
            self.clocks[self.ai_color] -= int((time.time() - t0) * 1000)
        self.thinking = False
        if move is None:
            return
        if self.clocks.get(self.ai_color, 1) is not None and self.clocks[self.ai_color] <= 0:
            self.clocks[self.ai_color] = 0
            self.over = ('timeout', other(self.ai_color))
            return
        self.play_move(move)

    def undo_moves(self):
        """Take back the last half-move (two-player) or full move pair (vs AI)."""
        if self.anim is not None or self.thinking or self.promo is not None:
            return
        if self.ai_color is not None and self.board.turn == self.ai_color:
            return  # AI is about to move; let it finish first
        if self.ai_color is not None:
            n = 2 if len(self.history) >= 2 else 0
        else:
            n = 1 if self.history else 0
        if n == 0:
            self.flash = (T('nothing'), pygame.time.get_ticks() + 1500)
            return
        for _ in range(n):
            undo, prev_last = self.history.pop()
            self.board.unmake(undo)
            self.last_move = prev_last
        self.moves_count -= n
        self.selected = None
        self.legal_cache = []
        self.over = None  # undo is allowed even after the game ended

    def play_move(self, move):
        frm, to, promo, flag = move
        board = self.board
        color = board.turn
        moving = board.squares[frm]
        # record pieces to animate before the position changes
        self.anim = [(moving, frm, to)]
        if flag == CASTLE:  # the rook slides too
            home = 7 if color == WHITE else 0
            if to % 8 == 6:
                self.anim.append((board.squares[home * 8 + 7], home * 8 + 7, home * 8 + 5))
            else:
                self.anim.append((board.squares[home * 8 + 0], home * 8 + 0, home * 8 + 3))
        self.anim_start = pygame.time.get_ticks()
        self.history.append((board.make(move), self.last_move))
        self.moves_count += 1
        self.last_move = (frm, to)
        self.selected = None
        self.legal_cache = []
        status = board.status()
        if status == 'checkmate':
            self.over = ('mate', other(board.turn))
        elif status == 'stalemate':
            self.over = ('stalemate', None)
        elif status == 'material_draw':
            self.over = ('material', None)

    # ------------------------------------------------------------- input

    def on_click(self, pos):
        for btn in self.buttons:
            if btn.rect.collidepoint(pos):
                self.on_button(btn)
                return
        if self.state == 'game' and self.promo is None and not self.over:
            self.on_board_click(pos)

    def on_button(self, btn):
        kind = btn.kind
        if kind == 'opt':
            group, value = btn.value
            self.cfg[group] = value
        elif kind == 'start':
            self.start_game()
        elif kind == 'exit':
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        elif kind == 'resign':
            if self.board is None or self.over:
                return
            if self.ai_color is not None:
                loser = self.human_colors[0]
            else:
                loser = self.board.turn
            self.over = ('resign', other(loser))
        elif kind == 'undo':
            self.undo_moves()
        elif kind == 'rematch':
            self.start_game()
        elif kind == 'menu':
            self.state = 'settings'
            self._init_game_state()
        elif kind == 'promo':
            frm, to = self.promo
            self.promo = None
            self.play_move((frm, to, btn.value, NORMAL))

    def square_at(self, pos):
        x, y = pos
        if not (BOARD_X <= x < BOARD_X + BOARD_PX and BOARD_Y <= y < BOARD_Y + BOARD_PX):
            return None
        vc = (x - BOARD_X) // SQ
        vr = (y - BOARD_Y) // SQ
        if self.view_flip:
            vc, vr = 7 - vc, 7 - vr
        return vr * 8 + vc

    def on_board_click(self, pos):
        if self.thinking or self.anim is not None or self.board.turn not in self.human_colors:
            return
        sq = self.square_at(pos)
        if sq is None:
            return
        if self.selected is not None:
            candidates = [m for m in self.legal_cache if m[1] == sq]
            if candidates:
                if candidates[0][2] is not None:      # promotion
                    self.promo = (self.selected, sq)
                else:
                    self.play_move(candidates[0])
                return
        piece = self.board.squares[sq]
        if piece is not None and piece[0] == self.board.turn:
            self.selected = sq
            self.legal_cache = [m for m in self.board.legal_moves() if m[0] == sq]
        else:
            self.selected = None
            self.legal_cache = []

    # --------------------------------------------------------------- draw

    def draw(self):
        self.buttons = []
        self.screen.fill(BG)
        if self.state == 'settings':
            self.draw_settings()
        else:
            self.draw_game()
            if self.promo is not None:
                self.draw_promo_dialog()
            elif self.over is not None:
                self.draw_over_dialog()

    # ------------------------------------------------------ settings menu

    def draw_settings(self):
        scr = self.screen
        # title
        title = self.fonts['title'].render(fa(T('title')), True, TEXT)
        scr.blit(title, title.get_rect(center=(WIN_W // 2, 58)))
        g1 = self.fonts['glyph_mid'].render('♛', True, GOLD)
        g2 = self.fonts['glyph_mid'].render('♚', True, GOLD)
        scr.blit(g1, (WIN_W // 2 - title.get_width() // 2 - 48, 44))
        scr.blit(g2, (WIN_W // 2 + title.get_width() // 2 + 20, 44))

        groups = [
            ('mode', [('classic', T('classic')), ('random', T('random'))]),
            ('opponent', [('ai', T('computer')), ('2p', T('twoplayer'))]),
        ]
        if self.cfg['opponent'] == 'ai':
            groups.append(('difficulty', [('easy', T('easy')), ('medium', T('medium')),
                                          ('hard', T('hard'))]))
            groups.append(('side', [('white', T('white')), ('black', T('black'))]))
        groups.append(('minutes', [(10, T('min10')), (15, T('min15')),
                                   (None, T('notime'))]))

        y = 118
        for group, options in groups:
            y = self.draw_option_group(y, group, options)

        # start button
        start = self.fonts['big'].render(fa(T('start')), True, (18, 24, 14))
        rect = pygame.Rect(0, 0, 240, 56)
        rect.center = (WIN_W // 2, y + 44)
        pygame.draw.rect(scr, ACCENT, rect, border_radius=12)
        scr.blit(start, start.get_rect(center=rect.center))
        self.buttons.append(Button(rect, 'start'))
        # exit
        ex = self.fonts['text'].render(fa(T('exit')), True, DIM)
        er = pygame.Rect(0, 0, 110, 38)
        er.center = (WIN_W // 2 + 190, y + 44)
        pygame.draw.rect(scr, PANEL, er, border_radius=10)
        pygame.draw.rect(scr, PANEL_HI, er, 1, border_radius=10)
        scr.blit(ex, ex.get_rect(center=er.center))
        self.buttons.append(Button(er, 'exit'))

        hint = T('randomhint')
        words = hint.split()
        lines, cur = [], ''
        for w in words:
            trial = (cur + ' ' + w).strip()
            if self.fonts['small'].size(fa(trial))[0] > WIN_W - 80 and cur:
                lines.append(cur)
                cur = w
            else:
                cur = trial
        lines.append(cur)
        for i, line in enumerate(lines):
            surf = self.fonts['small'].render(fa(line), True, DIM)
            scr.blit(surf, surf.get_rect(center=(WIN_W // 2, WIN_H - 52 + i * 22)))

    def draw_option_group(self, y, group, options):
        scr = self.screen
        panel = pygame.Rect(180, y, 640, 74)
        pygame.draw.rect(scr, PANEL, panel, border_radius=12)
        label = self.fonts['label'].render(fa(T(group if group != 'minutes' else 'time')), True, GOLD)
        label_rect = label.get_rect(right=panel.right - 20, centery=panel.centery)
        scr.blit(label, label_rect)
        # option pills laid out right-to-left, to the left of the label
        pill_right = label_rect.left - 24
        selected = self.cfg[group]
        for value, txt in options:
            surf = self.fonts['pill'].render(fa(txt), True, TEXT)
            w = surf.get_width() + 34
            rect = pygame.Rect(pill_right - w, 0, w, 46)
            rect.centery = panel.centery
            is_sel = (value == selected)
            pygame.draw.rect(scr, ACCENT if is_sel else PANEL_HI, rect, border_radius=23)
            scr.blit(surf, surf.get_rect(center=rect.center))
            self.buttons.append(Button(rect, 'opt', (group, value)))
            pill_right = rect.left - 10
        return y + panel.height + 12

    # ------------------------------------------------------------- board

    def view_rect(self, r, c):
        if self.view_flip:
            r, c = 7 - r, 7 - c
        return pygame.Rect(BOARD_X + c * SQ, BOARD_Y + r * SQ, SQ, SQ)

    def piece_surface(self, glyph, fill, outline):
        key = (glyph, fill, outline)
        cached = self._piece_cache.get(key)
        if cached is not None:
            return cached
        f = self.fonts['glyph']
        main = f.render(glyph, True, fill)
        w, h = main.get_size()
        pad = 3
        surf = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        edge = f.render(glyph, True, outline)
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, -2),
                       (-2, 2), (2, 2), (-3, 0), (3, 0)):
            surf.blit(edge, (pad + dx, pad + dy))
        surf.blit(main, (pad, pad))
        self._piece_cache[key] = surf
        return surf

    def glyph_surface(self, glyph, size, color):
        key = (glyph, size, color)
        cached = self._glyph_cache.get(key)
        if cached is None:
            cached = self.fonts[size].render(glyph, True, color)
            self._glyph_cache[key] = cached
        return cached

    def draw_board(self):
        scr = self.screen
        overlay = pygame.Surface((BOARD_PX, BOARD_PX), pygame.SRCALPHA)
        board = self.board
        # squares + last-move tint
        for r in range(8):
            for c in range(8):
                rect = self.view_rect(r, c)
                pygame.draw.rect(scr, LIGHT_SQ if (r + c) % 2 == 0 else DARK_SQ, rect)
        if self.last_move:
            for sq in self.last_move:
                r, c = divmod(sq, 8)
                overlay.fill(LAST_TINT, self.view_rect(r, c).move(-BOARD_X, -BOARD_Y))
        # selection
        if self.selected is not None:
            r, c = divmod(self.selected, 8)
            srect = self.view_rect(r, c).move(-BOARD_X, -BOARD_Y)
            overlay.fill(SEL_TINT, srect)
        # check indicator
        if not self.over or self.over[0] != 'mate':
            for color in (WHITE, BLACK):
                if board.is_check(color):
                    r, c = divmod(board.king_sq[color], 8)
                    krect = self.view_rect(r, c).move(-BOARD_X, -BOARD_Y)
                    pygame.draw.circle(overlay, CHECK_TINT, krect.center, SQ // 2 - 6)
        # legal-move dots
        if self.selected is not None:
            for m in self.legal_cache:
                to = m[1]
                r, c = divmod(to, 8)
                trect = self.view_rect(r, c).move(-BOARD_X, -BOARD_Y)
                if board.squares[to] is not None or m[3] == EN_PASSANT:
                    pygame.draw.circle(overlay, DOT_COLOR, trect.center, SQ // 2 - 7, 6)
                else:
                    pygame.draw.circle(overlay, DOT_COLOR, trect.center, 13)
        scr.blit(overlay, (BOARD_X, BOARD_Y))
        # pieces (skip squares occupied by the sliding animation)
        anim_squares = set()
        if self.anim is not None:
            for _, frm, to in self.anim:
                anim_squares.update((frm, to))
        for r in range(8):
            for c in range(8):
                sq = r * 8 + c
                piece = board.squares[sq]
                if piece is None or sq in anim_squares:
                    continue
                color, kind, pat = piece
                rect = self.view_rect(r, c)
                surf = self.piece_surface(GLYPH[kind], PIECE_FILL[color], PIECE_OUTLINE[color])
                scr.blit(surf, surf.get_rect(center=rect.center))
                if pat != kind:  # Random Chess badge showing real movement
                    self.draw_badge(scr, rect, color, pat)
        # sliding animation on top
        if self.anim is not None:
            elapsed = pygame.time.get_ticks() - self.anim_start
            t = 1.0 if elapsed >= self.ANIM_MS else elapsed / self.ANIM_MS
            t = 1 - (1 - t) ** 3  # ease-out cubic
            for piece, frm, to in self.anim:
                frect = self.view_rect(*divmod(frm, 8))
                trect = self.view_rect(*divmod(to, 8))
                color, kind, pat = piece
                surf = self.piece_surface(GLYPH[kind], PIECE_FILL[color], PIECE_OUTLINE[color])
                x = frect.centerx + (trect.centerx - frect.centerx) * t
                y = frect.centery + (trect.centery - frect.centery) * t
                scr.blit(surf, surf.get_rect(center=(round(x), round(y))))
        # coordinates
        for vc in range(8):
            bc = 7 - vc if self.view_flip else vc
            letter = self.fonts['coord'].render(FILES[bc], True, DIM)
            scr.blit(letter, (BOARD_X + vc * SQ + SQ - letter.get_width() - 3,
                              BOARD_Y + BOARD_PX - letter.get_height() - 1))
        for vr in range(8):
            br = 7 - vr if self.view_flip else vr
            num = self.fonts['coord'].render(str(8 - br), True, DIM)
            scr.blit(num, (BOARD_X + 3, BOARD_Y + vr * SQ + 3))
        # selection border on top
        if self.selected is not None:
            r, c = divmod(self.selected, 8)
            pygame.draw.rect(scr, GOLD, self.view_rect(r, c), 3)

    def draw_badge(self, scr, rect, piece_color, pattern):
        cx = rect.right - 17
        cy = rect.bottom - 17
        if piece_color == WHITE:
            bg, fg = (52, 44, 36), (242, 236, 224)
        else:
            bg, fg = (240, 234, 220), (40, 34, 28)
        pygame.draw.circle(scr, bg, (cx, cy), 14)
        glyph = self.glyph_surface(GLYPH[pattern], 'glyph_small', fg)
        scr.blit(glyph, glyph.get_rect(center=(cx, cy)))

    # ------------------------------------------------------------ sidebar

    def fmt_clock(self, color):
        ms = self.clocks.get(color)
        if ms is None:
            return fa_num('∞')
        s = max(0, ms // 1000)
        return fa_num(f'{s // 60:02d}:{s % 60:02d}')

    def draw_clock_panel(self, y, color):
        scr = self.screen
        rect = pygame.Rect(SIDE_X, y, SIDE_W, 64)
        active = (not self.over and self.board.turn == color)
        pygame.draw.rect(scr, PANEL_HI if active else PANEL, rect, border_radius=10)
        if active:
            pygame.draw.rect(scr, ACCENT, rect, 2, border_radius=10)
        name = self.fonts['text'].render(self.player_name(color), True, TEXT)
        scr.blit(name, name.get_rect(right=rect.right - 14, centery=rect.centery - 8))
        dot = self.fonts['small'].render(
            fa(T('white') if color == WHITE else T('black')), True, DIM)
        scr.blit(dot, dot.get_rect(right=rect.right - 14, centery=rect.centery + 16))
        clk = self.fonts['clock'].render(self.fmt_clock(color), True,
                                         TEXT if active else DIM)
        scr.blit(clk, clk.get_rect(left=rect.left + 14, centery=rect.centery))
        return y + 64 + 12

    def sidebar_button(self, y, key, kind, color=TEXT, bg=PANEL, h=42):
        scr = self.screen
        rect = pygame.Rect(SIDE_X, y, SIDE_W, h)
        pygame.draw.rect(scr, bg, rect, border_radius=10)
        pygame.draw.rect(scr, PANEL_HI, rect, 1, border_radius=10)
        surf = self.fonts['text'].render(fa(T(key)), True, color)
        scr.blit(surf, surf.get_rect(center=rect.center))
        self.buttons.append(Button(rect, kind))
        return y + h + 8

    def draw_sidebar(self):
        scr = self.screen
        y = self.draw_clock_panel(BOARD_Y, BLACK)
        y = self.draw_clock_panel(y, WHITE)
        # status line
        if self.over is None:
            if self.thinking:
                status, col = fa(T('thinking')), GOLD
            else:
                who = T('white') if self.board.turn == WHITE else T('black')
                status, col = fa(f"{T('turn')}: {who}"), TEXT
            if self.board.is_check(self.board.turn):
                status += '  —  ' + fa(T('check'))
                col = (232, 106, 90)
        else:
            status, col = '', TEXT
            if self.over[1] is not None:
                w = T('white') if self.over[1] == WHITE else T('black')
                status = fa(f"{w} {T('wins')}")
                col = ACCENT
            elif self.over[0] == 'stalemate':
                status, col = fa(T('stalemate')), DIM
            else:
                status, col = fa(T('material')), DIM
        surf = self.fonts['text'].render(status, True, col)
        scr.blit(surf, surf.get_rect(centerx=SIDE_X + SIDE_W // 2, top=y))
        if self.flash is not None:
            text, until = self.flash
            if pygame.time.get_ticks() < until:
                fsurf = self.fonts['small'].render(fa(text), True, GOLD)
                scr.blit(fsurf, fsurf.get_rect(centerx=SIDE_X + SIDE_W // 2,
                                               top=y + 26))
            else:
                self.flash = None
        y += 34
        # mode info
        info = f"Random Chess — {T('computername')} ({T(self.cfg['difficulty'])})" \
            if self.cfg['mode'] == 'random' and self.ai_color is not None else \
            (f"Random Chess — {T('twoplayer')}" if self.cfg['mode'] == 'random'
             else f"{T('classic')} — {T('computername')} ({T(self.cfg['difficulty'])})"
             if self.ai_color is not None else f"{T('classic')} — {T('twoplayer')}")
        isurf = self.fonts['small'].render(fa(info), True, DIM)
        scr.blit(isurf, isurf.get_rect(centerx=SIDE_X + SIDE_W // 2, top=y))
        y += 30

        if self.cfg['mode'] == 'random' and self.board is not None:
            y = self.draw_pattern_table(y)

        y += 8
        y = self.sidebar_button(y, 'undo', 'undo')
        y = self.sidebar_button(y, 'resign', 'resign')
        y = self.sidebar_button(y, 'rematch', 'rematch')
        y = self.sidebar_button(y, 'menu', 'menu')

    def draw_pattern_table(self, y):
        """Sidebar list: which back-rank piece moves like what (Random Chess)."""
        scr = self.screen
        head = self.fonts['small'].render(fa(T('patterns')), True, GOLD)
        scr.blit(head, head.get_rect(centerx=SIDE_X + SIDE_W // 2, top=y))
        y += 24
        row_h = 27
        board = self.board
        rows = []
        for f in (0, 1, 2, 3, 5, 6, 7):
            # pattern_map survives captures; a piece may be gone from the board
            pat = board.pattern_map.get(f)
            rows.append((FILES[f], BACK_RANK[f], pat if pat is not None else BACK_RANK[f]))
        for i, (letter, kind, pat) in enumerate(rows):
            ry = y + i * row_h
            if i % 2 == 0:
                pygame.draw.rect(scr, PANEL,
                                 (SIDE_X, ry - 3, SIDE_W, row_h), border_radius=6)
            cy = ry + row_h // 2 - 3
            # right: file letter + piece glyph (what it looks like)
            lt = self.fonts['small'].render(letter, True, DIM)
            scr.blit(lt, (SIDE_X + SIDE_W - 16 - lt.get_width(), ry + 2))
            kgl = self.glyph_surface(GLYPH[kind], 'glyph_mid', TEXT if kind else TEXT)
            scr.blit(kgl, kgl.get_rect(right=SIDE_X + SIDE_W - 34, centery=cy))
            # middle: "مثل"
            like = self.fonts['small'].render(fa(T('like')), True, DIM)
            scr.blit(like, like.get_rect(centerx=SIDE_X + SIDE_W // 2, centery=cy))
            # left: pattern glyph (how it really moves)
            pgl = self.glyph_surface(GLYPH[pat], 'glyph_mid', ACCENT)
            scr.blit(pgl, pgl.get_rect(left=SIDE_X + 24, centery=cy))
        y += len(rows) * row_h + 6
        note = self.fonts['small'].render(fa(T('pawnsnormal')), True, DIM)
        scr.blit(note, note.get_rect(centerx=SIDE_X + SIDE_W // 2, top=y))
        return y + 24

    # ------------------------------------------------------------ dialogs

    def draw_promo_dialog(self):
        scr = self.screen
        veil = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        veil.fill((15, 12, 10, 170))
        scr.blit(veil, (0, 0))
        panel = pygame.Rect(0, 0, 420, 200)
        panel.center = (WIN_W // 2, WIN_H // 2)
        pygame.draw.rect(scr, PANEL, panel, border_radius=14)
        pygame.draw.rect(scr, GOLD, panel, 2, border_radius=14)
        title = self.fonts['text'].render(fa(T('promotitle')), True, TEXT)
        scr.blit(title, title.get_rect(centerx=panel.centerx, top=panel.top + 18))
        order = [QUEEN, ROOK, BISHOP, KNIGHT]
        size = 72
        gap = 14
        total = size * 4 + gap * 3
        x0 = panel.centerx - total // 2
        color = self.board.turn
        for i, kind in enumerate(order):
            rect = pygame.Rect(x0 + i * (size + gap), panel.top + 62, size, size)
            pygame.draw.rect(scr, PANEL_HI, rect, border_radius=10)
            glyph = self.piece_surface(GLYPH[kind], PIECE_FILL[color], PIECE_OUTLINE[color])
            small = pygame.transform.smoothscale(glyph, (size - 22, size - 22))
            scr.blit(small, small.get_rect(center=rect.center))
            self.buttons.append(Button(rect, 'promo', kind))

    def draw_over_dialog(self):
        scr = self.screen
        key, winner = self.over
        if key == 'mate':
            big = fa(T('mate'))
        elif key == 'timeout':
            big = fa(T('timeout'))
        elif key == 'resign':
            big = fa(T('resigned'))
        elif key == 'stalemate':
            big = fa(T('stalemate'))
        else:
            big = fa(T('material'))
        sub = ''
        if winner is not None:
            w = T('white') if winner == WHITE else T('black')
            sub = fa(f"{w} {T('wins')}")
        elif key == 'mate':
            pass
        veil = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        veil.fill((15, 12, 10, 170))
        scr.blit(veil, (0, 0))
        panel = pygame.Rect(0, 0, 480, 230)
        panel.center = (WIN_W // 2, WIN_H // 2)
        pygame.draw.rect(scr, PANEL, panel, border_radius=14)
        pygame.draw.rect(scr, GOLD, panel, 2, border_radius=14)
        surf = self.fonts['title'].render(big, True, GOLD)
        scr.blit(surf, surf.get_rect(centerx=panel.centerx, top=panel.top + 26))
        if sub:
            s2 = self.fonts['big'].render(sub, True, TEXT)
            scr.blit(s2, s2.get_rect(centerx=panel.centerx, top=panel.top + 92))
        w, h = 190, 48
        y = panel.bottom - 70
        r1 = pygame.Rect(panel.centerx - w - 10, y, w, h)
        r2 = pygame.Rect(panel.centerx + 10, y, w, h)
        for rect, tkey, kind, col in ((r1, 'rematch', 'rematch', ACCENT),
                                      (r2, 'menu', 'menu', PANEL_HI)):
            pygame.draw.rect(scr, col, rect, border_radius=10)
            tsurf = self.fonts['text'].render(fa(T(tkey)), True, TEXT)
            scr.blit(tsurf, tsurf.get_rect(center=rect.center))
            self.buttons.append(Button(rect, kind))

    def draw_game(self):
        self.draw_board()
        self.draw_sidebar()

    # ------------------------------------------------------------ screenshot helper

    def screenshot(self, path):
        pygame.image.save(self.screen, path)


def run():
    App().run()


if __name__ == '__main__':
    run()
