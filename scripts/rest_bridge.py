from fastapi import FastAPI, Request
from openmock import FakeOpenSearch
import uvicorn
import json

app = FastAPI(title="Openmock REST Bridge")
es = FakeOpenSearch()

@app.get("/")
def info():
    return es.info()

@app.get("/_cluster/health")
def health():
    return es.cluster.health()

@app.post("/{index}/_doc")
@app.post("/{index}/_create")
async def index_doc(index: str, request: Request):
    body = await request.json()
    return es.index(index=index, body=body)

@app.api_route("/{index}/_search", methods=["GET", "POST"])
async def search(index: str, request: Request):
    try:
        body = await request.json()
    except:
        body = {"query": {"match_all": {}}}
    return es.search(index=index, body=body)

@app.get("/{index}/_count")
async def count(index: str, request: Request):
    try:
        body = await request.json()
    except:
        body = None
    return es.count(index=index, body=body)

if __name__ == "__main__":
    print("Openmock REST Bridge running on http://localhost:9201")
    print("This allows non-python tools to talk to the fake.")
    uvicorn.run(app, host="0.0.0.0", port=9201)
