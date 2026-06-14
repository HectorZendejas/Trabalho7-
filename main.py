"""
main.py — Ponto de entrada CLI para o simulador de busca P2P.

Uso:
    python main.py --config config.yaml [--verbose] [--grafico] [--sem-wizard]

Prompt interativo:
    > buscar --no n1 --recurso r5 --ttl 5 --algo flooding
    > buscar --no n3 --recurso r2 --ttl 4 --algo random_walk --modo backtracking
    > buscar --no n1 --recurso r5 --ttl 6 --algo flooding --modo paralelo --num-caminhos 3
    > buscar --no n1 --recurso r5 --ttl 5 --algo flooding --validar --exportar-rastro saida.txt
    > consultar --recurso r5
    > rede
    > grafico
    > sair
"""

import argparse
import shlex
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from network import Network
from search import executar_busca, validar_com_vizinhos, ALGORITMOS, MODOS


# ------------------------------------------------------------------
# Topologia ASCII
# ------------------------------------------------------------------

def exibir_grafico_ascii(rede: Network) -> None:
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
# Wizard de configuração inicial
# ------------------------------------------------------------------

def configurar_busca_inicial(rede: Network) -> dict:
    """
    Wizard interativo que define padrões para o comando buscar.
    O usuário pode pressionar Enter para aceitar os valores padrão.
    Retorna um dicionário com as configurações escolhidas.
    """
    todos_recursos: set[str] = set()
    for no in rede.nos.values():
        todos_recursos.update(no.recursos)
    todos_nos = sorted(rede.nos.keys())
    recursos_ord = sorted(todos_recursos)

    print("=== CONFIGURAÇÃO DE PADRÕES ===")
    print("Defina valores padrão para não precisar redigitá-los a cada busca.")
    print("Pressione Enter para manter o padrão entre colchetes.\n")
    print(f"  Nós disponíveis : {todos_nos}")
    print(f"  Recursos na rede: {recursos_ord}")
    print(f"  Algoritmos      : {', '.join(ALGORITMOS.keys())}")
    print(f"  Modos           : {', '.join(MODOS)}")
    print()

    # --- recurso ---
    print("1) Recurso-alvo padrão")
    print(f"   Digite apenas o ID do recurso, ex: {recursos_ord[0] if recursos_ord else 'r1'}")
    recurso_raw = input("   Valor [nenhum]: ").strip() or None
    recurso = None
    if recurso_raw:
        if recurso_raw in todos_recursos:
            recurso = recurso_raw
        else:
            opcoes = [r for r in recursos_ord if recurso_raw in r]
            if opcoes:
                print(f"   [aviso] '{recurso_raw}' não encontrado. Recursos parecidos: {opcoes}")
            else:
                print(f"   [aviso] '{recurso_raw}' não existe na rede. Deixando sem padrão.")
    print()

    # --- nó de origem ---
    print("2) Nó de origem padrão")
    print(f"   Digite apenas o ID do nó, ex: {todos_nos[0] if todos_nos else 'n1'}")
    no_raw = input("   Valor [nenhum]: ").strip() or None
    no_default = None
    if no_raw:
        if no_raw in rede.nos:
            no_default = no_raw
        else:
            opcoes = [n for n in todos_nos if no_raw in n]
            if opcoes:
                print(f"   [aviso] '{no_raw}' não encontrado. Nós parecidos: {opcoes}")
            else:
                print(f"   [aviso] '{no_raw}' não existe na rede. Deixando sem padrão.")
    print()

    # --- algoritmo ---
    algos = list(ALGORITMOS.keys())
    print("3) Algoritmo padrão")
    print(f"   Opções: {', '.join(algos)}")
    algo_input = input("   Valor [flooding]: ").strip()
    if algo_input and algo_input not in ALGORITMOS:
        parecidos = [a for a in algos if algo_input in a]
        if parecidos:
            print(f"   [aviso] '{algo_input}' não reconhecido. Você quis dizer: {parecidos[0]}? Usando flooding.")
        else:
            print(f"   [aviso] '{algo_input}' não reconhecido. Usando flooding.")
    algo = algo_input if algo_input in ALGORITMOS else "flooding"
    print()

    # --- TTL ---
    print("4) TTL padrão (número inteiro, ex: 5)")
    ttl_input = input("   Valor [5]: ").strip()
    try:
        ttl = int(ttl_input) if ttl_input else 5
        if ttl <= 0:
            print("   [aviso] TTL deve ser positivo. Usando 5.")
            ttl = 5
    except ValueError:
        print(f"   [aviso] '{ttl_input}' não é um número. Usando 5.")
        ttl = 5
    print()

    # --- modo ---
    print("5) Modo de busca padrão")
    print(f"   Opções: {', '.join(MODOS)}")
    modo_input = input("   Valor [normal]: ").strip()
    if modo_input and modo_input not in MODOS:
        print(f"   [aviso] '{modo_input}' não reconhecido. Usando normal.")
    modo = modo_input if modo_input in MODOS else "normal"
    print()

    # --- num caminhos ---
    print("6) Número de caminhos paralelos (usado somente no modo paralelo/ambos)")
    nc_input = input("   Valor [3]: ").strip()
    try:
        num_caminhos = int(nc_input) if nc_input else 3
        if num_caminhos <= 0:
            print("   [aviso] Deve ser positivo. Usando 3.")
            num_caminhos = 3
    except ValueError:
        print(f"   [aviso] '{nc_input}' não é um número. Usando 3.")
        num_caminhos = 3

    defaults = {
        "recurso": recurso,
        "no_id": no_default,
        "algo": algo,
        "ttl": ttl,
        "modo": modo,
        "num_caminhos": num_caminhos,
    }

    print("\n=== Padrões salvos ===")
    print(f"  Recurso        : {recurso or '(nenhum)'}")
    print(f"  Nó de origem   : {no_default or '(nenhum)'}")
    print(f"  Algoritmo      : {algo}")
    print(f"  TTL            : {ttl}")
    print(f"  Modo           : {modo}")
    print(f"  Num. caminhos  : {num_caminhos}")
    print()
    print("Esses valores serão usados quando você omitir o parâmetro no comando buscar.")
    print("Exemplo com todos os padrões acima:")
    exemplo_no = no_default or (todos_nos[0] if todos_nos else "n1")
    exemplo_rec = recurso or (recursos_ord[0] if recursos_ord else "r1")
    print(f"  > buscar --no {exemplo_no} --recurso {exemplo_rec}")
    print()

    return defaults


# ------------------------------------------------------------------
# Rastro da busca
# ------------------------------------------------------------------

def _exibir_rastro(resultado, recurso_id: str, algo: str) -> None:
    print("\n=== RASTRO DA BUSCA ===")
    print(f"Recurso: {recurso_id}  |  Algoritmo: {algo}")
    print(f"Nós visitados ({len(resultado.caminho)}): {' -> '.join(resultado.caminho) or '(vazio)'}")

    if resultado.mensagens_log:
        print(f"\nMensagens trocadas ({len(resultado.mensagens_log)}):")
        for i, (de, para, conteudo) in enumerate(resultado.mensagens_log, 1):
            print(f"  [{i:3d}] {de:>8} -> {para:<8}  {conteudo}")

    if resultado.encontrado:
        print(f"\nRecurso encontrado em: '{resultado.no_encontrado}'")
    else:
        print("\nRecurso NÃO encontrado.")
    print("=======================\n")


def _exportar_rastro(resultado, recurso_id: str, algo: str, arquivo: str) -> None:
    try:
        with open(arquivo, "w", encoding="utf-8") as f:
            f.write("RASTRO DA BUSCA\n")
            f.write("=" * 40 + "\n")
            f.write(f"Recurso   : {recurso_id}\n")
            f.write(f"Algoritmo : {algo}\n")
            f.write(f"Encontrado: {'Sim' if resultado.encontrado else 'Nao'}\n")
            if resultado.encontrado:
                f.write(f"No com recurso: {resultado.no_encontrado}\n")
            f.write(f"Mensagens : {resultado.mensagens}\n")
            f.write(f"Nos envolvidos: {sorted(resultado.nos_envolvidos)}\n\n")

            f.write(f"SEQUENCIA DE NOS ({len(resultado.caminho)}):\n")
            f.write(" -> ".join(resultado.caminho) + "\n\n")

            if resultado.mensagens_log:
                f.write(f"MENSAGENS TROCADAS ({len(resultado.mensagens_log)}):\n")
                for i, (de, para, conteudo) in enumerate(resultado.mensagens_log, 1):
                    f.write(f"  [{i}] {de} -> {para}: {conteudo}\n")

        print(f"Rastro exportado para '{arquivo}'.")
    except OSError as e:
        print(f"Erro ao exportar rastro: {e}")


# ------------------------------------------------------------------
# Validação com vizinhos
# ------------------------------------------------------------------

def _exibir_validacao(resultado, rede: Network, recurso_id: str, verbose: bool) -> None:
    if not resultado.encontrado or not resultado.no_encontrado:
        print("  (validação ignorada: recurso não encontrado)")
        return

    no_enc = rede.nos.get(resultado.no_encontrado)
    if not no_enc:
        print(f"  (validação ignorada: nó '{resultado.no_encontrado}' não localizado)")
        return

    print(f"\n--- Validação com vizinhos de '{no_enc.id}' ---")
    val = validar_com_vizinhos(no_enc, recurso_id)

    for viz_id, resp in val["respostas"].items():
        print(f"  {viz_id}: {resp}")

    if val["total_vizinhos"] == 0:
        print("  (nenhum vizinho para consultar)")
    else:
        print(
            f"  Resultado: {val['confirmacoes']} CONFIRMA / {val['refutacoes']} REFUTA"
            f"  -> {'VALIDO' if val['valido'] else 'INVALIDO'}"
        )
    print()


# ------------------------------------------------------------------
# Consulta de recursos no grafo
# ------------------------------------------------------------------

def processar_consultar(rede: Network, args_linha: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="consultar", add_help=False)
    parser.add_argument("--recurso", required=True, dest="recurso_id")

    try:
        args = parser.parse_args(args_linha)
    except SystemExit:
        print("Uso: consultar --recurso <id>")
        return

    nos_com = [no for no in rede.nos.values() if no.tem_recurso(args.recurso_id)]

    print(f"\nConsulta de recursos no grafo: '{args.recurso_id}'")
    if nos_com:
        print(f"  Recurso presente em {len(nos_com)} nó(s):")
        for no in nos_com:
            vizinhos_ids = [v.id for v in no.vizinhos]
            print(f"    {no.id}  (vizinhos: {vizinhos_ids})")
    else:
        print(f"  '{args.recurso_id}' não existe em nenhum nó da rede.")
    print()


# ------------------------------------------------------------------
# Ajuda
# ------------------------------------------------------------------

def _exibir_ajuda() -> None:
    print("Comandos disponíveis:")
    print()
    print("  buscar --no <id> --recurso <id> --ttl <n> --algo <algoritmo>")
    print("         [--modo normal|backtracking|paralelo|ambos]")
    print("         [--num-caminhos <n>]  (usado com paralelo/ambos, padrão 3)")
    print("         [--validar]           (consulta vizinhos após encontrar)")
    print("         [--rastro]            (exibe rastro detalhado)")
    print("         [--exportar-rastro <arquivo>]")
    print("         [--verbose]")
    print()
    print("    algoritmos: flooding | informed_flooding | random_walk |")
    print("                informed_random_walk | backtracking_walk | parallel_walk")
    print()
    print("  consultar --recurso <id>  — mostra quais nós têm o recurso no grafo")
    print("  rede                      — topologia ASCII e recursos por nó")
    print("  grafico                   — visualização matplotlib")
    print("  ajuda                     — esta mensagem")
    print("  sair                      — encerra o programa")


# ------------------------------------------------------------------
# Processamento do comando buscar
# ------------------------------------------------------------------

def processar_buscar(
    rede: Network,
    args_linha: list[str],
    verbose_global: bool,
    defaults: dict,
) -> None:
    parser = argparse.ArgumentParser(prog="buscar", add_help=False)
    parser.add_argument("--no", dest="no_id", default=defaults.get("no_id"))
    parser.add_argument("--recurso", dest="recurso_id", default=defaults.get("recurso"))
    parser.add_argument("--ttl", type=int, default=defaults.get("ttl", 5))
    parser.add_argument("--algo", choices=list(ALGORITMOS.keys()),
                        default=defaults.get("algo", "flooding"))
    parser.add_argument("--modo", choices=list(MODOS),
                        default=defaults.get("modo", "normal"))
    parser.add_argument("--num-caminhos", type=int, dest="num_caminhos",
                        default=defaults.get("num_caminhos", 3))
    parser.add_argument("--validar", action="store_true", default=False)
    parser.add_argument("--rastro", action="store_true", default=False)
    parser.add_argument("--exportar-rastro", dest="exportar_rastro", default=None)
    parser.add_argument("--verbose", action="store_true", default=False)

    try:
        args = parser.parse_args(args_linha)
    except SystemExit:
        print("Uso: buscar --no <id> --recurso <id> [--ttl <n>] [--algo <algoritmo>] ...")
        return

    if not args.no_id:
        print("Erro: informe o nó de origem com --no <id>.")
        return
    if not args.recurso_id:
        print("Erro: informe o recurso com --recurso <id>.")
        return

    try:
        no_origem = rede.obter_no(args.no_id)
    except KeyError as e:
        print(f"Erro: {e}")
        return

    modo_verbose = verbose_global or args.verbose

    print(
        f"\nBuscando '{args.recurso_id}' a partir de '{args.no_id}' "
        f"(TTL={args.ttl}, algo={args.algo}, modo={args.modo})..."
    )

    resultado = executar_busca(
        no_origem=no_origem,
        recurso_id=args.recurso_id,
        ttl=args.ttl,
        algo=args.algo,
        verbose=modo_verbose,
        modo=args.modo,
        num_caminhos=args.num_caminhos,
    )

    if modo_verbose and resultado.log:
        print("\n--- Log passo a passo ---")
        for entrada in resultado.log:
            print(f"  {entrada}")
        print("--- Fim do log ---")

    print("\n=== RESULTADO ===")
    print(f"  Algoritmo      : {args.algo}  (modo: {args.modo})")
    print(f"  Mensagens      : {resultado.mensagens}")
    print(f"  Nós envolvidos : {len(resultado.nos_envolvidos)} {sorted(resultado.nos_envolvidos)}")
    if resultado.encontrado:
        print(f"  Recurso        : ENCONTRADO em '{resultado.no_encontrado}'")
    else:
        print(f"  Recurso        : NAO ENCONTRADO (TTL esgotado)")
    print()

    if args.validar:
        _exibir_validacao(resultado, rede, args.recurso_id, modo_verbose)

    if args.rastro:
        _exibir_rastro(resultado, args.recurso_id, args.algo)

    if args.exportar_rastro:
        _exportar_rastro(resultado, args.recurso_id, args.algo, args.exportar_rastro)


# ------------------------------------------------------------------
# Loop principal
# ------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Simulador de busca em redes P2P")
    parser.add_argument("--config", required=True, help="Caminho para o arquivo config.yaml")
    parser.add_argument("--verbose", action="store_true", help="Ativa log passo a passo")
    parser.add_argument("--grafico", action="store_true", help="Exibe grafo matplotlib ao iniciar")
    parser.add_argument("--sem-wizard", action="store_true",
                        help="Pula o wizard de configuração inicial")
    args = parser.parse_args()

    print(f"Carregando rede de '{args.config}'...")
    try:
        rede = Network.carregar(args.config)
    except (ValueError, FileNotFoundError) as e:
        print(f"Erro ao carregar rede: {e}")
        sys.exit(1)

    print(f"Rede carregada: {len(rede.nos)} nós.\n")
    print(rede.resumo())
    print()

    if args.grafico:
        exibir_grafico_matplotlib(rede)

    # Wizard de configuração inicial
    defaults: dict = {
        "recurso": None,
        "no_id": None,
        "algo": "flooding",
        "ttl": 5,
        "modo": "normal",
        "num_caminhos": 3,
    }

    if not args.sem_wizard:
        resp = input("Deseja configurar padrões de busca agora? (s/N): ").strip().lower()
        if resp == "s":
            defaults = configurar_busca_inicial(rede)
        print()

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
            processar_buscar(rede, partes[1:], args.verbose, defaults)
        elif comando == "consultar":
            processar_consultar(rede, partes[1:])
        elif comando in ("ajuda", "help"):
            _exibir_ajuda()
        else:
            print(f"Comando desconhecido: '{comando}'. Digite 'ajuda' para ver os comandos.")


if __name__ == "__main__":
    main()
