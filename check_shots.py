# -*- coding: utf-8 -*-
"""Pixel-level inspection of the rendered screenshots (visual sanity check)."""

import os

os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame

pygame.init()

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shots')
SQ = 79
BX, BY = 30, 26


def px(path, x, y):
    return pygame.image.load(path).get_at((x, y))


def main():
    for f in sorted(os.listdir(BASE)):
        s = pygame.image.load(os.path.join(BASE, f))
        print(f, s.get_size())

    g = os.path.join(BASE, 'game_classic.png')
    # square a8 (row0,col0) must be LIGHT (238,216,180) ignoring piece pixels:
    print('a8 square (edge, no piece):', px(g, BX + 4, BY + 4))
    print('h1 square (edge):', px(g, BX + 7 * SQ + 4, BY + 7 * SQ + 4))
    # e2->e4 last-move tint should make e4 lighter than a plain dark square:
    e4 = px(g, BX + 4 * SQ + 4, BY + 4 * SQ + 4)
    d4 = px(g, BX + 3 * SQ + 4, BY + 4 * SQ + 4)
    print('e4 (last move, dark sq + tint):', e4, ' d4 (plain dark):', d4)

    # sidebar: clock panel area should differ from background
    print('sidebar panel bg:', px(g, 700, 40))
    print('sidebar bg bottom:', px(g, 700, 660))

    # pieces: center of a1 (white rook) should contain near-white pixels
    center_a1 = px(g, BX + 0 * SQ + SQ // 2, BY + 7 * SQ + SQ // 2)
    print('a1 piece center:', center_a1)
    center_a8 = px(g, BX + 0 * SQ + SQ // 2, BY + 0 * SQ + SQ // 2)
    print('a8 piece center:', center_a8)

    # settings hint line: check for non-background pixels beyond right edge
    st = os.path.join(BASE, 'settings.png')
    print('settings far right (clip zone):', px(st, 995, 660))
    print('settings center bottom (hint):', px(st, 500, 660))

    # random mode: badge = circle at square bottom-right; check badge center of h8 rook
    r = os.path.join(BASE, 'game_random.png')
    badge = px(r, BX + 7 * SQ + SQ - 17, BY + 0 * SQ + SQ - 17)
    print('h8 badge center pixel:', badge)

    # pattern table header area on sidebar (should have gold text pixels)
    scan = pygame.image.load(r)
    found_gold = any(
        scan.get_at((x, y)).r > 150 and scan.get_at((x, y)).g > 110
        and scan.get_at((x, y)).b < 130
        for y in range(230, 480) for x in range(684, 984, 3))
    print('pattern table gold header found:', found_gold)


if __name__ == '__main__':
    main()
