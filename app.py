"""
app.py — Servidor web do simulador de busca P2P.

Instalar dependência:
    pip install flask

Uso:
    python app.py --config config.yaml [--porta 5000]

Depois abra http://localhost:5000 no navegador.
"""

import argparse
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from flask import Flask, jsonify, request, render_template
from network import Network
from search import executar_busca, validar_com_vizinhos, ALGORITMOS, MODOS

app = Flask(__name__)
_rede: Network = None  # type: ignore


def _serializar_rede() -> dict:
    nos = []
    arestas = []
    vistos: set[tuple] = set()
    for no in _rede.nos.values():
        nos.append({"id": no.id, "recursos": sorted(no.recursos)})
        for viz in no.vizinhos:
            chave = tuple(sorted([no.id, viz.id]))
            if chave not in vistos:
                vistos.add(chave)
                arestas.append({"from": no.id, "to": viz.id})
    return {"nos": nos, "arestas": arestas}


@app.route("/")
def index():
    nos_ids = sorted(_rede.nos.keys())
    todos_recursos = sorted({r for no in _rede.nos.values() for r in no.recursos})
    return render_template(
        "index.html",
        nos=nos_ids,
        recursos=todos_recursos,
        algoritmos=list(ALGORITMOS.keys()),
        modos=list(MODOS),
    )


@app.route("/api/rede")
def api_rede():
    return jsonify(_serializar_rede())


@app.route("/api/buscar", methods=["POST"])
def api_buscar():
    data = request.get_json(force=True)
    no_id = data.get("no_id", "")
    recurso_id = data.get("recurso_id", "")
    ttl = max(1, int(data.get("ttl", 5)))
    algo = data.get("algo", "flooding")
    modo = data.get("modo", "normal")
    num_caminhos = max(1, int(data.get("num_caminhos", 3)))
    fazer_validar = bool(data.get("validar", False))

    try:
        no_origem = _rede.obter_no(no_id)
    except KeyError:
        return jsonify({"erro": f"Nó '{no_id}' não encontrado"}), 400

    if algo not in ALGORITMOS:
        return jsonify({"erro": f"Algoritmo '{algo}' inválido"}), 400

    resultado = executar_busca(
        no_origem=no_origem,
        recurso_id=recurso_id,
        ttl=ttl,
        algo=algo,
        verbose=True,
        modo=modo,
        num_caminhos=num_caminhos,
    )

    validacao = None
    if fazer_validar and resultado.encontrado and resultado.no_encontrado:
        no_enc = _rede.nos.get(resultado.no_encontrado)
        if no_enc:
            validacao = validar_com_vizinhos(no_enc, recurso_id)

    return jsonify({
        "encontrado": resultado.encontrado,
        "no_encontrado": resultado.no_encontrado,
        "mensagens": resultado.mensagens,
        "nos_envolvidos": sorted(resultado.nos_envolvidos),
        "caminho": resultado.caminho,
        "mensagens_log": [list(m) for m in resultado.mensagens_log],
        "log": resultado.log,
        "validacao": validacao,
    })


@app.route("/api/consultar/<recurso_id>")
def api_consultar(recurso_id: str):
    nos = [no.id for no in _rede.nos.values() if no.tem_recurso(recurso_id)]
    return jsonify({"recurso": recurso_id, "nos": nos})


def main():
    parser = argparse.ArgumentParser(description="Interface web do simulador P2P")
    parser.add_argument("--config", required=True, help="Caminho para config.yaml")
    parser.add_argument("--porta", type=int, default=5000, help="Porta HTTP (padrão 5000)")
    args = parser.parse_args()

    global _rede
    print(f"Carregando rede de '{args.config}'...")
    try:
        _rede = Network.carregar(args.config)
    except (ValueError, FileNotFoundError) as e:
        print(f"Erro ao carregar rede: {e}")
        sys.exit(1)

    print(f"Rede carregada: {len(_rede.nos)} nós.")
    print(f"Acesse http://localhost:{args.porta} no navegador.\n")
    app.run(debug=False, port=args.porta)


if __name__ == "__main__":
    main()
