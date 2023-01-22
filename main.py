from fastapi import FastAPI, Request
import uvicorn
import json

app = FastAPI()

def embed_node(node):
    pass

def store_node(node):
    for n in node: print(n)
    print('////')

def flatten_nodes(nodes, level=6):
    start = None
    node_content = []
    to_slice = []

    if level == 0:
        store_node(nodes)
        return(nodes)
        
    for i, n in enumerate(nodes):
        if start and n.get('type') != 'heading':
            node_content.append(n)
        if start is not None and (n.get('type') == 'heading' or i == len(nodes) - 1):
            store_node([nodes[start]] + node_content)
            to_slice.extend(node_content)
            node_content.clear()
            nodes[start] = {'type': 'node', 'id': nodes[start].get('attrs').get('id')}
        if n.get('type') == 'heading' and n.get('attrs').get('level') == level:
            start = i    
        elif n.get('type') == 'heading':
            start = None

    nodes = list(filter(lambda n: n not in to_slice, nodes))
    flatten_nodes(nodes, level - 1)
    

@app.post('/node')
async def save_nodes(request: Request):
    data = await request.json()
    flatten_nodes(data['content'])

if __name__ == '__main__':
    uvicorn.run('main:app', host='127.0.0.1', port=8080, reload=True)