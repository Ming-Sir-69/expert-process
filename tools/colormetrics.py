#!/usr/bin/env python3
"""颜色的可计算指标：WCAG 对比度、OKLCH、OKLab 色差、红/绿色盲模拟（Machado 2009，严重度 1.0）。

用法：
  python3 tools/colormetrics.py <颜色> <相邻色> [<要避开的颜色>]
      例：python3 tools/colormetrics.py 000000 FFFFFF FF0000
      相邻色写实际挨着的颜色（被框住时写框的颜色，不是底色）。
  python3 tools/colormetrics.py
      不带参数：显示用法。算法来源见仓库ACKNOWLEDGEMENTS.md。"""
import math, colorsys


def h2r(h):
    h = h.lstrip('#'); return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def L(rgb): r, g, b = [lin(c) for c in rgb]; return 0.2126 * r + 0.7152 * g + 0.0722 * b


def cr(a, b):
    la, lb = L(h2r(a)), L(h2r(b)); hi, lo = max(la, lb), min(la, lb); return (hi + .05) / (lo + .05)


def oklch(h):
    r, g, b = [lin(c) for c in h2r(h)]
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = [x ** (1 / 3) for x in (l, m, s)]
    Lk = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s
    a = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s
    bb = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s
    return Lk, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360, a, bb


def dE_ok(x, y):
    a = oklch(x); b = oklch(y); return math.sqrt((a[0] - b[0]) ** 2 + (a[3] - b[3]) ** 2 + (a[4] - b[4]) ** 2) * 100


PROT = [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]]
DEUT = [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]]


def sim(h, M):
    v = [lin(c) for c in h2r(h)]
    o = [max(0, min(1, sum(M[i][j] * v[j] for j in range(3)))) for i in range(3)]
    enc = lambda c: 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return '#' + ''.join(f'{round(enc(c) * 255):02X}' for c in o)


def report(fg, adj, avoid=None):
    fg, adj = '#' + fg.lstrip('#').upper(), '#' + adj.lstrip('#').upper()
    Lk, C, hh, _, _ = oklch(fg)
    line = (f"{fg} L{Lk*100:.0f} C{C:.3f} h{hh:.0f} | 对相邻 {adj} {cr(fg, adj):.2f}:1"
            f"{'  不足 3:1' if cr(fg, adj) < 3 else ''} | 红盲 {cr(sim(fg, PROT), sim(adj, PROT)):.2f} | 绿盲 {cr(sim(fg, DEUT), sim(adj, DEUT)):.2f}")
    if avoid:
        avoid = '#' + avoid.lstrip('#').upper()
        dh = abs(hh - oklch(avoid)[2]); dh = min(dh, 360 - dh)
        line += f" | 与 {avoid} 色差 ΔE {dE_ok(fg, avoid):.1f}、色相差 {dh:.0f}°"
    print(line)


if __name__ == "__main__":
    import argparse
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("foreground", help="前景色，6位十六进制，可带#")
    parser.add_argument("adjacent", help="实际相邻色，6位十六进制，可带#")
    parser.add_argument("avoid", nargs="?", help="可选比较色")
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
    args = parser.parse_args()
    for value in (args.foreground, args.adjacent, args.avoid):
        if value is not None and (len(value.lstrip("#")) != 6 or any(c not in "0123456789abcdefABCDEF" for c in value.lstrip("#"))):
            parser.error("颜色必须为6位十六进制，可带#")
    report(args.foreground, args.adjacent, args.avoid)
