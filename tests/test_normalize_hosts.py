from openmock.normalize_hosts import _normalize_hosts


def test_normalize_hosts_none():
    assert _normalize_hosts(None) == [{}]


def test_normalize_hosts_string():
    assert _normalize_hosts("localhost") == [{"host": "localhost"}]


def test_normalize_hosts_list_of_strings():
    assert _normalize_hosts(["localhost", "otherhost:9201"]) == [
        {"host": "localhost"},
        {"host": "otherhost", "port": 9201},
    ]


def test_normalize_hosts_with_protocol():
    assert _normalize_hosts("http://localhost:9200") == [
        {"host": "localhost", "port": 9200}
    ]


def test_normalize_hosts_https():
    assert _normalize_hosts("https://localhost") == [
        {"host": "localhost", "port": 443, "use_ssl": True}
    ]


def test_normalize_hosts_https_custom_port():
    assert _normalize_hosts("https://localhost:8443") == [
        {"host": "localhost", "port": 8443, "use_ssl": True}
    ]


def test_normalize_hosts_auth():
    assert _normalize_hosts("http://user:pass@localhost:9200") == [
        {"host": "localhost", "port": 9200, "http_auth": "user:pass"}
    ]


def test_normalize_hosts_path():
    assert _normalize_hosts("http://localhost:9200/path") == [
        {"host": "localhost", "port": 9200, "url_prefix": "/path"}
    ]


def test_normalize_hosts_dict():
    host_dict = {"host": "localhost", "port": 9200}
    assert _normalize_hosts([host_dict]) == [host_dict]


def test_normalize_hosts_complex():
    hosts = [
        "localhost",
        "https://user:pass@remote:443/api",
        {"host": "proxy", "port": 8080},
    ]
    expected = [
        {"host": "localhost"},
        {
            "host": "remote",
            "port": 443,
            "use_ssl": True,
            "http_auth": "user:pass",
            "url_prefix": "/api",
        },
        {"host": "proxy", "port": 8080},
    ]
    assert _normalize_hosts(hosts) == expected
