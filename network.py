"""
network.py — Carrega a configuração YAML, constrói o grafo e executa validações.
"""

from __future__ import annotations

import yaml
from collections import deque
from node import Node


class Network:
    def __init__(self):
        self.nos: dict[str, Node] = {}
        self.min_vizinhos: int = 0
        self.max_vizinhos: int = 0

    # ------------------------------------------------------------------
    # Carregamento
    # ------------------------------------------------------------------

    @classmethod
    def carregar(cls, caminho: str) -> "Network":
        """Lê o arquivo YAML e retorna uma Network validada."""
        with open(caminho, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        rede = cls()
        rede.min_vizinhos = cfg.get("min_neighbors", 1)
        rede.max_vizinhos = cfg.get("max_neighbors", 10)
        num_nos = cfg.get("num_nodes", 0)

        # Criar nós
        recursos_cfg = cfg.get("resources", {})
        arestas_cfg = cfg.get("edges", [])

        # Garante que todos os nós mencionados em arestas existam
        nos_mencionados: set[str] = set()
        for no_id, lista_rec in recursos_cfg.items():
            nos_mencionados.add(no_id.strip())

        if isinstance(arestas_cfg, list):
            for aresta in arestas_cfg:
                partes = [p.strip() for p in str(aresta).split(",")]
                nos_mencionados.update(partes)
        elif isinstance(arestas_cfg, str):
            for linha in arestas_cfg.strip().splitlines():
                partes = [p.strip() for p in linha.split(",")]
                nos_mencionados.update(partes)

        for no_id in nos_mencionados:
            if no_id:
                rede.nos[no_id] = Node(no_id)

        # Atribuir recursos
        for no_id, lista_rec in recursos_cfg.items():
            no_id = no_id.strip()
            if no_id not in rede.nos:
                rede.nos[no_id] = Node(no_id)
            if isinstance(lista_rec, str):
                for r in lista_rec.split(","):
                    r = r.strip()
                    if r:
                        rede.nos[no_id].recursos.add(r)
            elif isinstance(lista_rec, list):
                for r in lista_rec:
                    rede.nos[no_id].recursos.add(str(r).strip())

        # Criar arestas (não direcionadas)
        if isinstance(arestas_cfg, list):
            for aresta in arestas_cfg:
                partes = [p.strip() for p in str(aresta).split(",")]
                if len(partes) == 2:
                    rede._adicionar_aresta(partes[0], partes[1])
        elif isinstance(arestas_cfg, str):
            for linha in arestas_cfg.strip().splitlines():
                partes = [p.strip() for p in linha.split(",")]
                if len(partes) == 2:
                    rede._adicionar_aresta(partes[0], partes[1])

        rede.validar()

        # Aviso informativo se num_nodes não bater com o total carregado
        if num_nos and num_nos != len(rede.nos):
            print(
                f"[aviso] num_nodes={num_nos} no YAML, "
                f"mas {len(rede.nos)} nós foram carregados."
            )

        return rede

    def _adicionar_aresta(self, a: str, b: str) -> None:
        if a not in self.nos:
            self.nos[a] = Node(a)
        if b not in self.nos:
            self.nos[b] = Node(b)
        no_a = self.nos[a]
        no_b = self.nos[b]
        if no_b not in no_a.vizinhos:
            no_a.vizinhos.append(no_b)
        if no_a not in no_b.vizinhos:
            no_b.vizinhos.append(no_a)

    # ------------------------------------------------------------------
    # Validações
    # ------------------------------------------------------------------

    def validar(self) -> None:
        """Executa todas as validações; lança ValueError se alguma falhar."""
        self._validar_conectividade()
        self._validar_grau_vizinhos()
        self._validar_recursos()
        self._validar_self_loops()

    def _validar_conectividade(self) -> None:
        """BFS para garantir que a rede não está particionada."""
        if not self.nos:
            return
        visitados: set[str] = set()
        fila = deque([next(iter(self.nos.values()))])
        while fila:
            no = fila.popleft()
            if no.id in visitados:
                continue
            visitados.add(no.id)
            for viz in no.vizinhos:
                if viz.id not in visitados:
                    fila.append(viz)
        if visitados != set(self.nos.keys()):
            particionados = set(self.nos.keys()) - visitados
            raise ValueError(
                f"A rede está particionada. Nós inacessíveis: {particionados}"
            )

    def _validar_grau_vizinhos(self) -> None:
        """Verifica se cada nó respeita min_neighbors e max_neighbors."""
        for no in self.nos.values():
            grau = len(no.vizinhos)
            if grau < self.min_vizinhos:
                raise ValueError(
                    f"Nó '{no.id}' tem {grau} vizinhos, "
                    f"mínimo exigido: {self.min_vizinhos}"
                )
            if grau > self.max_vizinhos:
                raise ValueError(
                    f"Nó '{no.id}' tem {grau} vizinhos, "
                    f"máximo permitido: {self.max_vizinhos}"
                )

    def _validar_recursos(self) -> None:
        """Garante que nenhum nó possui zero recursos."""
        for no in self.nos.values():
            if not no.recursos:
                raise ValueError(
                    f"Nó '{no.id}' não possui nenhum recurso."
                )

    def _validar_self_loops(self) -> None:
        """Garante que não existem arestas de um nó para si mesmo."""
        for no in self.nos.values():
            for viz in no.vizinhos:
                if viz.id == no.id:
                    raise ValueError(
                        f"Nó '{no.id}' possui uma aresta para si mesmo (self-loop)."
                    )

    # ------------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------------

    def obter_no(self, no_id: str) -> Node:
        if no_id not in self.nos:
            raise KeyError(f"Nó '{no_id}' não encontrado na rede.")
        return self.nos[no_id]

    def resumo(self) -> str:
        linhas = [f"Rede com {len(self.nos)} nós:"]
        for no in self.nos.values():
            vizinhos_ids = [v.id for v in no.vizinhos]
            recursos = sorted(no.recursos)
            linhas.append(
                f"  {no.id}: recursos={recursos}, vizinhos={vizinhos_ids}"
            )
        return "\n".join(linhas)
