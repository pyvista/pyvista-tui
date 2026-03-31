from __future__ import annotations

from pyvista_tui.terminal._detect import _parse_osc11_response


def test_parse_osc11_valid_st_response():
    seq = '\x1b]11;rgb:1e1e/1e1e/1e1e\x1b\\'
    result = _parse_osc11_response(seq, '\x1b\\')
    assert result == '#1e1e1e'


def test_parse_osc11_valid_bel_response():
    seq = '\x1b]11;rgb:ffff/0000/0000\a'
    result = _parse_osc11_response(seq, '\a')
    assert result == '#ff0000'


def test_parse_osc11_invalid_prefix():
    result = _parse_osc11_response('garbage', '\x1b\\')
    assert result is None


def test_parse_osc11_wrong_part_count():
    seq = '\x1b]11;rgb:ff/ff\x1b\\'
    result = _parse_osc11_response(seq, '\x1b\\')
    assert result is None


def test_parse_osc11_black():
    seq = '\x1b]11;rgb:0000/0000/0000\x1b\\'
    result = _parse_osc11_response(seq, '\x1b\\')
    assert result == '#000000'


def test_parse_osc11_white():
    seq = '\x1b]11;rgb:ffff/ffff/ffff\x1b\\'
    result = _parse_osc11_response(seq, '\x1b\\')
    assert result == '#ffffff'
