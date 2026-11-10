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


# Frases-meme -> tipo do token. Cada frase vira somente um token.
FRASES = {
    "OLHA O GÁS": "PRINT",
    "se é louco cachoeira": "INPUT",
    "aqui tem coragem": "LET",
    "quero cafééé": "IF",
    "que show da xuxa é esse": "ELSE",
    "para nossa alegria": "END",
    "Irineu você não sabe nem eu": "WHILE",
}

# Palavras simples reservadas (vindas do Python, usadas nas expressões).
PALAVRAS = {
    "and": "AND",
    "or": "OR",
    "not": "NOT",
    "True": "TRUE",
    "False": "FALSE",
    "None": "NONE",
}

# Operadores: os de 2 caracteres vêm antes para ganhar dos de 1.
OPERADORES = {
    "==": "EQ", "!=": "NE", "<=": "LE", ">=": "GE",
    "//": "FLOORDIV", "**": "POW",
    "<": "LT", ">": "GT", "=": "ASSIGN",
    "+": "PLUS", "-": "MINUS", "*": "STAR", "/": "SLASH", "%": "MOD",
    "(": "LPAREN", ")": "RPAREN", ",": "COMMA", "[": "LBRACKET",
    "]": "RBRACKET", ".": "DOT", ":": "COLON",
}


def _montar_regex_frases():
    # Mais longas primeiro; espaços na frase aceitam qualquer quantidade de
    # espaços; (?!\w) impede casar o começo de uma palavra maior.
    frases = sorted(FRASES, key=len, reverse=True)
    alternativas = [r"\s+".join(map(re.escape, f.split())) for f in frases]
    return re.compile("(?:" + "|".join(alternativas) + r")(?!\w)")


RE_FRASE = _montar_regex_frases()
RE_IDENT = re.compile(r"[^\W\d]\w*")
RE_NUMERO = re.compile(r"\d+(?:\.\d+)?")
RE_OP = re.compile(
    "|".join(map(re.escape, sorted(OPERADORES, key=len, reverse=True)))
)
RE_ESPACO = re.compile(r"[ \t]+")

ESCAPES = {"n": "\n", "t": "\t", "\\": "\\", '"': '"', "'": "'", "0": "\0"}


def _ler_string(linha_txt, pos, n_linha, prefixo_f):
    """Lê uma string começando na aspa em `pos`. Devolve (valor, nova_pos)."""
    aspa = linha_txt[pos]
    i = pos + 1
    partes = []
    while i < len(linha_txt):
        c = linha_txt[i]
        if c == aspa:
            return "".join(partes), i + 1
        if c == "\\" and i + 1 < len(linha_txt):
            prox = linha_txt[i + 1]
            # Em f-string o texto é mantido cru; quem avalia decide depois.
            partes.append("\\" + prox if prefixo_f else ESCAPES.get(prox, prox))
            i += 2
            continue
        partes.append(c)
        i += 1
    raise LexerError("string sem aspas de fechamento", n_linha, pos + 1)


def tokenizar(codigo):
    codigo = unicodedata.normalize("NFC", codigo)
    tokens = []
    pilha_indent = [0]

    for n_linha, linha in enumerate(codigo.splitlines(), start=1):
        sem_indent = linha.lstrip(" \t")
        # Linha vazia ou só comentário: ignora.
        if not sem_indent.strip() or sem_indent.lstrip().startswith("#"):
            continue

        if "\t" in linha[: len(linha) - len(sem_indent)]:
            raise LexerError("use espaços (não tabs) para indentar", n_linha, 1)

        # --- indentação -> INDENT / DEDENT
        indent = len(linha) - len(sem_indent)
        if indent > pilha_indent[-1]:
            pilha_indent.append(indent)
            tokens.append(Token("INDENT", indent, n_linha, 1))
        else:
            while indent < pilha_indent[-1]:
                pilha_indent.pop()
                tokens.append(Token("DEDENT", indent, n_linha, 1))
            if indent != pilha_indent[-1]:
                raise LexerError("indentação inconsistente", n_linha, 1)

        # --- tokens da linha
        pos = indent
        while pos < len(linha):
            if m := RE_ESPACO.match(linha, pos):
                pos = m.end()
                continue
            col = pos + 1
            c = linha[pos]

            if c == "#":  # comentário até o fim da linha
                break

            if m := RE_FRASE.match(linha, pos):
                frase = " ".join(m.group().split())
                tokens.append(Token(FRASES[frase], frase, n_linha, col))
                pos = m.end()
                continue

            # f"..." (prefixo f/F colado na aspa)
            if c in "fF" and pos + 1 < len(linha) and linha[pos + 1] in "\"'":
                valor, pos = _ler_string(linha, pos + 1, n_linha, True)
                tokens.append(Token("FSTRING", valor, n_linha, col))
                continue

            if c in "\"'":
                valor, pos = _ler_string(linha, pos, n_linha, False)
                tokens.append(Token("STRING", valor, n_linha, col))
                continue

            if m := RE_NUMERO.match(linha, pos):
                txt = m.group()
                valor = float(txt) if "." in txt else int(txt)
                tokens.append(Token("NUMBER", valor, n_linha, col))
                pos = m.end()
                continue

            if m := RE_IDENT.match(linha, pos):
                txt = m.group()
                tipo = PALAVRAS.get(txt, "IDENT")
                tokens.append(Token(tipo, txt, n_linha, col))
                pos = m.end()
                continue

            if m := RE_OP.match(linha, pos):
                tokens.append(Token(OPERADORES[m.group()], m.group(), n_linha, col))
                pos = m.end()
                continue

            raise LexerError(f"caractere inesperado {c!r}", n_linha, col)

        tokens.append(Token("NEWLINE", "\\n", n_linha, len(linha) + 1))

    # fecha os blocos que ficaram abertos no fim do arquivo
    ultima = tokens[-1].linha if tokens else 1
    while len(pilha_indent) > 1:
        pilha_indent.pop()
        tokens.append(Token("DEDENT", 0, ultima, 1))
    tokens.append(Token("EOF", None, ultima, 1))
    return tokens


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python lexer.py arquivo.meme")
        sys.exit(1)
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            for t in tokenizar(f.read()):
                print(t)
    except FileNotFoundError:
        print(f"o meu amor não fique triste: '{sys.argv[1]}' não foi encontrado.")
    except LexerError as e:
        print(f"o meu amor não fique triste: {e}")