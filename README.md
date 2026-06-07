# Simulador de Busca em Redes P2P

Simulador de linha de comando de uma rede P2P não estruturada com quatro algoritmos de busca diferentes.

## Estrutura do Projeto

```
p2p_search/
├── main.py        # Ponto de entrada CLI e loop interativo
├── network.py     # Grafo, carregamento do YAML e validações
├── search.py      # Implementação dos 4 algoritmos de busca
├── node.py        # Classe Node (id, recursos, vizinhos, cache)
└── config.yaml    # Configuração de exemplo com 12 nós
```

## Requisitos

```bash
pip install pyyaml
# Opcional, para visualização gráfica:
pip install matplotlib networkx
```

## Como Usar

```bash
cd p2p_search
python main.py --config config.yaml
```

Flags disponíveis:

| Flag | Descrição |
|---|---|
| `--config` | Caminho para o arquivo YAML (obrigatório) |
| `--verbose` | Ativa log passo a passo em todas as buscas |
| `--grafico` | Exibe o grafo com matplotlib ao iniciar |

### Comandos Interativos

```
> buscar --no <id> --recurso <id> --ttl <n> --algo <algoritmo>
> rede        # exibe topologia ASCII e recursos de cada nó
> grafico     # exibe grafo com matplotlib
> sair
```

### Exemplos

```
> buscar --no n1 --recurso r9 --ttl 5 --algo flooding
> buscar --no n3 --recurso r2 --ttl 4 --algo informed_random_walk
> buscar --no n2 --recurso r12 --ttl 8 --algo random_walk --verbose
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

Todos os algoritmos recebem `--no`, `--recurso`, `--ttl` e `--algo`. A saída sempre inclui total de mensagens trocadas, nós envolvidos e se o recurso foi encontrado.

### `flooding`

Envia a consulta para **todos os vizinhos** recursivamente até TTL=0. Não para ao encontrar o recurso: explora todos os caminhos possíveis e registra o primeiro nó encontrado. Garante cobertura máxima ao custo de alto volume de mensagens.

### `informed_flooding`

Igual ao flooding, mas cada nó consulta seu **cache local** antes de propagar. Se o recurso estiver em cache, responde imediatamente sem continuar. Ao encontrar o recurso, atualiza o cache de todos os nós no caminho de volta.

### `random_walk`

Encaminha para **um único vizinho aleatório** por salto. Baixo custo em mensagens, mas sem garantia de encontrar o recurso dentro do TTL.

### `informed_random_walk`

Random walk com consulta de cache. Ao encontrar o recurso (ou acertar o cache), atualiza o cache de todos os nós percorridos no caminho — buscas futuras pelo mesmo recurso convergem mais rápido.

### Comparativo

| Algoritmo | Mensagens | Garantia de Encontrar | Cache |
|---|---|---|---|
| `flooding` | Alta | Sim (dentro do TTL) | Não |
| `informed_flooding` | Média/Baixa | Sim (1ª vez); imediato após | Sim |
| `random_walk` | Baixa | Não | Não |
| `informed_random_walk` | Baixa | Não (1ª vez); imediato após | Sim |

## Saída de Exemplo

```
Buscando 'r9' a partir de 'n1' (TTL=5, algoritmo=flooding)...

=== RESULTADO ===
  Algoritmo      : flooding
  Mensagens      : 12
  Nós envolvidos : 12 ['n1', 'n10', 'n11', 'n12', 'n2', 'n3', 'n4', 'n5', 'n6', 'n7', 'n8', 'n9']
  Recurso        : ENCONTRADO em 'n4'
```

Com `--verbose` (ou `--algo ... --verbose` no prompt), cada salto é exibido:

```
--- Log passo a passo ---
  [flooding] n1 recebeu busca por 'r9' (TTL=5)
  [flooding] n2 recebeu busca por 'r9' (TTL=4)
  ...
  -> ENCONTRADO em n4!
```
