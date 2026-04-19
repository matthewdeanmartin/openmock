import opensearchpy
from openmock import openmock

@openmock
def test_fail_fast():
    client = opensearchpy.OpenSearch(hosts=[{"host": "localhost", "port": 9200}])
    print("Calling unmocked field_caps...")
    try:
        client.field_caps(index="test-index", fields="*")
        print("Success (unexpected!)")
    except Exception as e:
        print(f"Caught expected exception: {e}")
        assert "Attempted to connect to real OpenSearch server" in str(e)

if __name__ == "__main__":
    test_fail_fast()
