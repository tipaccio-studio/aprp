from urllib.parse import quote

from aprp_scanner.modrinth import _URL_PATH_SAFE, _description


def test_launch_id_encoding_matches_url_crate():
    iid = "legacy:Timeless [UPDATE SOON!] #2/x"
    assert quote(iid, safe=_URL_PATH_SAFE) == "legacy:Timeless%20[UPDATE%20SOON!]%20%232%2Fx"


def test_description():
    assert _description("1.20.1", "forge", "47.4.10", 0) == "Minecraft 1.20.1 · Forge 47.4.10"
    assert _description("1.21", "vanilla", None, 0) == "Minecraft 1.21"
