"""
main.py — Ponto de entrada CLI para o simulador de busca P2P.

Uso:
    python main.py --config config.yaml [--verbose] [--grafico]

Depois, prompt interativo:
    > buscar --no n1 --recurso r5 --ttl 5 --algo flooding
    > buscar --no n3 --recurso r2 --ttl 4 --algo informed_random_walk
    > rede          (exibe resumo da rede)
    > grafico       (exibe representação ASCII)
    > sair
"""

import argparse
import shlex
import sys

# Força UTF-8 no console do Windows para exibir acentos corretamente
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from network import Network
from search import executar_busca, ALGORITMOS


# ------------------------------------------------------------------
# Representação ASCII da rede
# ------------------------------------------------------------------

def exibir_grafico_ascii(rede: Network) -> None:
    """Exibe uma representação textual simples da rede."""
    print("\n=== TOPOLOGIA DA REDE ===")
    arestas_vistas: set[frozenset] = set()
    for no in rede.nos.values():
        for viz in no.vizinhos:
            chave = frozenset({no.id, viz.id})
            if chave not in arestas_vistas:
                arestas_vistas.add(chave)
                print(f"  {no.id} --- {viz.id}")
    print()

    print("=== RECURSOS POR NÓ ===")
    for no in rede.nos.values():
        print(f"  {no.id}: {sorted(no.recursos)}")
    print()


def exibir_grafico_matplotlib(rede: Network) -> None:
    """Exibe a rede graficamente usando matplotlib (opcional)."""
    try:
        import matplotlib.pyplot as plt
        import networkx as nx
    except ImportError:
        print("[aviso] matplotlib ou networkx não instalado. Use 'pip install matplotlib networkx'.")
        return

    G = nx.Graph()
    for no in rede.nos.values():
        G.add_node(no.id)
        for viz in no.vizinhos:
            G.add_edge(no.id, viz.id)

    rotulos = {no.id: f"{no.id}\n{','.join(sorted(no.recursos))}" for no in rede.nos.values()}
    pos = nx.spring_layout(G, seed=42)
    plt.figure(figsize=(10, 7))
    nx.draw(G, pos, labels=rotulos, with_labels=True,
            node_color="lightblue", node_size=1500, font_size=8)
    plt.title("Rede P2P")
    plt.tight_layout()
    plt.show()


# ------------------------------------------------------------------
# Ajuda
# ------------------------------------------------------------------

def _exibir_ajuda() -> None:
    print("Comandos disponíveis:")
    print("  buscar --no <id> --recurso <id> --ttl <n> --algo <algoritmo> [--verbose]")
    print("    algoritmos: flooding | informed_flooding | random_walk | informed_random_walk")
    print("  rede         — exibe topologia ASCII e recursos de cada nó")
    print("  grafico      — exibe grafo com matplotlib")
    print("  ajuda        — exibe esta mensagem")
    print("  sair         — encerra o programa")


# ------------------------------------------------------------------
# Processamento de comandos interativos
# ------------------------------------------------------------------

def processar_buscar(rede: Network, args_linha: list[str], verbose: bool) -> None:
    parser = argparse.ArgumentParser(prog="buscar", add_help=False)
    parser.add_argument("--no", required=True, dest="no_id")
    parser.add_argument("--recurso", required=True, dest="recurso_id")
    parser.add_argument("--ttl", required=True, type=int)
    parser.add_argument("--algo", required=True, choices=list(ALGORITMOS.keys()))
    parser.add_argument("--verbose", action="store_true", default=False)

    try:
        args = parser.parse_args(args_linha)
    except SystemExit:
        print("Uso: buscar --no <id> --recurso <id> --ttl <n> --algo <algoritmo>")
        return

    try:
        no_origem = rede.obter_no(args.no_id)
    except KeyError as e:
        print(f"Erro: {e}")
        return

    modo_verbose = verbose or args.verbose

    print(f"\nBuscando '{args.recurso_id}' a partir de '{args.no_id}' "
          f"(TTL={args.ttl}, algoritmo={args.algo})...")

    resultado = executar_busca(
        no_origem=no_origem,
        recurso_id=args.recurso_id,
        ttl=args.ttl,
        algo=args.algo,
        verbose=modo_verbose,
    )

    if modo_verbose and resultado.log:
        print("\n--- Log passo a passo ---")
        for entrada in resultado.log:
            print(f"  {entrada}")
        print("--- Fim do log ---")

    print("\n=== RESULTADO ===")
    print(f"  Algoritmo      : {args.algo}")
    print(f"  Mensagens      : {resultado.mensagens}")
    print(f"  Nós envolvidos : {len(resultado.nos_envolvidos)} {sorted(resultado.nos_envolvidos)}")
    if resultado.encontrado:
        print(f"  Recurso        : ENCONTRADO em '{resultado.no_encontrado}'")
    else:
        print(f"  Recurso        : NÃO ENCONTRADO (TTL esgotado)")
    print()


# ------------------------------------------------------------------
# Loop principal
# ------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Simulador de busca em redes P2P")
    parser.add_argument("--config", required=True, help="Caminho para o arquivo config.yaml")
    parser.add_argument("--verbose", action="store_true", help="Ativa log passo a passo")
    parser.add_argument("--grafico", action="store_true", help="Exibe grafo com matplotlib ao iniciar")
    args = parser.parse_args()

    print(f"Carregando rede de '{args.config}'...")
    try:
        rede = Network.carregar(args.config)
    except (ValueError, FileNotFoundError) as e:
        print(f"Erro ao carregar rede: {e}")
        sys.exit(1)

    print(f"Rede carregada com sucesso: {len(rede.nos)} nós.\n")
    print(rede.resumo())
    print()

    if args.grafico:
        exibir_grafico_matplotlib(rede)

    _exibir_ajuda()
    print()

    while True:
        try:
            linha = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando.")
            break

        if not linha:
            continue

        try:
            partes = shlex.split(linha)
        except ValueError as e:
            print(f"Erro de sintaxe: {e}")
            continue

        comando = partes[0].lower()

        if comando == "sair":
            print("Encerrando.")
            break
        elif comando == "rede":
            print(rede.resumo())
            exibir_grafico_ascii(rede)
        elif comando == "grafico":
            exibir_grafico_matplotlib(rede)
        elif comando == "buscar":
            processar_buscar(rede, partes[1:], args.verbose)
        elif comando in ("ajuda", "help"):
            _exibir_ajuda()
        else:
            print(f"Comando desconhecido: '{comando}'. Digite 'ajuda' para ver os comandos.")


if __name__ == "__main__":
    main()
