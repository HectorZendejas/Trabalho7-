"""
search.py — Implementação dos 4 algoritmos de busca P2P.

Cada algoritmo retorna um SearchResult com:
  - encontrado: bool
  - no_encontrado: str | None
  - mensagens: int  (total de mensagens trocadas)
  - nos_envolvidos: set[str]
  - log: list[str]  (passo a passo opcional)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from node import Node


@dataclass
class SearchResult:
    encontrado: bool = False
    no_encontrado: str | None = None
    mensagens: int = 0
    nos_envolvidos: set[str] = field(default_factory=set)
    log: list[str] = field(default_factory=list)


# ------------------------------------------------------------------
# Flooding
# ------------------------------------------------------------------

def flooding(
    no_origem: Node,
    recurso_id: str,
    ttl: int,
    verbose: bool = False,
) -> SearchResult:
    """
    Envia a consulta para TODOS os vizinhos recursivamente até TTL=0.
    Não para ao encontrar: explora todos os caminhos possíveis dentro do TTL
    e registra o primeiro nó que possui o recurso. Isso reflete o comportamento
    real do flooding, onde o iniciador não sabe antecipadamente onde o recurso está.
    """
    resultado = SearchResult()
    visitados: set[str] = set()

    def _buscar(no: Node, ttl_atual: int) -> None:
        if no.id in visitados:
            return
        visitados.add(no.id)
        resultado.nos_envolvidos.add(no.id)
        resultado.mensagens += 1

        if verbose:
            resultado.log.append(
                f"[flooding] {no.id} recebeu busca por '{recurso_id}' (TTL={ttl_atual})"
            )

        # Registra o primeiro encontrado, mas continua explorando
        if no.tem_recurso(recurso_id) and not resultado.encontrado:
            resultado.encontrado = True
            resultado.no_encontrado = no.id
            if verbose:
                resultado.log.append(f"  -> ENCONTRADO em {no.id}!")

        if ttl_atual <= 0:
            return

        for viz in no.vizinhos:
            _buscar(viz, ttl_atual - 1)

    _buscar(no_origem, ttl)
    return resultado


# ------------------------------------------------------------------
# Informed Flooding
# ------------------------------------------------------------------

def informed_flooding(
    no_origem: Node,
    recurso_id: str,
    ttl: int,
    verbose: bool = False,
) -> SearchResult:
    """
    Igual ao flooding, mas cada nó consulta seu cache antes de propagar.
    Se o recurso está em cache, responde diretamente sem continuar a busca.
    Ao encontrar o recurso, todos os nós no caminho atualizam seu cache.
    """
    resultado = SearchResult()
    visitados: set[str] = set()

    def _buscar(no: Node, ttl_atual: int, remetente_id: str | None) -> bool:
        if no.id in visitados:
            return False
        visitados.add(no.id)
        resultado.nos_envolvidos.add(no.id)
        resultado.mensagens += 1

        if verbose:
            resultado.log.append(
                f"[informed_flooding] {no.id} recebeu busca por '{recurso_id}' (TTL={ttl_atual})"
            )

        # Verifica cache local primeiro
        cached = no.consultar_cache(recurso_id)
        if cached:
            resultado.encontrado = True
            resultado.no_encontrado = next(iter(cached))
            if verbose:
                resultado.log.append(
                    f"  -> Cache HIT em {no.id}: recurso está em {resultado.no_encontrado}"
                )
            return True

        if no.tem_recurso(recurso_id):
            resultado.encontrado = True
            resultado.no_encontrado = no.id
            no.atualizar_cache(recurso_id, no.id)
            if verbose:
                resultado.log.append(f"  -> ENCONTRADO em {no.id}!")
            return True

        if ttl_atual <= 0:
            return False

        for viz in no.vizinhos:
            if viz.id != remetente_id and viz.id not in visitados:
                encontrou = _buscar(viz, ttl_atual - 1, no.id)
                if encontrou:
                    # Propaga o conhecimento de volta pelo caminho
                    if resultado.no_encontrado:
                        no.atualizar_cache(recurso_id, resultado.no_encontrado)
                    return True
        return False

    _buscar(no_origem, ttl, None)
    return resultado


# ------------------------------------------------------------------
# Random Walk
# ------------------------------------------------------------------

def random_walk(
    no_origem: Node,
    recurso_id: str,
    ttl: int,
    verbose: bool = False,
) -> SearchResult:
    """
    Encaminha a busca para apenas UM vizinho aleatório por salto.
    Continua até TTL=0 ou até encontrar o recurso.
    """
    resultado = SearchResult()
    no_atual = no_origem
    no_anterior_id: str | None = None

    for salto in range(ttl + 1):
        resultado.nos_envolvidos.add(no_atual.id)
        resultado.mensagens += 1

        if verbose:
            resultado.log.append(
                f"[random_walk] salto {salto}: {no_atual.id} "
                f"verifica '{recurso_id}' (TTL restante={ttl - salto})"
            )

        if no_atual.tem_recurso(recurso_id):
            resultado.encontrado = True
            resultado.no_encontrado = no_atual.id
            if verbose:
                resultado.log.append(f"  -> ENCONTRADO em {no_atual.id}!")
            return resultado

        if salto == ttl:
            break

        # Escolhe próximo vizinho (evitando voltar ao anterior, se possível)
        candidatos = [v for v in no_atual.vizinhos if v.id != no_anterior_id]
        if not candidatos:
            candidatos = no_atual.vizinhos
        if not candidatos:
            break

        proximo = random.choice(candidatos)
        no_anterior_id = no_atual.id
        no_atual = proximo

    return resultado


# ------------------------------------------------------------------
# Informed Random Walk
# ------------------------------------------------------------------

def informed_random_walk(
    no_origem: Node,
    recurso_id: str,
    ttl: int,
    verbose: bool = False,
) -> SearchResult:
    """
    Random walk com suporte a cache local.
    Se o nó atual tem o recurso em cache, responde sem propagar.
    Ao encontrar, atualiza o cache dos nós visitados.
    """
    resultado = SearchResult()
    no_atual = no_origem
    no_anterior_id: str | None = None
    caminho: list[Node] = []

    for salto in range(ttl + 1):
        resultado.nos_envolvidos.add(no_atual.id)
        resultado.mensagens += 1
        caminho.append(no_atual)

        if verbose:
            resultado.log.append(
                f"[informed_random_walk] salto {salto}: {no_atual.id} "
                f"verifica '{recurso_id}' (TTL restante={ttl - salto})"
            )

        # Verifica cache local
        cached = no_atual.consultar_cache(recurso_id)
        if cached:
            resultado.encontrado = True
            resultado.no_encontrado = next(iter(cached))
            if verbose:
                resultado.log.append(
                    f"  -> Cache HIT em {no_atual.id}: recurso está em {resultado.no_encontrado}"
                )
            _atualizar_caminho(caminho, recurso_id, resultado.no_encontrado)
            return resultado

        if no_atual.tem_recurso(recurso_id):
            resultado.encontrado = True
            resultado.no_encontrado = no_atual.id
            if verbose:
                resultado.log.append(f"  -> ENCONTRADO em {no_atual.id}!")
            _atualizar_caminho(caminho, recurso_id, no_atual.id)
            return resultado

        if salto == ttl:
            break

        candidatos = [v for v in no_atual.vizinhos if v.id != no_anterior_id]
        if not candidatos:
            candidatos = no_atual.vizinhos
        if not candidatos:
            break

        proximo = random.choice(candidatos)
        no_anterior_id = no_atual.id
        no_atual = proximo

    return resultado


def _atualizar_caminho(caminho: list[Node], recurso_id: str, no_dono: str) -> None:
    """Atualiza o cache de todos os nós no caminho percorrido."""
    for no in caminho:
        no.atualizar_cache(recurso_id, no_dono)


# ------------------------------------------------------------------
# Dispatcher
# ------------------------------------------------------------------

ALGORITMOS = {
    "flooding": flooding,
    "informed_flooding": informed_flooding,
    "random_walk": random_walk,
    "informed_random_walk": informed_random_walk,
}


def executar_busca(
    no_origem: Node,
    recurso_id: str,
    ttl: int,
    algo: str,
    verbose: bool = False,
) -> SearchResult:
    """Executa o algoritmo especificado e retorna o resultado."""
    if algo not in ALGORITMOS:
        raise ValueError(
            f"Algoritmo '{algo}' desconhecido. "
            f"Opções: {list(ALGORITMOS.keys())}"
        )
    return ALGORITMOS[algo](no_origem, recurso_id, ttl, verbose)
