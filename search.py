"""
search.py — Implementação dos algoritmos de busca P2P.

Cada algoritmo retorna um SearchResult com:
  - encontrado: bool
  - no_encontrado: str | None
  - mensagens: int
  - nos_envolvidos: set[str]
  - log: list[str]          (passo a passo)
  - caminho: list[str]      (sequência de nós visitados, em ordem)
  - mensagens_log: list[tuple[str,str,str]]  (de, para, conteúdo)
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
    caminho: list[str] = field(default_factory=list)
    mensagens_log: list[tuple[str, str, str]] = field(default_factory=list)


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
    Registra o primeiro nó que possui o recurso e continua explorando.
    """
    resultado = SearchResult()
    visitados: set[str] = set()

    def _buscar(no: Node, ttl_atual: int, remetente_id: str | None) -> None:
        if no.id in visitados:
            return
        visitados.add(no.id)
        resultado.nos_envolvidos.add(no.id)
        resultado.mensagens += 1
        resultado.caminho.append(no.id)

        if remetente_id:
            resultado.mensagens_log.append(
                (remetente_id, no.id, f"QUERY {recurso_id} TTL={ttl_atual}")
            )

        if verbose:
            resultado.log.append(
                f"[flooding] {no.id} recebeu busca por '{recurso_id}' (TTL={ttl_atual})"
            )

        if no.tem_recurso(recurso_id) and not resultado.encontrado:
            resultado.encontrado = True
            resultado.no_encontrado = no.id
            if remetente_id:
                resultado.mensagens_log.append(
                    (no.id, remetente_id, f"FOUND {recurso_id}")
                )
            if verbose:
                resultado.log.append(f"  -> ENCONTRADO em {no.id}!")

        if ttl_atual <= 0:
            return

        for viz in no.vizinhos:
            _buscar(viz, ttl_atual - 1, no.id)

    _buscar(no_origem, ttl, None)
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
    Se o recurso está em cache, responde diretamente. Atualiza cache ao encontrar.
    """
    resultado = SearchResult()
    visitados: set[str] = set()

    def _buscar(no: Node, ttl_atual: int, remetente_id: str | None) -> bool:
        if no.id in visitados:
            return False
        visitados.add(no.id)
        resultado.nos_envolvidos.add(no.id)
        resultado.mensagens += 1
        resultado.caminho.append(no.id)

        if remetente_id:
            resultado.mensagens_log.append(
                (remetente_id, no.id, f"QUERY {recurso_id} TTL={ttl_atual}")
            )

        if verbose:
            resultado.log.append(
                f"[informed_flooding] {no.id} recebeu busca por '{recurso_id}' (TTL={ttl_atual})"
            )

        cached = no.consultar_cache(recurso_id)
        if cached:
            resultado.encontrado = True
            resultado.no_encontrado = next(iter(cached))
            resultado.mensagens_log.append(
                (no.id, remetente_id or no.id, f"CACHE_HIT {recurso_id}@{resultado.no_encontrado}")
            )
            if verbose:
                resultado.log.append(
                    f"  -> Cache HIT em {no.id}: recurso está em {resultado.no_encontrado}"
                )
            return True

        if no.tem_recurso(recurso_id):
            resultado.encontrado = True
            resultado.no_encontrado = no.id
            no.atualizar_cache(recurso_id, no.id)
            if remetente_id:
                resultado.mensagens_log.append(
                    (no.id, remetente_id, f"FOUND {recurso_id}")
                )
            if verbose:
                resultado.log.append(f"  -> ENCONTRADO em {no.id}!")
            return True

        if ttl_atual <= 0:
            return False

        for viz in no.vizinhos:
            if viz.id != remetente_id and viz.id not in visitados:
                encontrou = _buscar(viz, ttl_atual - 1, no.id)
                if encontrou:
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
        resultado.caminho.append(no_atual.id)

        if salto > 0 and no_anterior_id:
            resultado.mensagens_log.append(
                (no_anterior_id, no_atual.id, f"QUERY {recurso_id} TTL={ttl - salto}")
            )

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
    caminho_nos: list[Node] = []

    for salto in range(ttl + 1):
        resultado.nos_envolvidos.add(no_atual.id)
        resultado.mensagens += 1
        resultado.caminho.append(no_atual.id)
        caminho_nos.append(no_atual)

        if salto > 0 and no_anterior_id:
            resultado.mensagens_log.append(
                (no_anterior_id, no_atual.id, f"QUERY {recurso_id} TTL={ttl - salto}")
            )

        if verbose:
            resultado.log.append(
                f"[informed_random_walk] salto {salto}: {no_atual.id} "
                f"verifica '{recurso_id}' (TTL restante={ttl - salto})"
            )

        cached = no_atual.consultar_cache(recurso_id)
        if cached:
            resultado.encontrado = True
            resultado.no_encontrado = next(iter(cached))
            resultado.mensagens_log.append(
                (no_atual.id, no_anterior_id or no_atual.id,
                 f"CACHE_HIT {recurso_id}@{resultado.no_encontrado}")
            )
            if verbose:
                resultado.log.append(
                    f"  -> Cache HIT em {no_atual.id}: recurso está em {resultado.no_encontrado}"
                )
            _atualizar_caminho(caminho_nos, recurso_id, resultado.no_encontrado)
            return resultado

        if no_atual.tem_recurso(recurso_id):
            resultado.encontrado = True
            resultado.no_encontrado = no_atual.id
            if verbose:
                resultado.log.append(f"  -> ENCONTRADO em {no_atual.id}!")
            _atualizar_caminho(caminho_nos, recurso_id, no_atual.id)
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


# ------------------------------------------------------------------
# Backtracking Walk  (DFS com backtracking)
# ------------------------------------------------------------------

def backtracking_walk(
    no_origem: Node,
    recurso_id: str,
    ttl: int,
    verbose: bool = False,
) -> SearchResult:
    """
    Busca por profundidade com backtracking.
    Quando um caminho falha (TTL esgotado ou sem vizinhos inéditos),
    retorna ao nó anterior e tenta outro vizinho.
    """
    resultado = SearchResult()

    def _dfs(no: Node, ttl_atual: int, caminho_atual: list[str], remetente_id: str | None) -> bool:
        if resultado.encontrado:
            return True

        resultado.nos_envolvidos.add(no.id)
        resultado.mensagens += 1
        novo_caminho = caminho_atual + [no.id]
        resultado.caminho.append(no.id)

        if remetente_id:
            resultado.mensagens_log.append(
                (remetente_id, no.id, f"QUERY {recurso_id} TTL={ttl_atual}")
            )

        if verbose:
            resultado.log.append(
                f"[backtracking] {'->'.join(novo_caminho)} (TTL={ttl_atual})"
            )

        if no.tem_recurso(recurso_id):
            resultado.encontrado = True
            resultado.no_encontrado = no.id
            if remetente_id:
                resultado.mensagens_log.append(
                    (no.id, remetente_id, f"FOUND {recurso_id}")
                )
            if verbose:
                resultado.log.append(f"  -> ENCONTRADO em {no.id}!")
            return True

        if ttl_atual <= 0:
            if verbose:
                resultado.log.append(f"  -> TTL esgotado em {no.id}, backtracking...")
            return False

        vizinhos = list(no.vizinhos)
        random.shuffle(vizinhos)
        caminho_set = set(novo_caminho)

        for viz in vizinhos:
            if viz.id not in caminho_set:
                if _dfs(viz, ttl_atual - 1, novo_caminho, no.id):
                    return True

        if verbose and not resultado.encontrado:
            resultado.log.append(f"  -> Sem saída em {no.id}, backtracking...")
        return False

    _dfs(no_origem, ttl, [], None)
    return resultado


# ------------------------------------------------------------------
# Parallel Walk  (múltiplos caminhantes simultâneos)
# ------------------------------------------------------------------

def parallel_walk(
    no_origem: Node,
    recurso_id: str,
    ttl: int,
    num_caminhos: int = 3,
    verbose: bool = False,
) -> SearchResult:
    """
    Múltiplos caminhantes aleatórios simultâneos a partir do nó de origem.
    Cada caminhante segue uma direção diferente; o primeiro a encontrar o
    recurso encerra a busca.
    """
    resultado = SearchResult()
    resultado.nos_envolvidos.add(no_origem.id)
    resultado.mensagens += 1
    resultado.caminho.append(no_origem.id)

    vizinhos = list(no_origem.vizinhos)
    random.shuffle(vizinhos)
    starts = vizinhos[:min(num_caminhos, len(vizinhos))]

    if not starts:
        return resultado

    if verbose:
        resultado.log.append(
            f"[parallel] {len(starts)} caminhos iniciados: {[v.id for v in starts]}"
        )

    # Cada walker: (no_atual, no_anterior_id, ttl_restante, id_caminho)
    ativo: list[tuple[Node, str, int, int]] = [
        (no, no_origem.id, ttl - 1, i + 1) for i, no in enumerate(starts)
    ]

    while ativo and not resultado.encontrado:
        proximo_ativo: list[tuple[Node, str, int, int]] = []
        for no_atual, no_ant_id, ttl_atual, cid in ativo:
            if resultado.encontrado:
                break
            resultado.nos_envolvidos.add(no_atual.id)
            resultado.mensagens += 1
            resultado.caminho.append(no_atual.id)
            resultado.mensagens_log.append(
                (no_ant_id, no_atual.id, f"QUERY[c{cid}] {recurso_id} TTL={ttl_atual}")
            )

            if verbose:
                resultado.log.append(
                    f"[parallel/c{cid}] {no_atual.id} (TTL={ttl_atual})"
                )

            if no_atual.tem_recurso(recurso_id):
                resultado.encontrado = True
                resultado.no_encontrado = no_atual.id
                resultado.mensagens_log.append(
                    (no_atual.id, no_ant_id, f"FOUND[c{cid}] {recurso_id}")
                )
                if verbose:
                    resultado.log.append(
                        f"  -> ENCONTRADO em {no_atual.id} (caminho {cid})!"
                    )
                break

            if ttl_atual <= 0:
                continue

            candidatos = [v for v in no_atual.vizinhos if v.id != no_ant_id]
            if not candidatos:
                candidatos = no_atual.vizinhos
            if candidatos:
                proximo = random.choice(candidatos)
                proximo_ativo.append((proximo, no_atual.id, ttl_atual - 1, cid))

        if not resultado.encontrado:
            ativo = proximo_ativo

    return resultado


# ------------------------------------------------------------------
# Parallel Backtracking Walk  (paralelo + backtracking)
# ------------------------------------------------------------------

def parallel_backtracking_walk(
    no_origem: Node,
    recurso_id: str,
    ttl: int,
    num_caminhos: int = 3,
    verbose: bool = False,
) -> SearchResult:
    """
    Múltiplos caminhos paralelos, cada um usando DFS com backtracking.
    """
    resultado = SearchResult()
    resultado.nos_envolvidos.add(no_origem.id)
    resultado.mensagens += 1
    resultado.caminho.append(no_origem.id)

    vizinhos = list(no_origem.vizinhos)
    random.shuffle(vizinhos)
    starts = vizinhos[:min(num_caminhos, len(vizinhos))]

    if verbose:
        resultado.log.append(
            f"[parallel+backtracking] {len(starts)} caminhos com DFS backtracking"
        )

    for i, no_inicial in enumerate(starts):
        if resultado.encontrado:
            break
        if verbose:
            resultado.log.append(f"  Caminho {i + 1} iniciando em {no_inicial.id}")

        sub = backtracking_walk(no_inicial, recurso_id, ttl - 1, verbose)
        resultado.mensagens += sub.mensagens
        resultado.nos_envolvidos.update(sub.nos_envolvidos)
        resultado.caminho.extend(sub.caminho)
        resultado.log.extend(sub.log)
        resultado.mensagens_log.extend(sub.mensagens_log)

        if sub.encontrado:
            resultado.encontrado = True
            resultado.no_encontrado = sub.no_encontrado

    return resultado


# ------------------------------------------------------------------
# Validação com vizinhos
# ------------------------------------------------------------------

def validar_com_vizinhos(no_encontrado: Node, recurso_id: str) -> dict:
    """
    Consulta os vizinhos de `no_encontrado` para confirmar ou refutar a
    disponibilidade do recurso. Cada vizinho responde com base no seu
    cache e conhecimento local.
    """
    confirmacoes = 0
    refutacoes = 0
    respostas: dict[str, str] = {}

    recurso_existe = no_encontrado.tem_recurso(recurso_id)

    for viz in no_encontrado.vizinhos:
        tem_no_cache = (
            recurso_id in viz.cache
            and no_encontrado.id in viz.cache.get(recurso_id, set())
        )
        if recurso_existe:
            if tem_no_cache:
                resp = "CONFIRMA (cache)"
            else:
                resp = "CONFIRMA (ping)"
            confirmacoes += 1
        else:
            resp = "REFUTA (recurso ausente)"
            refutacoes += 1

        respostas[viz.id] = resp

    total = confirmacoes + refutacoes
    return {
        "confirmacoes": confirmacoes,
        "refutacoes": refutacoes,
        "total_vizinhos": total,
        "respostas": respostas,
        "valido": total > 0 and confirmacoes >= refutacoes,
    }


# ------------------------------------------------------------------
# Utilitário interno
# ------------------------------------------------------------------

def _atualizar_caminho(caminho: list[Node], recurso_id: str, no_dono: str) -> None:
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
    "backtracking_walk": backtracking_walk,
    "parallel_walk": parallel_walk,
}

MODOS = ("normal", "backtracking", "paralelo", "ambos")


def executar_busca(
    no_origem: Node,
    recurso_id: str,
    ttl: int,
    algo: str,
    verbose: bool = False,
    modo: str = "normal",
    num_caminhos: int = 3,
) -> SearchResult:
    """
    Executa o algoritmo especificado e retorna o resultado.

    `modo` pode ser:
      - "normal"       — usa o algoritmo selecionado sem modificações
      - "backtracking" — substitui por backtracking_walk (DFS)
      - "paralelo"     — substitui por parallel_walk (N caminhantes)
      - "ambos"        — substitui por parallel_backtracking_walk
    """
    if algo not in ALGORITMOS:
        raise ValueError(
            f"Algoritmo '{algo}' desconhecido. Opções: {list(ALGORITMOS.keys())}"
        )

    if modo == "backtracking":
        return backtracking_walk(no_origem, recurso_id, ttl, verbose)
    if modo == "paralelo":
        return parallel_walk(no_origem, recurso_id, ttl, num_caminhos, verbose)
    if modo == "ambos":
        return parallel_backtracking_walk(no_origem, recurso_id, ttl, num_caminhos, verbose)

    fn = ALGORITMOS[algo]
    if algo == "parallel_walk":
        return fn(no_origem, recurso_id, ttl, num_caminhos, verbose)
    return fn(no_origem, recurso_id, ttl, verbose)
