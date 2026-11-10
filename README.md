# CompiladorMeme

Uma linguagem de programação de brincadeira, escrita com frases de meme brasileiro. Os programas ficam em arquivos `.meme` e são executados por um interpretador feito em Python.

## Como usar

Requisitos: Python 3.8 ou superior.

```
python interpretador.py teste.meme
```

Se algo der errado, o interpretador responde com `o meu amor não fique triste: ...`. Quando o programa termina sem erro, ele imprime `sai da frente satanás`.

## Dicionário da linguagem

| Meme                          | O que faz                     | Equivalente em Python |
|-------------------------------|-------------------------------|-----------------------|
| `OLHA O GÁS`                  | Mostra um valor na tela       | `print(...)`          |
| `se é louco cachoeira`        | Lê uma entrada do usuário     | `input(...)`          |
| `aqui tem coragem`            | Guarda um valor numa variável | `x = ...`             |
| `quero cafééé`                | Condição                      | `if ...:`             |
| `que show da xuxa é esse`     | Caso contrário                | `else:`               |
| `para nossa alegria`          | Fecha um bloco de condição    | `pass`                |
| `Irineu você não sabe nem eu` | Laço de repetição             | `while ...:`          |

As expressões (contas, comparações, strings, f-strings) seguem a sintaxe do Python. Os blocos são marcados pela indentação, como no Python.

## Exemplo

```
aqui tem coragem usuario = se é louco cachoeira "Qual e o seu apelido? "
OLHA O GÁS usuario

aqui tem coragem tentativas = 2

Irineu você não sabe nem eu tentativas > 0
    aqui tem coragem resposta = se é louco cachoeira "Quantas horas voce dormiu hoje? (dica: 0): "

    quero cafééé resposta == "0"
        OLHA O GÁS "Não dormiu nada"
        aqui tem coragem tentativas = 0
    que show da xuxa é esse
        OLHA O GÁS "Dormiu demais!!"
        aqui tem coragem tentativas = tentativas - 1
    para nossa alegria

OLHA O GÁS "Diagnostico final concluido com sucesso!"
```

## Estrutura do projeto

| Arquivo            | Descrição                                                              |
|--------------------|------------------------------------------------------------------------|
| `interpretador.py` | Traduz cada linha `.meme` para Python e executa o resultado            |
| `lexer.py`         | Em desenvolvimento: transforma o código `.meme` em tokens              |
| `teste.meme`       | Exemplo com entrada de dados, `while` e `if/else`                      |
| `caos.meme`        | Exemplo de coleta de dados para um cálculo de IMC (ainda incompleto)   |

## Como funciona hoje

O interpretador atual é um tradutor: troca as frases-meme por código Python e roda o resultado com `exec`. É simples, mas tem limitações:

- as trocas de texto também afetam o conteúdo de strings;
- os erros mostram a linha do Python gerado, não a do `.meme`;
- o `exec` executa qualquer código, então só rode arquivos `.meme` em que você confia.

## Roteiro

- [x] Interpretador por tradução para Python
- [X] Lexer (`lexer.py`)
- [ ] Parser que gera uma árvore sintática (AST)
- [ ] Avaliador próprio, sem `exec`
- [ ] Erros com a linha do `.meme`
- [ ] Novas palavras-chave: `elif`, `for`, funções
- [ ] Testes automatizados com `pytest`
- [ ] Terminar o exemplo do IMC em `caos.meme`

## Como contribuir

1. Faça um fork do repositório.
2. Crie uma branch: `git checkout -b minha-contribuicao`.
3. Faça a alteração e teste com `python interpretador.py teste.meme`.
4. Abra um Pull Request explicando o que mudou.

Para mudanças grandes, abra antes uma issue para combinar o rumo com o autor.