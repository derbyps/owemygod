import pytest

from owemygod.schema import ParseError, ReplyRead, parse_reply, to_target_json


def test_parse_strips_think_and_prose():
    r = parse_reply('<think>\n</think>\nSure: {"kind":"promise","when":{"type":"payday"}} ok')
    assert r.kind == "promise" and r.when.type == "payday"


def test_promise_requires_when():
    with pytest.raises(ParseError):
        parse_reply('{"kind":"promise"}')


def test_vague_rejects_when():
    with pytest.raises(ParseError):
        parse_reply('{"kind":"vague","when":{"type":"payday"}}')


def test_unknown_type_rejected():
    with pytest.raises(ParseError):
        parse_reply('{"kind":"promise","when":{"type":"lebaran"}}')


def test_no_json():
    with pytest.raises(ParseError):
        parse_reply("nope")


def test_roundtrip():
    assert to_target_json(ReplyRead(kind="vague")) == '{"kind":"vague"}'
    s = '{"kind":"promise","when":{"type":"relative_days","n":1}}'
    assert to_target_json(parse_reply(s)) == s
