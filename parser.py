"""Parser da linguagem Meme.

Recebe a lista de tokens produzida pelo lexer e monta a Árvore Sintática
Abstrata (AST) usando os nós definidos em ast_nodes.py.

Uso:  python parser.py arquivo.meme
"""
import sys

from lexer import Token, tokenizar
from ast_nodes import (
    Programa, Comando, Expressao,
    Print, Atribuicao, If, While,
    Literal, FString, Variavel, Input,
    Binario, Unario, Chamada,
)


class ParserError(Exception):

    def __init__(self, mensagem, linha):
        super().__init__(f"linha {linha}: {mensagem}")
        self.linha = linha


class Parser:
    """Analisa sintaticamente uma lista de tokens e produz um nó Programa."""

    def __init__(self, tokens: list[Token]):
        self._tokens = tokens
        self._pos = 0

    # ------------------------------------------------------------------
    # Utilitários de navegação
    # ------------------------------------------------------------------

    def _atual(self) -> Token:
        """Devolve o token na posição corrente."""
        return self._tokens[self._pos]

    def _tipo_atual(self) -> str:
        return self._atual().tipo

    def _linha_atual(self) -> int:
        return self._atual().linha

    def _avançar(self) -> Token:
        """Devolve o token atual e avança para o próximo."""
        token = self._tokens[self._pos]
        if token.tipo != "EOF":
            self._pos += 1
        return token

    def _consumir(self, tipo: str) -> Token:
        """Exige que o token atual seja do tipo `tipo`, avança e devolve-o.

        Lança ParserError se o tipo não bater.
        """
        token = self._atual()
        if token.tipo != tipo:
            raise ParserError(
                f"esperava {tipo!r}, mas encontrei {token.tipo!r} ({token.valor!r})",
                token.linha,
            )
        return self._avançar()

    def _verifica(self, *tipos: str) -> bool:
        """True se o token atual for de um dos tipos dados."""
        return self._tipo_atual() in tipos

    # ------------------------------------------------------------------
    # Ponto de entrada
    # ------------------------------------------------------------------

    def parsear(self) -> Programa:
        """Regra: programa = { comando } EOF"""
        linha = self._linha_atual()
        comandos: list[Comando] = []

        while not self._verifica("EOF"):
            comandos.append(self._comando())

        self._consumir("EOF")
        return Programa(comandos=comandos, linha=linha)

    # ------------------------------------------------------------------
    # Comandos
    # ------------------------------------------------------------------

    def _comando(self) -> Comando:
        """Regra: comando = print | atribuicao | if | while"""
        tipo = self._tipo_atual()

        if tipo == "PRINT":
            return self._print()
        if tipo == "LET":
            return self._atribuicao()
        if tipo == "IF":
            return self._if()
        if tipo == "WHILE":
            return self._while()

        raise ParserError(
            f"comando inesperado: {tipo!r} ({self._atual().valor!r})",
            self._linha_atual(),
        )

    def _print(self) -> Print:
        """Regra: print = PRINT expr NEWLINE"""
        linha = self._linha_atual()
        self._consumir("PRINT")
        expressao = self._expr()
        self._consumir("NEWLINE")
        return Print(expressao=expressao, linha=linha)

    def _atribuicao(self) -> Atribuicao:
        """Regra: atribuicao = LET IDENT ASSIGN expr NEWLINE"""
        linha = self._linha_atual()
        self._consumir("LET")
        nome = self._consumir("IDENT").valor
        self._consumir("ASSIGN")
        expressao = self._expr()
        self._consumir("NEWLINE")
        return Atribuicao(nome=nome, expressao=expressao, linha=linha)

    def _if(self) -> If:
        """Regra: if = IF expr NEWLINE bloco [ ELSE NEWLINE bloco ] [ END NEWLINE ]"""
        linha = self._linha_atual()
        self._consumir("IF")
        condicao = self._expr()
        self._consumir("NEWLINE")
        corpo = self._bloco()

        senao: list[Comando] = []
        if self._verifica("ELSE"):
            self._consumir("ELSE")
            self._consumir("NEWLINE")
            senao = self._bloco()

        if self._verifica("END"):
            self._consumir("END")
            self._consumir("NEWLINE")

        return If(condicao=condicao, corpo=corpo, senao=senao, linha=linha)

    def _while(self) -> While:
        """Regra: while = WHILE expr NEWLINE bloco"""
        linha = self._linha_atual()
        self._consumir("WHILE")
        condicao = self._expr()
        self._consumir("NEWLINE")
        corpo = self._bloco()
        return While(condicao=condicao, corpo=corpo, linha=linha)

    def _bloco(self) -> list[Comando]:
        """Regra: bloco = INDENT comando { comando } DEDENT"""
        self._consumir("INDENT")
        comandos: list[Comando] = [self._comando()]
        while not self._verifica("DEDENT"):
            comandos.append(self._comando())
        self._consumir("DEDENT")
        return comandos

    # ------------------------------------------------------------------
    # Expressões  (do nível mais fraco para o mais forte)
    # ------------------------------------------------------------------

    def _expr(self) -> Expressao:
        """Regra: expr = ou"""
        return self._ou()

    def _ou(self) -> Expressao:
        """Regra: ou = e { OR e }"""
        esq = self._e()
        while self._verifica("OR"):
            linha = self._linha_atual()
            op = self._avançar().tipo   # consome OR
            dir = self._e()
            esq = Binario(operador=op, esquerda=esq, direita=dir, linha=linha)
        return esq

    def _e(self) -> Expressao:
        """Regra: e = nao { AND nao }"""
        esq = self._nao()
        while self._verifica("AND"):
            linha = self._linha_atual()
            op = self._avançar().tipo   # consome AND
            dir = self._nao()
            esq = Binario(operador=op, esquerda=esq, direita=dir, linha=linha)
        return esq

    def _nao(self) -> Expressao:
        """Regra: nao = NOT nao | comparacao"""
        if self._verifica("NOT"):
            linha = self._linha_atual()
            op = self._avançar().tipo   # consome NOT
            operando = self._nao()
            return Unario(operador=op, operando=operando, linha=linha)
        return self._comparacao()

    def _comparacao(self) -> Expressao:
        """Regra: comparacao = soma [ ( EQ | NE | LT | GT | LE | GE ) soma ]

        Comparação não encadeia: a < b < c é erro de sintaxe.
        """
        esq = self._soma()
        if self._verifica("EQ", "NE", "LT", "GT", "LE", "GE"):
            linha = self._linha_atual()
            op = self._avançar().tipo
            dir = self._soma()
            return Binario(operador=op, esquerda=esq, direita=dir, linha=linha)
        return esq

    def _soma(self) -> Expressao:
        """Regra: soma = termo { ( PLUS | MINUS ) termo }"""
        esq = self._termo()
        while self._verifica("PLUS", "MINUS"):
            linha = self._linha_atual()
            op = self._avançar().tipo
            dir = self._termo()
            esq = Binario(operador=op, esquerda=esq, direita=dir, linha=linha)
        return esq

    def _termo(self) -> Expressao:
        """Regra: termo = unario { ( STAR | SLASH | FLOORDIV | MOD ) unario }"""
        esq = self._unario()
        while self._verifica("STAR", "SLASH", "FLOORDIV", "MOD"):
            linha = self._linha_atual()
            op = self._avançar().tipo
            dir = self._unario()
            esq = Binario(operador=op, esquerda=esq, direita=dir, linha=linha)
        return esq

    def _unario(self) -> Expressao:
        """Regra: unario = MINUS unario | potencia"""
        if self._verifica("MINUS"):
            linha = self._linha_atual()
            op = self._avançar().tipo   # consome MINUS
            operando = self._unario()
            return Unario(operador=op, operando=operando, linha=linha)
        return self._potencia()

    def _potencia(self) -> Expressao:
        """Regra: potencia = primario [ POW unario ]

        Associatividade à direita: o lado direito chama _unario (não _potencia),
        o que garante que 2 ** 3 ** 2 == 2 ** (3 ** 2).
        """
        base = self._primario()
        if self._verifica("POW"):
            linha = self._linha_atual()
            op = self._avançar().tipo   # consome POW
            exp = self._unario()
            return Binario(operador=op, esquerda=base, direita=exp, linha=linha)
        return base

    def _primario(self) -> Expressao:
        """Regra: primario = NUMBER | STRING | FSTRING
                           | TRUE | FALSE | NONE
                           | INPUT expr
                           | IDENT [ LPAREN [ argumentos ] RPAREN ]
                           | LPAREN expr RPAREN
        """
        token = self._atual()
        linha = token.linha

        # Literais numéricos e strings
        if self._verifica("NUMBER", "STRING"):
            self._avançar()
            return Literal(valor=token.valor, linha=linha)

        # F-string
        if self._verifica("FSTRING"):
            self._avançar()
            return FString(texto=token.valor, linha=linha)

        # Literais booleanos e None
        if self._verifica("TRUE"):
            self._avançar()
            return Literal(valor=True, linha=linha)
        if self._verifica("FALSE"):
            self._avançar()
            return Literal(valor=False, linha=linha)
        if self._verifica("NONE"):
            self._avançar()
            return Literal(valor=None, linha=linha)

        # Input: se é louco cachoeira expr
        if self._verifica("INPUT"):
            self._avançar()
            prompt = self._expr()
            return Input(prompt=prompt, linha=linha)

        # Variável ou chamada de função: IDENT [ LPAREN [ argumentos ] RPAREN ]
        if self._verifica("IDENT"):
            self._avançar()
            nome = token.valor
            if self._verifica("LPAREN"):
                self._avançar()             # consome (
                argumentos: list[Expressao] = []
                if not self._verifica("RPAREN"):
                    argumentos = self._argumentos()
                self._consumir("RPAREN")
                return Chamada(nome=nome, argumentos=argumentos, linha=linha)
            return Variavel(nome=nome, linha=linha)

        # Expressão parentesizada: ( expr )
        if self._verifica("LPAREN"):
            self._avançar()             # consome (
            expressao = self._expr()
            self._consumir("RPAREN")
            return expressao            # sem nó extra, conforme a gramática

        raise ParserError(
            f"expressão inválida: {token.tipo!r} ({token.valor!r})",
            linha,
        )

    def _argumentos(self) -> list[Expressao]:
        """Regra: argumentos = expr { COMMA expr }"""
        args = [self._expr()]
        while self._verifica("COMMA"):
            self._avançar()             # consome ,
            args.append(self._expr())
        return args


# ---------------------------------------------------------------------------
# Função auxiliar para imprimir a AST de forma legível
# ---------------------------------------------------------------------------

def _dump(no, prefixo="", ultimo=True):
    """Imprime a árvore em formato de texto, igual ao exemplo da gramática."""
    conector = "└── " if ultimo else "├── "
    extensao = "    " if ultimo else "│   "

    nome_no = type(no).__name__

    if hasattr(no, "__dataclass_fields__"):
        campos = list(no.__dataclass_fields__.keys())
        # Remove 'linha' do resumo da linha de cabeçalho
        campos_sem_linha = [c for c in campos if c != "linha"]

        # Para nós com um único campo relevante, mostra o valor no cabeçalho
        if len(campos_sem_linha) == 1:
            valor = getattr(no, campos_sem_linha[0])
            if not isinstance(valor, (list,)) and not hasattr(valor, "__dataclass_fields__"):
                print(f"{prefixo}{conector}{nome_no}({campos_sem_linha[0]}={valor!r})")
                return

        print(f"{prefixo}{conector}{nome_no}")
        filhos = [(c, getattr(no, c)) for c in campos_sem_linha]
        for i, (nome_campo, valor) in enumerate(filhos):
            eh_ultimo = i == len(filhos) - 1
            if isinstance(valor, list):
                sub_conector = "└── " if eh_ultimo else "├── "
                print(f"{prefixo}{extensao}{sub_conector}{nome_campo}: [{len(valor)} item(s)]")
                sub_ext = "    " if eh_ultimo else "│   "
                for j, item in enumerate(valor):
                    _dump(item, prefixo + extensao + sub_ext, j == len(valor) - 1)
            elif hasattr(valor, "__dataclass_fields__"):
                sub_conector = "└── " if eh_ultimo else "├── "
                print(f"{prefixo}{extensao}{sub_conector}{nome_campo}:")
                sub_ext = "    " if eh_ultimo else "│   "
                _dump(valor, prefixo + extensao + sub_ext, True)
            else:
                sub_conector = "└── " if eh_ultimo else "├── "
                print(f"{prefixo}{extensao}{sub_conector}{nome_campo}={valor!r}")
    else:
        print(f"{prefixo}{conector}{no!r}")


def dump_ast(arvore):
    """Ponto de entrada para imprimir uma AST completa."""
    nome_no = type(arvore).__name__
    print(nome_no)
    if hasattr(arvore, "comandos"):
        for i, cmd in enumerate(arvore.comandos):
            _dump(cmd, "", i == len(arvore.comandos) - 1)


# ---------------------------------------------------------------------------
# Função pública de conveniência
# ---------------------------------------------------------------------------

def parsear(codigo: str) -> Programa:
    """Tokeniza `codigo` e devolve a AST como nó Programa."""
    from lexer import tokenizar
    tokens = tokenizar(codigo)
    return Parser(tokens).parsear()


# ---------------------------------------------------------------------------
# Modo CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python parser.py arquivo.meme")
        sys.exit(1)

    nome_arquivo = sys.argv[1]
    try:
        with open(nome_arquivo, encoding="utf-8") as f:
            codigo = f.read()
        arvore = parsear(codigo)
        dump_ast(arvore)
    except FileNotFoundError:
        print(f"o meu amor não fique triste: '{nome_arquivo}' não foi encontrado.")
        sys.exit(1)
    except Exception as erro:
        print(f"o meu amor não fique triste: {erro}")
        sys.exit(1)
