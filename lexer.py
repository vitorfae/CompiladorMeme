"""Lexer da linguagem Meme.

Transforma o texto de um arquivo .meme em uma lista de tokens.
Uso:  python lexer.py arquivo.meme
"""
import re
import sys
import unicodedata
from dataclasses import dataclass


class LexerError(Exception):

    def __init__(self, mensagem, linha, coluna):
        super().__init__(f"linha {linha}, coluna {coluna}: {mensagem}")
        self.linha = linha
        self.coluna = coluna


@dataclass(frozen=True)
class Token:

    tipo: str
    valor: object
    linha: int
    coluna: int

    def __repr__(self):
        return f"{self.linha}:{self.coluna:<3} {self.tipo:<8} {self.valor!r}"


# frases da linguagem -> tipo do token. Cada frase vira somente um token.
FRASES_MEME = {
    "OLHA O GÁS": "PRINT",
    "se é louco cachoeira": "INPUT",
    "aqui tem coragem": "LET",
    "quero cafééé": "IF",
    "que show da xuxa é esse": "ELSE",
    "para nossa alegria": "END",
    "Irineu você não sabe nem eu": "WHILE",
}

# palavras reservadas simples, usadas nas expressões.
PALAVRAS_RESERVADAS = {
    "and": "AND", "or": "OR", "not": "NOT",
    "True": "TRUE", "False": "FALSE", "None": "NONE",
}

OPERADORES = {
    # comparação
    "==": "EQ", "!=": "NE", "<=": "LE", ">=": "GE", "<": "LT", ">": "GT",
    
    # atribuição
    "=": "ASSIGN",
    
    # aritmética
    "+": "PLUS", "-": "MINUS", "*": "STAR", "/": "SLASH",
    "//": "FLOORDIV", "%": "MOD", "**": "POW",
    
    # pontuação
    "(": "LPAREN", ")": "RPAREN", "[": "LBRACKET", "]": "RBRACKET",
    ",": "COMMA", ".": "DOT", ":": "COLON",
}

# escapes aceitos dentro de strings, como "\n".
ESCAPES = {"n": "\n", "t": "\t", "\\": "\\", '"': '"', "'": "'", "0": "\0"}


def _montar_regex_frases():
    """Regex que reconhece qualquer frase-meme.

    Testa as frases mais longas primeiro, aceita vários espaços entre as
    palavras e não casa se a frase for o começo de uma palavra maior.
    """
    frases = sorted(FRASES_MEME, key=len, reverse=True)
    alternativas = []
    for frase in frases:
        palavras = [re.escape(palavra) for palavra in frase.split()]
        alternativas.append(r"\s+".join(palavras))
    return re.compile("(?:" + "|".join(alternativas) + r")(?!\w)")


# operadores mais longos primeiro, para "==" não virar dois "=".
_operadores_ordenados = sorted(OPERADORES, key=len, reverse=True)

RE_FRASE = _montar_regex_frases()
RE_OPERADOR = re.compile("|".join(map(re.escape, _operadores_ordenados)))
RE_IDENTIFICADOR = re.compile(r"[^\W\d]\w*")
RE_NUMERO = re.compile(r"\d+(?:\.\d+)?")
RE_ESPACO = re.compile(r"[ \t]+")


def _ler_string(texto_linha, posicao_aspa, numero_linha, eh_fstring):
    """Lê uma string que começa na aspa em `posicao_aspa`.

    Devolve (conteudo, posicao_depois_da_string).
    """
    aspa = texto_linha[posicao_aspa]
    posicao = posicao_aspa + 1
    caracteres = []

    while posicao < len(texto_linha):
        caractere = texto_linha[posicao]

        if caractere == aspa:
            return "".join(caracteres), posicao + 1

        if caractere == "\\" and posicao + 1 < len(texto_linha):
            proximo = texto_linha[posicao + 1]
            if eh_fstring:
                # Em f-string o escape fica cru; quem avalia decide depois.
                caracteres.append("\\" + proximo)
            else:
                caracteres.append(ESCAPES.get(proximo, proximo))
            posicao += 2
            continue

        caracteres.append(caractere)
        posicao += 1

    raise LexerError("string sem aspas de fechamento", numero_linha, posicao_aspa + 1)


def tokenizar(codigo):
    """Transforma o código .meme em uma lista de tokens."""
    # garante que letras acentuadas (é, Á) tenham sempre a mesma forma.
    codigo = unicodedata.normalize("NFC", codigo)
    tokens = []
    niveis_indentacao = [0]  # níveis dos blocos abertos

    for numero_linha, texto_linha in enumerate(codigo.splitlines(), start=1):

        # --- 1. ignora linhas vazias e linhas só com comentário
        sem_indentacao = texto_linha.lstrip(" \t")
        conteudo = sem_indentacao.strip()
        if not conteudo or conteudo.startswith("#"):
            continue

        # --- 2. mede a indentação e gera INDENT / DEDENT
        tamanho_indentacao = len(texto_linha) - len(sem_indentacao)
        if "\t" in texto_linha[:tamanho_indentacao]:
            raise LexerError("use espaços (não tabs) para indentar", numero_linha, 1)

        if tamanho_indentacao > niveis_indentacao[-1]:
            niveis_indentacao.append(tamanho_indentacao)
            tokens.append(Token("INDENT", tamanho_indentacao, numero_linha, 1))
        else:
            while tamanho_indentacao < niveis_indentacao[-1]:
                niveis_indentacao.pop()
                tokens.append(Token("DEDENT", tamanho_indentacao, numero_linha, 1))
            if tamanho_indentacao != niveis_indentacao[-1]:
                raise LexerError("indentação inconsistente", numero_linha, 1)

        # --- 3. lê os tokens da linha, da esquerda para a direita
        posicao = tamanho_indentacao
        while posicao < len(texto_linha):
            espacos = RE_ESPACO.match(texto_linha, posicao)
            if espacos:
                posicao = espacos.end()
                continue

            coluna = posicao + 1
            caractere = texto_linha[posicao]

            # comentário
            if caractere == "#":
                break

            # frases (OLHA O GÁS, quero cafééé, ...)
            achou_frase = RE_FRASE.match(texto_linha, posicao)
            if achou_frase:
                frase = " ".join(achou_frase.group().split())
                tokens.append(Token(FRASES_MEME[frase], frase, numero_linha, coluna))
                posicao = achou_frase.end()
                continue

            # f-string: f"Olá {nome}"
            proximo = texto_linha[posicao + 1 : posicao + 2]
            if caractere in "fF" and proximo in ("\"", "'"):
                valor, posicao = _ler_string(texto_linha, posicao + 1, numero_linha, True)
                tokens.append(Token("FSTRING", valor, numero_linha, coluna))
                continue

            # string normal: "texto" ou 'texto'
            if caractere in "\"'":
                valor, posicao = _ler_string(texto_linha, posicao, numero_linha, False)
                tokens.append(Token("STRING", valor, numero_linha, coluna))
                continue

            # número
            achou_numero = RE_NUMERO.match(texto_linha, posicao)
            if achou_numero:
                texto_numero = achou_numero.group()
                if "." in texto_numero:
                    valor = float(texto_numero)
                else:
                    valor = int(texto_numero)
                tokens.append(Token("NUMBER", valor, numero_linha, coluna))
                posicao = achou_numero.end()
                continue

            # nome de variável ou palavra reservada
            achou_nome = RE_IDENTIFICADOR.match(texto_linha, posicao)
            if achou_nome:
                nome = achou_nome.group()
                tipo = PALAVRAS_RESERVADAS.get(nome, "IDENT")
                tokens.append(Token(tipo, nome, numero_linha, coluna))
                posicao = achou_nome.end()
                continue

            # operadores: ==, +, (, ...
            achou_operador = RE_OPERADOR.match(texto_linha, posicao)
            if achou_operador:
                operador = achou_operador.group()
                tokens.append(Token(OPERADORES[operador], operador, numero_linha, coluna))
                posicao = achou_operador.end()
                continue

            raise LexerError(f"caractere inesperado {caractere!r}", numero_linha, coluna)

        # --- 4. marca o fim da linha
        tokens.append(Token("NEWLINE", "\\n", numero_linha, len(texto_linha) + 1))

    # --- 5. mecha os blocos abertos e marca o fim do arquivo
    ultima_linha = tokens[-1].linha if tokens else 1
    while len(niveis_indentacao) > 1:
        niveis_indentacao.pop()
        tokens.append(Token("DEDENT", 0, ultima_linha, 1))
    tokens.append(Token("EOF", None, ultima_linha, 1))

    return tokens


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python lexer.py arquivo.meme")
        sys.exit(1)

    nome_arquivo = sys.argv[1]
    try:
        with open(nome_arquivo, encoding="utf-8") as arquivo:
            for token in tokenizar(arquivo.read()):
                print(token)
    except FileNotFoundError:
        print(f"o meu amor não fique triste: '{nome_arquivo}' não foi encontrado.")
    except LexerError as erro:
        print(f"o meu amor não fique triste: {erro}")