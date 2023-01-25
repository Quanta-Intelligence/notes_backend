from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import pinecone
import random
import json
from functools import reduce
import math

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pinecone.init(api_key='06bb24b7-2061-460e-9ba6-c9f8dfbbb736', environment='us-west1-gcp')
index = pinecone.Index('nodes')

def get_raw_content(node) -> str:
    content = ''
    if not node.get('content'):
        return content
    for n in node.get('content'):
        if n.get('text'):
            content = content + n.get('text')
    return content

def embed_nodes(nodes, dim=16) -> tuple[list[float], list[float]]:
    embeddings = []
    magnitudes = []
    for node in nodes:
        embedding = [random.uniform(0, 1) for i in range(dim)]
        magnitude = math.sqrt(reduce(lambda x, y: x + y * y, embedding))
        new_magnitude = 0.4 if node[0].get('type') == 'title' else 0.8
        embedding = list(map(lambda x: x * new_magnitude / magnitude, embedding))
        magnitudes.append(new_magnitude)
        embeddings.append(embedding)
    return embeddings, magnitudes

def store_nodes(nodes) -> None:
    nodes.reverse()
    embeddings, magnitudes = embed_nodes(nodes)
    index.upsert([(
        nodes[i][0].get('attrs').get('id'),
        embeddings[i],
        {
            'name': get_raw_content(nodes[i][0]),
            'magnitude': magnitudes[i],
            'data': json.dumps(nodes[i])
        }
    ) for i in range(len(nodes))])

def fetch_node(id: str) -> dict:
    content = json.loads(index.fetch(ids=[id]).get('vectors').get(id).get('metadata').get('data'))
    for i, c in enumerate(content):
        if c.get('type') == 'node':
            content[i] = fetch_node(c.get('id'))
    return content

def flatten_nodes(nodes, level=6, result=[]) -> list[dict]:
    start = None
    node_content = []
    to_slice = []
    if level == 0:
        return result + [nodes]
    for i, n in enumerate(nodes):
        if start and n.get('type') != 'heading':
            node_content.append(n)
        if start is not None and (n.get('type') == 'heading' or i == len(nodes) - 1):
            result.append([nodes[start]] + node_content)
            to_slice.extend(node_content)
            node_content.clear()
            nodes[start] = {'type': 'node', 'name': get_raw_content(
                nodes[start]), 'id': nodes[start].get('attrs').get('id')}
        if n.get('type') == 'heading' and n.get('attrs').get('level') == level:
            start = i
        elif n.get('type') == 'heading':
            start = None
    nodes = list(filter(lambda n: n not in to_slice, nodes))
    return flatten_nodes(nodes, level - 1, result)

def clear_database():
    index.delete(delete_all=True)

@ app.post('/node')
async def save_nodes(request: Request) -> None:
    data = await request.json()
    store_nodes(flatten_nodes(data['content']))

@ app.get('/node/{id}')
async def load_node(id: str, request: Request) -> dict:
    return fetch_node(id)

@ app.get('/children/{id}')
async def children(id: str, request: Request) -> dict:
    result = {'matches': []}
    if id == 'root':
        result = index.query(
            vector=[0.1 for i in range(16)],
            top_k=50,
            filter={
                'magnitude': {'$lt': 0.5}
            },
            include_metadata=True
        ).to_dict()
    return result

if __name__ == '__main__':
    clear_database()
    uvicorn.run('main:app', host='127.0.0.1', port=8080, reload=True)
