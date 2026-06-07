"""
node.py — Representa um nó individual na rede P2P.
Cada nó conhece seus vizinhos, seus recursos e mantém um cache local
de localizações conhecidas de recursos (usado pelos algoritmos informados).
"""


class Node:
    def __init__(self, node_id: str):
        self.id = node_id
        self.recursos: set[str] = set()
        self.vizinhos: list["Node"] = []
        # cache: recurso -> conjunto de nós onde foi visto
        self.cache: dict[str, set[str]] = {}

    def tem_recurso(self, recurso_id: str) -> bool:
        return recurso_id in self.recursos

    def atualizar_cache(self, recurso_id: str, no_origem: str) -> None:
        """Registra no cache que `recurso_id` foi encontrado em `no_origem`."""
        if recurso_id not in self.cache:
            self.cache[recurso_id] = set()
        self.cache[recurso_id].add(no_origem)

    def consultar_cache(self, recurso_id: str) -> set[str] | None:
        """Retorna os nós conhecidos para o recurso, ou None se não estiver em cache."""
        return self.cache.get(recurso_id)

    def __repr__(self) -> str:
        return f"Node({self.id})"
