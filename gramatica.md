# Gramática da linguagem Meme

Este arquivo define a sintaxe da linguagem: quais sequências de tokens formam
um programa válido. Ele liga as três partes do projeto:

- `lexer.py` produz os **tokens** (os nomes em MAIÚSCULAS abaixo);
- `parser.py` segue **estas regras** para montar a árvore;
- `ast_nodes.py` define os **nós** que cada regra produz.

## Notação

| Símbolo     | Significado                          |
|-------------|--------------------------------------|
| `MAIUSCULA` | token vindo do lexer                 |
| `minuscula` | outra regra desta gramática          |
| `a b`       | `a` seguido de `b`                   |
| `a \| b`    | `a` ou `b`                           |
| `[ a ]`     | `a` é opcional (0 ou 1 vez)          |
| `{ a }`     | `a` se repete (0 ou mais vezes)      |
| `( a )`     | agrupamento                          |

## Tokens

| Token                                      | Vem de                          |
|--------------------------------------------|---------------------------------|
| `PRINT`                                    | `OLHA O GÁS`                    |
| `INPUT`                                    | `se é louco cachoeira`          |
| `LET`                                      | `aqui tem coragem`              |
| `IF`                                       | `quero cafééé`                  |
| `ELSE`                                     | `que show da xuxa é esse`       |
| `END`                                      | `para nossa alegria`            |
| `WHILE`                                    | `Irineu você não sabe nem eu`   |
| `IDENT`                                    | nomes: `usuario`, `int`         |
| `NUMBER`, `STRING`, `FSTRING`              | `42`, `"oi"`, `f"Olá {nome}"`   |
| `TRUE`, `FALSE`, `NONE`                    | `True`, `False`, `None`         |
| `AND`, `OR`, `NOT`                         | `and`, `or`, `not`              |
| `EQ NE LT GT LE GE`                        | `== != < > <= >=`               |
| `PLUS MINUS STAR SLASH FLOORDIV MOD POW`   | `+ - * / // % **`               |
| `ASSIGN`, `LPAREN`, `RPAREN`, `COMMA`      | `=`, `(`, `)`, `,`              |
| `NEWLINE`                                  | fim de cada linha com código    |
| `INDENT`, `DEDENT`                         | indentação aumentou / diminuiu  |
| `EOF`                                      | fim do arquivo                  |

O lexer também produz `LBRACKET`, `RBRACKET`, `DOT` e `COLON`, mas nenhuma
regra os usa por enquanto. Se aparecerem, o parser dá erro de sintaxe.

## Comandos

```ebnf
programa   = { comando } EOF ;

comando    = print
           | atribuicao
           | if
           | while ;

print      = PRINT expr NEWLINE ;

atribuicao = LET IDENT ASSIGN expr NEWLINE ;

if         = IF expr NEWLINE bloco
             [ ELSE NEWLINE bloco ]
             [ END NEWLINE ] ;

while      = WHILE expr NEWLINE bloco ;

bloco      = INDENT comando { comando } DEDENT ;
```

## Expressões

Cada regra abaixo é um nível de precedência, do mais fraco para o mais forte.
Uma regra só chama a regra de baixo dela, por isso `1 + 2 * 3` vira
`1 + (2 * 3)`.

```ebnf
expr       = ou ;

ou         = e { OR e } ;

e          = nao { AND nao } ;

nao        = NOT nao
           | comparacao ;

comparacao = soma [ ( EQ | NE | LT | GT | LE | GE ) soma ] ;

soma       = termo { ( PLUS | MINUS ) termo } ;

termo      = unario { ( STAR | SLASH | FLOORDIV | MOD ) unario } ;

unario     = MINUS unario
           | potencia ;

potencia   = primario [ POW unario ] ;

primario   = NUMBER | STRING | FSTRING
           | TRUE | FALSE | NONE
           | INPUT expr
           | IDENT [ LPAREN [ argumentos ] RPAREN ]
           | LPAREN expr RPAREN ;

argumentos = expr { COMMA expr } ;
```

### Precedência e associatividade

| Nível (fraco → forte) | Operadores                 | Associatividade        |
|-----------------------|----------------------------|------------------------|
| 1                     | `or`                       | esquerda               |
| 2                     | `and`                      | esquerda               |
| 3                     | `not`                      | unário                 |
| 4                     | `== != < > <= >=`          | não encadeia (só uma)  |
| 5                     | `+ -`                      | esquerda               |
| 6                     | `* / // %`                 | esquerda               |
| 7                     | `-` (negativo)             | unário                 |
| 8                     | `**`                       | direita                |

- **Esquerda:** `10 - 3 - 2` é `(10 - 3) - 2`. O parser usa um laço
  (`while` o próximo token for o operador), e não recursão.
- **Direita:** `2 ** 3 ** 2` é `2 ** (3 ** 2)`. Por isso `potencia`
  chama `unario` do lado direito, e `-2 ** 2` dá `-4`, como no Python.
- **Comparação não encadeia:** `a < b < c` é erro de sintaxe. Use
  `a < b and b < c`.

## Regra → nó da AST

| Regra                         | Nó produzido                                     |
|-------------------------------|--------------------------------------------------|
| `programa`                    | `Programa(comandos)`                             |
| `print`                       | `Print(expressao)`                               |
| `atribuicao`                  | `Atribuicao(nome, expressao)`                    |
| `if`                          | `If(condicao, corpo, senao)`                     |
| `while`                       | `While(condicao, corpo)`                         |
| `bloco`                       | `list[Comando]` (não é um nó)                    |
| `ou`, `e`, `comparacao`, `soma`, `termo`, `potencia` | `Binario(operador, esquerda, direita)` |
| `nao`, `unario`               | `Unario(operador, operando)`                     |
| `NUMBER`, `STRING`, `TRUE`, `FALSE`, `NONE` | `Literal(valor)`                   |
| `FSTRING`                     | `FString(texto)`                                 |
| `INPUT expr`                  | `Input(prompt)`                                  |
| `IDENT`                       | `Variavel(nome)`                                 |
| `IDENT ( argumentos )`        | `Chamada(nome, argumentos)`                      |
| `( expr )`                    | o nó da `expr` de dentro (sem nó extra)          |

Em `Binario` e `Unario`, `operador` é o **tipo** do token (`"PLUS"`, `"EQ"`,
`"NOT"`...). Todo nó recebe `linha` = linha do primeiro token da regra.

`para nossa alegria` (`END`) não gera nó: o parser só o consome.

## Decisões

1. **Os blocos são definidos pela indentação.** `para nossa alegria` é
   opcional depois de um `if`, e não é aceito em nenhum outro lugar.
2. **`aqui tem coragem` é obrigatório** para atribuir. `x = 1` sozinho é
   erro de sintaxe.
3. **`se é louco cachoeira` consome a expressão inteira à direita.**
   `se é louco cachoeira "Nome: " + "?"` mostra `"Nome: ?"`. Para usar o
   resultado numa conta, use parênteses: `int(se é louco cachoeira "Idade? ")`.
4. **`OLHA O GÁS` recebe uma expressão só.** Para juntar valores, use
   f-string: `OLHA O GÁS f"{nome} tem {idade} anos"`.
5. **Funções só podem ser chamadas pelo nome** (`int(x)`). O avaliador decide
   quais existem (`int`, `float`, `str`, `round`, `len`).

## Exemplo

```
quero cafééé resposta == "0"
    OLHA O GÁS "Não dormiu nada"
que show da xuxa é esse
    aqui tem coragem tentativas = tentativas - 1
para nossa alegria
```

Tokens:

```
IF IDENT EQ STRING NEWLINE
INDENT PRINT STRING NEWLINE
DEDENT ELSE NEWLINE
INDENT LET IDENT ASSIGN IDENT MINUS NUMBER NEWLINE
DEDENT END NEWLINE
```

Árvore:

```
If
├── condicao: Binario("EQ", Variavel("resposta"), Literal("0"))
├── corpo:
│   └── Print(Literal("Não dormiu nada"))
└── senao:
    └── Atribuicao("tentativas",
            Binario("MINUS", Variavel("tentativas"), Literal(1)))
```