from datetime import date

from owemygod.prompt import READER_SYSTEM, build_reader_messages, render_qwen3_prompt


def test_user_content_format():
    m = build_reader_messages("abis gajian ya", date(2026, 10, 23))
    assert m == [{"role": "system", "content": READER_SYSTEM},
                 {"role": "user", "content": "Today: Friday, 2026-10-23\nReply: abis gajian ya"}]


def test_render_disables_thinking():
    s = render_qwen3_prompt(build_reader_messages("besok", date(2026, 10, 23)))
    assert s.startswith("<|im_start|>system\n") and s.endswith("<|im_start|>assistant\n<think>\n\n</think>\n\n")


def test_system_lists_every_type():
    from owemygod.schema import WHEN_TYPES
    assert all(t in READER_SYSTEM for t in WHEN_TYPES)
