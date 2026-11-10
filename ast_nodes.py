"""Nós da árvore sintática (AST) da linguagem Meme.

Este arquivo é o contrato entre o parser e o avaliador:
- o parser (parser.py) lê os tokens e monta estes nós;
- o avaliador (avaliador.py) percorre estes nós e executa o programa.

Todo nó guarda `linha`, a linha do .meme de onde ele veio, para que os
erros apontem o lugar certo. Ela tem valor padrão 0 para facilitar a
montagem de árvores à mão nos testes, por exemplo:

    Print(Binario("PLUS", Literal(1), Literal(2)))
"""
from __future__ import annotations

from dataclasses import dataclass, field


class No:
    """Base de todos os nós da árvore."""


class Comando(No):
    """Base dos nós que são uma linha de ação (print, atribuição, if, ...)."""


class Expressao(No):
    """Base dos nós que produzem um valor (número, conta, variável, ...)."""


# ---------------------------------------------------------------------------
# Programa
# ---------------------------------------------------------------------------

@dataclass
class Programa(No):
    """O arquivo .meme inteiro: uma lista de comandos em ordem."""

    comandos: list[Comando] = field(default_factory=list)
    linha: int = 0


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

@dataclass
class Print(Comando):
    """OLHA O GÁS expr"""

    expressao: Expressao
    linha: int = 0


@dataclass
class Atribuicao(Comando):
    """aqui tem coragem nome = expr"""

    nome: str
    expressao: Expressao
    linha: int = 0


@dataclass
class If(Comando):
    """quero cafééé condicao
        corpo
    que show da xuxa é esse
        senao
    para nossa alegria

    `senao` é uma lista vazia quando não há "que show da xuxa é esse".
    """

    condicao: Expressao
    corpo: list[Comando]
    senao: list[Comando] = field(default_factory=list)
    linha: int = 0


@dataclass
class While(Comando):
    """Irineu você não sabe nem eu condicao
        corpo
    """

    condicao: Expressao
    corpo: list[Comando]
    linha: int = 0


# ---------------------------------------------------------------------------
# Expressões: valores simples
# ---------------------------------------------------------------------------

@dataclass
class Literal(Expressao):
    """Um valor escrito direto no código: 42, 3.14, "texto", True, False, None."""

    valor: object
    linha: int = 0


@dataclass
class FString(Expressao):
    """f"Olá {nome}"

    `texto` é o conteúdo cru, com as chaves; o avaliador troca cada
    {nome_de_variavel} pelo valor da variável.
    """

    texto: str
    linha: int = 0


@dataclass
class Variavel(Expressao):
    """O uso de uma variável pelo nome: usuario, tentativas, ..."""

    nome: str
    linha: int = 0


@dataclass
class Input(Expressao):
    """se é louco cachoeira prompt

    `prompt` é a expressão mostrada ao usuário antes de ler a entrada.
    """

    prompt: Expressao
    linha: int = 0


# ---------------------------------------------------------------------------
# Expressões: operações
# ---------------------------------------------------------------------------

@dataclass
class Binario(Expressao):
    """Operação com dois lados: a + b, x == 0, a and b, ...

    `operador` é o TIPO do token, como veio do lexer:
    "PLUS", "MINUS", "STAR", "SLASH", "FLOORDIV", "MOD", "POW",
    "EQ", "NE", "LT", "GT", "LE", "GE", "AND", "OR".
    """

    operador: str
    esquerda: Expressao
    direita: Expressao
    linha: int = 0


@dataclass
class Unario(Expressao):
    """Operação com um lado só: -x, not pronto.

    `operador` é "MINUS" ou "NOT".
    """

    operador: str
    operando: Expressao
    linha: int = 0


@dataclass
class Chamada(Expressao):
    """Chamada de função: int(idade), round(imc, 2), ..."""

    nome: str
    argumentos: list[Expressao] = field(default_factory=list)
    linha: int = 0