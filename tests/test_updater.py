"""① 단위 테스트 — 자동 업데이트 순수 로직 (core/updater.py).

네트워크는 get_latest 를 monkeypatch 로 대체해 접속하지 않는다.
"""
import pytest

from core import updater as up


@pytest.mark.parametrize(
    "s,expected",
    [
        ("v1.2.3", (1, 2, 3)),
        ("0.0.1", (0, 0, 1)),
        ("v2.0", (2, 0, 0)),
        ("1.4.2-beta", (1, 4, 2)),
        ("", (0, 0, 0)),
    ],
)
def test_parse_version(s, expected):
    assert up._parse_version(s) == expected


def test_build_kind_dev():
    # 소스 실행(비프리즈)에서는 dev
    assert up.build_kind() == "dev"


def test_extract_summary_with_markers():
    body = "머리말\n<!--CHANGES-->\n- 새 기능\n- 버그 수정\n<!--/CHANGES-->\n꼬리말"
    assert up.extract_summary(body) == "- 새 기능\n- 버그 수정"


def test_extract_summary_without_markers():
    assert up.extract_summary("첫 줄\n\n둘째 줄", max_lines=1) == "첫 줄"
    assert up.extract_summary("") == "(변경 내용 정보 없음)"


def test_asset_url_selects_by_kind():
    latest = {
        "assets": {
            "FormatConverter-full-0.0.2.zip": "http://x/full.zip",
            "FormatConverter-lite-0.0.2.zip": "http://x/lite.zip",
        }
    }
    assert up._asset_url(latest, "full") == ("FormatConverter-full-0.0.2.zip", "http://x/full.zip")
    assert up._asset_url(latest, "lite") == ("FormatConverter-lite-0.0.2.zip", "http://x/lite.zip")
    assert up._asset_url({"assets": {}}, "full") == (None, None)


def test_check_update_newer(monkeypatch):
    monkeypatch.setattr(up, "get_latest", lambda: {"tag": "v0.0.2", "body": "b", "assets": {}, "html_url": ""})
    assert up.check_update("0.0.1")["tag"] == "v0.0.2"


def test_check_update_same_or_older(monkeypatch):
    monkeypatch.setattr(up, "get_latest", lambda: {"tag": "v0.0.1", "body": "", "assets": {}, "html_url": ""})
    assert up.check_update("0.0.1") is None
    monkeypatch.setattr(up, "get_latest", lambda: {"tag": "v0.0.1", "body": "", "assets": {}, "html_url": ""})
    assert up.check_update("1.0.0") is None


def test_check_update_empty_tag(monkeypatch):
    monkeypatch.setattr(up, "get_latest", lambda: {"tag": "", "body": "", "assets": {}, "html_url": ""})
    assert up.check_update("0.0.1") is None


def test_apply_dev_raises():
    with pytest.raises(RuntimeError):
        up.download_and_apply({"assets": {}}, "dev")


def test_ps_literal_escapes_quotes():
    assert up._ps_literal("a'b") == "'a''b'"
