from aprp_scanner import vdf
from aprp_scanner.epic import _clean_title, launch_uri

LIBRARY = r'''
"libraryfolders"
{
    "0"
    {
        "path"      "C:\\Program Files (x86)\\Steam"
        "apps"      { "570" "123" }
    }
    "1"   "D:\\OldStyleLibrary"
}
'''


def test_nested_and_escaped():
    data = vdf.loads(LIBRARY)["libraryfolders"]
    assert data["0"]["path"] == r"C:\Program Files (x86)\Steam"
    assert data["0"]["apps"] == {"570": "123"}
    assert data["1"] == r"D:\OldStyleLibrary"


def test_keys_are_case_insensitive():
    assert vdf.loads('"AppState" { "StateFlags" "4" }') == {"appstate": {"stateflags": "4"}}


def test_epic_title_cleanup():
    assert _clean_title("Rocket League?") == "Rocket League"
    assert _clean_title("Who Wants To Be A Millionaire ?") == "Who Wants To Be A Millionaire ?"


def test_epic_uri_is_encoded():
    assert launch_uri("ns", "id", "App") == "com.epicgames.launcher://apps/ns%3Aid%3AApp?action=launch&silent=true"
