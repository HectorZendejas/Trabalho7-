# Simulador de Busca em Redes P2P

Simulador de uma rede P2P não estruturada com seis algoritmos de busca, interface de linha de comando e interface web interativa com visualização do grafo.

## Estrutura do Projeto

```
p2p_search/
├── main.py            # CLI interativo com wizard de configuração
├── app.py             # Servidor web (Flask) com interface HTML
├── network.py         # Grafo, carregamento do YAML e validações
├── search.py          # Algoritmos de busca, rastro e validação
├── node.py            # Classe Node (id, recursos, vizinhos, cache)
├── config.yaml        # Configuração de exemplo
└── templates/
    └── index.html     # Interface web (vis.js + Bootstrap)
```

## Requisitos

```bash
pip install pyyaml

# Para a interface web:
pip install flask

# Opcional, para visualização gráfica no CLI:
pip install matplotlib networkx
```

## Interface Web (recomendada)

```bash
python app.py --config config.yaml
```

Abra `http://localhost:5000` no navegador. A interface inclui:

- **Grafo interativo** (vis.js) com zoom, arrastar nós e tooltip com recursos
- **Formulário de busca** com dropdowns para nó, recurso, algoritmo, modo e TTL
- **Animação do rastro** — nós acendem em sequência durante a busca (velocidade ajustável)
- **Destacar recurso no grafo** — filtra e pinta os nós que têm um recurso específico
- **Painel de resultado** com estatísticas, caminho percorrido e lista de mensagens
- **Validação com vizinhos** — exibe confirmações e refutações por nó vizinho
- **Botão Replay** — re-anima a última busca sem nova requisição

Flag disponível:

| Flag | Descrição |
|---|---|
| `--config` | Caminho para o arquivo YAML (obrigatório) |
| `--porta` | Porta HTTP (padrão: 5000) |

## Interface de Linha de Comando

```bash
python main.py --config config.yaml [--verbose] [--grafico] [--sem-wizard]
```

Ao iniciar, o programa pergunta se você deseja configurar valores padrão (recurso, nó, algoritmo, TTL, modo). Esses padrões são usados automaticamente quando você omite parâmetros no comando `buscar`.

Flags disponíveis:

| Flag | Descrição |
|---|---|
| `--config` | Caminho para o arquivo YAML (obrigatório) |
| `--verbose` | Ativa log passo a passo em todas as buscas |
| `--grafico` | Exibe o grafo com matplotlib ao iniciar |
| `--sem-wizard` | Pula o wizard de configuração inicial |

### Comandos Interativos

```
> buscar --no <id> --recurso <id> --ttl <n> --algo <algoritmo>
         [--modo normal|backtracking|paralelo|ambos]
         [--num-caminhos <n>]
         [--validar]
         [--rastro]
         [--exportar-rastro <arquivo>]
         [--verbose]

> consultar --recurso <id>   # mostra quais nós têm o recurso no grafo
> rede                       # topologia ASCII e recursos por nó
> grafico                    # visualização com matplotlib
> ajuda
> sair
```

### Exemplos

```
> buscar --no n1 --recurso r5 --ttl 5 --algo flooding
> buscar --no n3 --recurso r2 --ttl 4 --algo random_walk --modo backtracking
> buscar --no n1 --recurso r5 --ttl 6 --algo flooding --modo paralelo --num-caminhos 3
> buscar --no n1 --recurso r5 --ttl 5 --algo flooding --validar --rastro
> buscar --no n1 --recurso r5 --ttl 5 --algo flooding --exportar-rastro saida.txt
> consultar --recurso r5
```

## Arquivo de Configuração (YAML)

```yaml
num_nodes: 12
min_neighbors: 2
max_neighbors: 4

resources:
  n1: r1, r2, r3
  n2: r4, r5

edges:
  - n1, n2
  - n1, n3
```

As arestas são não direcionadas. Todos os nós mencionados em `edges` que não aparecerem em `resources` são criados automaticamente — mas a validação exigirá que tenham recursos atribuídos.

## Validações

Executadas automaticamente ao carregar a rede. O programa encerra com erro se alguma falhar.

| Validação | Descrição |
|---|---|
| Conectividade | BFS garante que todos os nós são alcançáveis (sem partições) |
| Grau de vizinhos | Cada nó deve ter entre `min_neighbors` e `max_neighbors` vizinhos |
| Recursos | Nenhum nó pode ter zero recursos |
| Self-loops | Nenhum nó pode ter aresta para si mesmo |

## Algoritmos de Busca

Todos os algoritmos retornam total de mensagens, nós envolvidos, sequência de nós visitados e log de mensagens trocadas.

### `flooding`

Envia a consulta para **todos os vizinhos** recursivamente até TTL=0. Garante cobertura máxima ao custo de alto volume de mensagens.

### `informed_flooding`

Igual ao flooding, mas cada nó consulta seu **cache local** antes de propagar. Se o recurso estiver em cache, responde imediatamente. Atualiza o cache dos nós no caminho ao encontrar o recurso.

### `random_walk`

Encaminha para **um único vizinho aleatório** por salto. Baixo custo em mensagens, sem garantia de encontrar o recurso dentro do TTL.

### `informed_random_walk`

Random walk com consulta de cache. Ao encontrar o recurso, atualiza o cache de todos os nós percorridos — buscas futuras pelo mesmo recurso convergem mais rápido.

### `backtracking_walk`

Busca em profundidade (DFS) com **backtracking**: quando um caminho falha (TTL esgotado ou sem vizinhos inéditos no caminho atual), retorna ao nó anterior e tenta outro vizinho. Evita revisitar nós no caminho corrente para não criar ciclos.

### `parallel_walk`

Múltiplos **caminhantes aleatórios simultâneos** a partir do nó de origem, simulados em round-robin. O primeiro a encontrar o recurso encerra a busca. O número de caminhos é configurável com `--num-caminhos`.

### Modos de Busca (`--modo`)

Os modos podem ser aplicados independentemente do algoritmo escolhido em `--algo`:

| Modo | Comportamento |
|---|---|
| `normal` | Usa o algoritmo selecionado sem modificações (padrão) |
| `backtracking` | Substitui por DFS com backtracking |
| `paralelo` | Substitui por N caminhantes simultâneos |
| `ambos` | N caminhos paralelos, cada um com DFS backtracking |

### Comparativo

| Algoritmo | Mensagens | Garantia de Encontrar | Cache |
|---|---|---|---|
| `flooding` | Alta | Sim (dentro do TTL) | Não |
| `informed_flooding` | Média/Baixa | Sim (1ª vez); imediato após | Sim |
| `random_walk` | Baixa | Não | Não |
| `informed_random_walk` | Baixa | Não (1ª vez); imediato após | Sim |
| `backtracking_walk` | Média | Maior que random walk | Não |
| `parallel_walk` | Média | Maior que random walk | Não |

## Rastro da Busca

Todo resultado inclui:

- `caminho` — sequência ordenada de nós visitados
- `mensagens_log` — cada mensagem trocada entre nós: `(de, para, conteúdo)`

Use `--rastro` para exibir o rastro formatado no terminal ou `--exportar-rastro <arquivo>` para salvar em texto.

```
=== RASTRO DA BUSCA ===
Recurso: r5  |  Algoritmo: flooding
Sequência de nós (8): n1 -> n2 -> n3 -> n4 -> n5 -> n6 -> n7 -> n8

Mensagens trocadas (7):
  [  1] n1      -> n2       QUERY r5 TTL=4
  [  2] n2      -> n3       QUERY r5 TTL=3
  ...
  [  7] n8      -> n7       FOUND r5
=======================
```

## Validação com Vizinhos (`--validar`)

Após encontrar o recurso, consulta cada vizinho do nó encontrado. Cada vizinho responde com base no seu cache e conhecimento local:

- `CONFIRMA (cache)` — vizinho tem entrada de cache apontando para o nó
- `CONFIRMA (ping)` — vizinho não tem cache mas o nó realmente possui o recurso
- `REFUTA` — recurso ausente no nó indicado (cache obsoleto)

## Consulta de Recursos no Grafo

O comando `consultar --recurso <id>` (CLI) e o dropdown "Destacar recurso" (web) mostram exatamente quais nós têm o recurso antes de iniciar uma busca, sem gastar TTL.
