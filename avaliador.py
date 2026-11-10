"""Avaliador da linguagem Meme.

Percorre a Árvore Sintática Abstrata (AST) produzida pelo parser e
executa o programa, nó por nó.

Fluxo completo:
    código-fonte (.meme)
        └─► lexer.py   ──► lista de Tokens
                └─► parser.py  ──► nó Programa (AST)
                        └─► avaliador.py ──► execução / resultado

Uso:  python avaliador.py arquivo.meme
"""
import re
import sys

from ast_nodes import (
    Programa, Comando, Expressao,
    Print, Atribuicao, If, While,
    Literal, FString, Variavel, Input,
    Binario, Unario, Chamada,
)
from parser import parsear


# ---------------------------------------------------------------------------
# Exceção de erro em tempo de execução
# ---------------------------------------------------------------------------

class ErroExecucao(Exception):
    """Lançada quando algo dá errado durante a execução do programa Meme.

    Guarda a linha do nó da AST que causou o erro para uma mensagem clara.
    """

    def __init__(self, mensagem: str, linha: int = 0):
        super().__init__(f"linha {linha}: {mensagem}")
        self.linha = linha


# ---------------------------------------------------------------------------
# Ambiente de variáveis
# ---------------------------------------------------------------------------

class Ambiente:
    """Tabela de símbolos: guarda o nome e o valor de cada variável.

    Funciona como uma pilha de dicionários (escopos). Quando o avaliador
    entra num bloco (if, while) ele empurra um escopo novo; ao sair, ele
    desempilha. Assim variáveis internas não "vazam" para fora.

    Resolução de nome:
        Busca do escopo mais interno para o mais externo, como Python faz.
        Se não achar em nenhum, lança ErroExecucao.
    """

    def __init__(self):
        # Pilha de dicionários; o índice -1 é o escopo mais interno.
        # Começa com um dicionário global vazio.
        self._escopos: list[dict[str, object]] = [{}]

    def entrar_escopo(self) -> None:
        """Empurra um novo escopo vazio (usado ao entrar em blocos)."""
        self._escopos.append({})

    def sair_escopo(self) -> None:
        """Desempilha o escopo mais interno (usado ao sair de blocos)."""
        if len(self._escopos) > 1:
            self._escopos.pop()

    def definir(self, nome: str, valor: object) -> None:
        """Cria ou atualiza a variável `nome` no escopo mais interno.

        Se a variável já existir em algum escopo externo, ela é atualizada
        lá (comportamento semelhante ao Python: atribuição não cria shadowing
        implícito).
        """
        # Procura em escopos do mais interno para o mais externo
        for escopo in reversed(self._escopos):
            if nome in escopo:
                escopo[nome] = valor
                return
        # Não existia em nenhum escopo: cria no escopo mais interno
        self._escopos[-1][nome] = valor

    def buscar(self, nome: str, linha: int = 0) -> object:
        """Devolve o valor da variável `nome`.

        Busca do escopo mais interno para o mais externo.
        Lança ErroExecucao se a variável não estiver definida.
        """
        for escopo in reversed(self._escopos):
            if nome in escopo:
                return escopo[nome]
        raise ErroExecucao(f"variável '{nome}' não foi definida", linha)


# ---------------------------------------------------------------------------
# Funções nativas disponíveis nos programas Meme
# ---------------------------------------------------------------------------

# Mapeamento: nome usado no código → função Python equivalente.
# O avaliador consulta este dicionário ao processar um nó Chamada.
FUNCOES_NATIVAS = {
    "int":   int,       # converte para inteiro:  int("42") → 42
    "float": float,     # converte para float:    float("3.14") → 3.14
    "str":   str,       # converte para string:   str(42) → "42"
    "round": round,     # arredonda:              round(3.567, 2) → 3.57
    "len":   len,       # comprimento:            len("oi") → 2
}


# ---------------------------------------------------------------------------
# Avaliador principal
# ---------------------------------------------------------------------------

class Avaliador:
    """Percorre a AST e executa o programa Meme.

    Implementa o padrão Visitor de forma simples: um método `_avaliar`
    central que despacha para o método correto de acordo com o tipo do nó.

    Dois grupos de métodos:
        _executar_*   → processa nós Comando (Print, Atribuicao, If, While)
        _avaliar_*    → processa nós Expressao e devolve um valor Python
    """

    def __init__(self):
        # Ambiente de variáveis compartilhado por toda a execução
        self._ambiente = Ambiente()

    # ------------------------------------------------------------------
    # Despacho central
    # ------------------------------------------------------------------

    def executar(self, programa: Programa) -> None:
        """Ponto de entrada: executa todos os comandos do programa."""
        for comando in programa.comandos:
            self._executar(comando)

    def _executar(self, no: Comando) -> None:
        """Despacha um nó Comando para o método _executar_* correto."""
        tipo = type(no).__name__
        metodo = getattr(self, f"_executar_{tipo}", None)
        if metodo is None:
            raise ErroExecucao(f"comando desconhecido: {tipo}", getattr(no, "linha", 0))
        metodo(no)

    def _avaliar(self, no: Expressao) -> object:
        """Despacha um nó Expressao para o método _avaliar_* correto
        e devolve o valor Python resultante."""
        tipo = type(no).__name__
        metodo = getattr(self, f"_avaliar_{tipo}", None)
        if metodo is None:
            raise ErroExecucao(f"expressão desconhecida: {tipo}", getattr(no, "linha", 0))
        return metodo(no)

    # ------------------------------------------------------------------
    # Execução de comandos
    # ------------------------------------------------------------------

    def _executar_Print(self, no: Print) -> None:
        """Avalia a expressão do PRINT e exibe o resultado no terminal.

        OLHA O GÁS "Olá mundo"  →  print("Olá mundo")
        """
        valor = self._avaliar(no.expressao)
        # Converte para string da mesma forma que o Python faz com print()
        print(self._para_str(valor))

    def _executar_Atribuicao(self, no: Atribuicao) -> None:
        """Avalia a expressão do lado direito e guarda no ambiente.

        aqui tem coragem x = 1 + 2  →  x recebe 3
        """
        valor = self._avaliar(no.expressao)
        self._ambiente.definir(no.nome, valor)

    def _executar_If(self, no: If) -> None:
        """Avalia a condição e executa o corpo ou o ramo else.

        quero cafééé x > 0
            ...corpo...
        que show da xuxa é esse
            ...senao...
        para nossa alegria

        A condição segue a mesma semântica do Python (qualquer valor
        não-nulo/não-zero/não-vazio é verdadeiro).
        """
        condicao = self._avaliar(no.condicao)

        # Entra num escopo novo para isolar variáveis do bloco
        self._ambiente.entrar_escopo()
        try:
            if condicao:
                # Condição verdadeira: executa o bloco do if
                for cmd in no.corpo:
                    self._executar(cmd)
            elif no.senao:
                # Condição falsa e há ramo else: executa o bloco else
                for cmd in no.senao:
                    self._executar(cmd)
        finally:
            # Sempre sai do escopo, mesmo se ocorrer um erro
            self._ambiente.sair_escopo()

    def _executar_While(self, no: While) -> None:
        """Avalia a condição repetidamente e executa o corpo enquanto for verdadeira.

        Irineu você não sabe nem eu tentativas > 0
            ...corpo...

        A cada iteração um escopo novo é criado e descartado, assim
        variáveis declaradas dentro do laço não "acumulam" entre voltas.
        """
        while self._avaliar(no.condicao):
            self._ambiente.entrar_escopo()
            try:
                for cmd in no.corpo:
                    self._executar(cmd)
            finally:
                self._ambiente.sair_escopo()

    # ------------------------------------------------------------------
    # Avaliação de expressões
    # ------------------------------------------------------------------

    def _avaliar_Literal(self, no: Literal) -> object:
        """Devolve o valor já pronto, guardado no nó pelo parser.

        42 → int(42),  "oi" → str("oi"),  True → bool(True), None → None
        """
        return no.valor

    def _avaliar_FString(self, no: FString) -> str:
        """Interpola variáveis dentro de uma f-string.

        f"Olá {nome}, você tem {idade} anos"
            → "Olá João, você tem 20 anos"

        Cada {nome_de_variavel} é substituído pelo valor atual da variável
        no ambiente. Se a variável não existir, lança ErroExecucao.
        """
        def substituir(match: re.Match) -> str:
            # Pega o nome da variável entre as chaves
            nome_var = match.group(1)
            valor = self._ambiente.buscar(nome_var, no.linha)
            return self._para_str(valor)

        # Regex que encontra {nome} dentro do texto da f-string
        resultado = re.sub(r"\{(\w+)\}", substituir, no.texto)

        # Interpreta escapes como \n e \t que vieram crus do lexer
        resultado = resultado.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")
        return resultado

    def _avaliar_Variavel(self, no: Variavel) -> object:
        """Busca e devolve o valor atual da variável no ambiente.

        Se a variável não foi definida com `aqui tem coragem`, lança erro.
        """
        return self._ambiente.buscar(no.nome, no.linha)

    def _avaliar_Input(self, no: Input) -> str:
        """Avalia o prompt, exibe-o e lê uma linha do teclado.

        se é louco cachoeira "Qual seu nome? "
            → exibe "Qual seu nome? " e devolve o que o usuário digitou

        O resultado é sempre uma string (igual ao input() do Python).
        """
        prompt = self._para_str(self._avaliar(no.prompt))
        return input(prompt)

    def _avaliar_Unario(self, no: Unario) -> object:
        """Aplica um operador unário ao operando.

        Operadores suportados:
            MINUS  →  negação numérica:   -x
            NOT    →  negação lógica:     not x
        """
        operando = self._avaliar(no.operando)

        if no.operador == "MINUS":
            # Negação numérica: exige que o operando seja número
            self._verificar_numero(operando, no.linha, "-")
            return -operando

        if no.operador == "NOT":
            # Negação lógica: qualquer valor é aceito (semântica Python)
            return not operando

        raise ErroExecucao(f"operador unário desconhecido: {no.operador!r}", no.linha)

    def _avaliar_Binario(self, no: Binario) -> object:
        """Aplica um operador binário aos dois lados da expressão.

        Avalia esquerda e direita primeiro, depois aplica o operador.
        Divisão por zero e tipos incompatíveis lançam ErroExecucao.
        """
        # Operadores de curto-circuito (AND/OR) são tratados antes de
        # avaliar os dois lados, para evitar efeitos colaterais desnecessários
        if no.operador == "AND":
            return self._avaliar(no.esquerda) and self._avaliar(no.direita)
        if no.operador == "OR":
            return self._avaliar(no.esquerda) or self._avaliar(no.direita)

        # Para todos os outros operadores, avalia os dois lados agora
        esq = self._avaliar(no.esquerda)
        dir = self._avaliar(no.direita)

        # --- Comparação ---
        if no.operador == "EQ":   return esq == dir
        if no.operador == "NE":   return esq != dir
        if no.operador == "LT":
            self._verificar_mesmo_tipo(esq, dir, no.linha, "<")
            return esq < dir
        if no.operador == "GT":
            self._verificar_mesmo_tipo(esq, dir, no.linha, ">")
            return esq > dir
        if no.operador == "LE":
            self._verificar_mesmo_tipo(esq, dir, no.linha, "<=")
            return esq <= dir
        if no.operador == "GE":
            self._verificar_mesmo_tipo(esq, dir, no.linha, ">=")
            return esq >= dir

        # --- Aritmética ---
        if no.operador == "PLUS":
            # + funciona tanto para números quanto para concatenar strings
            if not (isinstance(esq, (int, float)) and isinstance(dir, (int, float))) \
               and not (isinstance(esq, str) and isinstance(dir, str)):
                raise ErroExecucao(
                    f"'+' exige dois números ou duas strings, "
                    f"mas recebeu {type(esq).__name__} e {type(dir).__name__}",
                    no.linha,
                )
            return esq + dir

        # Os demais operadores aritméticos exigem dois números
        self._verificar_numeros(esq, dir, no.linha, no.operador)

        if no.operador == "MINUS":    return esq - dir
        if no.operador == "STAR":     return esq * dir
        if no.operador == "POW":      return esq ** dir

        if no.operador == "SLASH":
            if dir == 0:
                raise ErroExecucao("divisão por zero", no.linha)
            return esq / dir

        if no.operador == "FLOORDIV":
            if dir == 0:
                raise ErroExecucao("divisão inteira por zero", no.linha)
            return esq // dir

        if no.operador == "MOD":
            if dir == 0:
                raise ErroExecucao("módulo por zero", no.linha)
            return esq % dir

        raise ErroExecucao(f"operador binário desconhecido: {no.operador!r}", no.linha)

    def _avaliar_Chamada(self, no: Chamada) -> object:
        """Chama uma função nativa com os argumentos avaliados.

        Funções disponíveis: int, float, str, round, len.
        Qualquer outro nome lança ErroExecucao.

        Exemplos:
            int("42")       → 42
            round(3.567, 2) → 3.57
            len("oi")       → 2
        """
        funcao = FUNCOES_NATIVAS.get(no.nome)
        if funcao is None:
            raise ErroExecucao(
                f"função '{no.nome}' não existe. "
                f"Funções disponíveis: {', '.join(FUNCOES_NATIVAS)}",
                no.linha,
            )

        # Avalia cada argumento antes de passar para a função
        argumentos = [self._avaliar(arg) for arg in no.argumentos]

        try:
            return funcao(*argumentos)
        except (ValueError, TypeError) as e:
            # Converte erros do Python em ErroExecucao com linha correta
            raise ErroExecucao(
                f"erro ao chamar '{no.nome}({', '.join(repr(a) for a in argumentos)})': {e}",
                no.linha,
            ) from e

    # ------------------------------------------------------------------
    # Utilitários internos
    # ------------------------------------------------------------------

    def _para_str(self, valor: object) -> str:
        """Converte um valor Python para a representação de texto Meme.

        Diferenças em relação ao str() do Python:
            True  → "True"   (não "true")
            False → "False"
            None  → "None"
        Essas são as mesmas palavras-chave que o lexer reconhece.
        """
        if isinstance(valor, bool):
            return "True" if valor else "False"
        if valor is None:
            return "None"
        return str(valor)

    def _verificar_numero(self, valor: object, linha: int, op: str) -> None:
        """Lança ErroExecucao se `valor` não for int nem float."""
        if not isinstance(valor, (int, float)) or isinstance(valor, bool):
            raise ErroExecucao(
                f"operador '{op}' exige um número, mas recebeu {type(valor).__name__!r}",
                linha,
            )

    def _verificar_numeros(self, esq: object, dir: object, linha: int, op: str) -> None:
        """Lança ErroExecucao se esq ou dir não forem numéricos."""
        if not isinstance(esq, (int, float)) or isinstance(esq, bool):
            raise ErroExecucao(
                f"operador '{op}': lado esquerdo deve ser número, "
                f"mas recebeu {type(esq).__name__!r}",
                linha,
            )
        if not isinstance(dir, (int, float)) or isinstance(dir, bool):
            raise ErroExecucao(
                f"operador '{op}': lado direito deve ser número, "
                f"mas recebeu {type(dir).__name__!r}",
                linha,
            )

    def _verificar_mesmo_tipo(self, esq: object, dir: object, linha: int, op: str) -> None:
        """Lança ErroExecucao se esq e dir forem de tipos incomparáveis."""
        if type(esq) != type(dir):
            raise ErroExecucao(
                f"operador '{op}' não pode comparar "
                f"{type(esq).__name__!r} com {type(dir).__name__!r}",
                linha,
            )


# ---------------------------------------------------------------------------
# Função pública de conveniência
# ---------------------------------------------------------------------------

def rodar(codigo: str) -> None:
    """Parseia e executa um programa Meme a partir de uma string de código.

    Uso típico (de scripts externos ou testes):
        from avaliador import rodar
        rodar(open("programa.meme").read())
    """
    arvore = parsear(codigo)
    Avaliador().executar(arvore)


# ---------------------------------------------------------------------------
# Modo CLI: python avaliador.py arquivo.meme
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python avaliador.py arquivo.meme")
        sys.exit(1)

    nome_arquivo = sys.argv[1]
    try:
        with open(nome_arquivo, encoding="utf-8") as f:
            codigo = f.read()
        rodar(codigo)
        print("\nsai da frente satanás")          # mensagem de sucesso da linguagem
    except FileNotFoundError:
        print(f"o meu amor não fique triste: '{nome_arquivo}' não foi encontrado.")
        sys.exit(1)
    except ErroExecucao as erro:
        print(f"o meu amor não fique triste: {erro}")
        sys.exit(1)
    except Exception as erro:
        print(f"o meu amor não fique triste: {erro}")
        sys.exit(1)

